"""`python app.py --mode board`: MuJoCo trên laptop, SmolVLA ONNX chạy trên Ventuno Q (KHÔNG qua STM32).

Một lệnh làm hết:
  1. chờ Ventuno Q qua USB-C (adb.exe của Arduino App Lab), kiểm tra đúng board arduino,monza
  2. mở simulation schema v2 (board_server/app.py: cửa sổ MuJoCo + dashboard http://localhost:8000)
     và ADB reverse 5050 (điều khiển) / 18000 (ảnh + góc khớp)
  3. kiểm tra trên board: Python có onnxruntime + QNN, và có 2 thư mục model
  4. gửi runner qua ADB (stdin) và chạy trên host IQ8: ../so101arm/python/board_runner.py
     (prefix_fp16 trên CPU, denoise core trên NPU) -> ACTION_CHUNK -> MuJoCo
Runner ghi 3 file code vào <board-dir>/python/ trên board (board_runner.py, smolvla_runner.py,
smolvla_config.json); không đụng tới sketch/ hay app khác. Model không tự chép: xem --push-models.
Mỗi lần gõ lệnh chạy MỘT lượt. Rút USB-C: model dừng, simulation HOLD, không tự chạy lại.
Ctrl+C: dừng runner trên board, tắt simulation, gỡ ADB reverse.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import glob
import json
import os
from pathlib import Path
import secrets
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parent                 # so101sim
SERVER = ROOT / 'board_server'                         # simulator schema v2
ARM_PYTHON = ROOT.parent / 'so101arm' / 'python'       # code chạy trên Ventuno Q
MODELS = ROOT.parent / 'ai'                            # bản gốc 2 gói model trên laptop
ADB_GLOB = '/mnt/c/Users/*/AppData/Local/AppLab/*/data/packages/arduino/tools/adb/*/adb.exe'
BOARD_DIR = '/home/arduino/ArduinoApps/so101arm'
BOARD_PYTHON = '/home/arduino/onnx-qnn-experiment/venv/bin/python'
BOARD_WEB_PORT = 18000   # đầu phía board của dashboard/camera (board tự dùng cổng 8000)
RUNNER_PID_FILE = '/tmp/so101-board-runner.pid'
MODEL_DIRS = ('smolvla_prefix', 'smolvla_w8a16')
MODEL_FILES = ('smolvla_prefix/prefix_fp16.onnx', 'smolvla_prefix/prefix_fp16.onnx.data',
               'smolvla_prefix/tokenizer/tokenizer.json', 'smolvla_w8a16/io_projector_weights.npz')
BALLS = ('red_ball', 'green_ball', 'blue_ball', 'yellow_ball')


class LinkError(RuntimeError):
    pass


def say(text):
    print(f'[{datetime.now():%H:%M:%S}] {text}', flush=True)


def find_adb(explicit=None):
    for candidate in (explicit, os.getenv('SO101_ADB')):
        if candidate:
            return candidate
    found = sorted(glob.glob(ADB_GLOB)) or [p for p in (shutil.which('adb'), shutil.which('adb.exe')) if p]
    if not found:
        raise SystemExit('LỖI: không tìm thấy adb.exe của Arduino App Lab. Mở App Lab một lần, hoặc dùng --adb.')
    return found[-1]


def host_path(path, adb_executable):
    """Đường dẫn mà adb hiểu: adb.exe (Windows) gọi từ WSL cần dạng C:\\..."""
    if str(adb_executable).lower().endswith('.exe') and shutil.which('wslpath'):
        return subprocess.run(['wslpath', '-w', str(path)], capture_output=True, text=True, check=True).stdout.strip()
    return str(path)


class Adb:
    def __init__(self, executable):
        self.executable = executable
        self.env = dict(os.environ)
        # Serial/server mặc định của người gọi không được biến USB thành kết nối ADB từ xa.
        for name in ('ANDROID_SERIAL', 'ANDROID_TRANSPORT_ID', 'ADB_SERVER_SOCKET',
                     'ANDROID_ADB_SERVER_ADDRESS', 'ANDROID_ADB_SERVER_PORT', 'ADB_TRACE'):
            self.env.pop(name, None)

    def run(self, *args, timeout=10):
        try:
            result = subprocess.run([self.executable, *args], capture_output=True, text=True, encoding='utf8',
                                    errors='replace', timeout=timeout, env=self.env)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise LinkError('ADB không chạy được hoặc quá thời gian; kiểm tra cáp USB-C.') from exc
        if result.returncode:
            raise LinkError((result.stderr or result.stdout).strip()[:300] or 'Lệnh ADB lỗi')
        return result.stdout.strip()

    def usb_serial(self):
        serial = self.run('-d', 'get-serialno')   # -d: chỉ thiết bị USB, không Wi-Fi/emulator
        if not serial or serial == 'unknown':
            raise LinkError('Chưa thấy thiết bị USB')
        return serial

    def shell(self, serial, command, timeout=15):
        return self.run('-s', serial, 'shell', command, timeout=timeout)

    def verify_ventuno(self, serial):
        identity = self.shell(serial, 'cat /proc/device-tree/model /proc/device-tree/compatible').lower()
        if 'ventuno q' not in identity and 'arduino,monza' not in identity:
            raise LinkError('Thiết bị USB đang cắm không phải Arduino Ventuno Q.')

    def mappings(self, serial):
        result = {}
        for line in self.run('-s', serial, 'reverse', '--list').splitlines():
            fields = line.split()
            if len(fields) >= 3:
                result[fields[-2]] = fields[-1]
        return result

    def add_reverse(self, serial, remote, local):
        remote, local = f'tcp:{remote}', f'tcp:{local}'
        existing = self.mappings(serial).get(remote)
        if existing is not None:
            if existing != local:
                raise LinkError(f'Cổng {remote} trên board đang được ứng dụng khác dùng.')
            return False
        self.run('-s', serial, 'reverse', '--no-rebind', remote, local)
        return True

    def remove_reverse(self, serial, remote, local):
        remote, local = f'tcp:{remote}', f'tcp:{local}'
        if self.mappings(serial).get(remote) == local:
            self.run('-s', serial, 'reverse', '--remove', remote)

    def push(self, serial, source, destination, timeout=1800):
        """Chép một thư mục/file từ laptop lên board (dùng cho model, vài trăm MB)."""
        return self.run('-s', serial, 'push', host_path(source, self.executable), destination, timeout=timeout)

    def start_python(self, serial, python, source):
        """Chạy `source` bằng `python` trên board, mã nguồn đi qua stdin."""
        process = subprocess.Popen([self.executable, '-s', serial, 'shell', '-T', python, '-u', '-'],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   env=self.env)
        try:
            process.stdin.write(source.encode('utf8'))
            process.stdin.close()
        except (OSError, BrokenPipeError):
            stop_process(process)
            raise LinkError('Không khởi động được runner trên board.')
        return process


class LocalAdb:
    """`--rehearsal`: đóng vai adb, nhưng "board" chính là laptop này (không USB-C, không Ventuno Q, không NPU).

    Mọi thứ khác đi đúng đường board mode: simulator schema v2 thật, bootstrap qua stdin, board_runner.py,
    2 model ONNX thật (cả hai chạy CPU). Dùng để thử trước khi có board; kết quả KHÔNG phải bằng chứng chạy trên board.
    """
    executable = 'laptop (rehearsal)'

    def usb_serial(self):
        return 'LAPTOP-REHEARSAL'

    def verify_ventuno(self, serial):
        pass

    def shell(self, serial, command, timeout=15):
        try:
            result = subprocess.run(['sh', '-c', command], capture_output=True, text=True, encoding='utf8',
                                    errors='replace', timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise LinkError(f'Lệnh kiểm tra trên laptop lỗi: {exc}') from exc
        return result.stdout.strip()

    def add_reverse(self, serial, remote, local):
        return False   # runner nối thẳng 127.0.0.1 của laptop

    def remove_reverse(self, serial, remote, local):
        pass

    def push(self, serial, source, destination, timeout=1800):
        raise LinkError('--push-models không dùng với --rehearsal (model lấy từ C:\\RobotArm trên laptop).')

    def start_python(self, serial, python, source):
        process = subprocess.Popen([python, '-u', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)
        process.stdin.write(source.encode('utf8'))
        process.stdin.close()
        return process


def stop_process(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def port_owner(port):
    """'PID 123: python app.py ...' của tiến trình đang nghe cổng TCP này (Linux/WSL), hoặc ''."""
    try:
        out = subprocess.run(['ss', '-ltnpH', f'sport = :{port}'], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ''
    for token in out.replace(',', ' ').split():
        if token.startswith('pid='):
            pid = token[4:]
            try:
                command = Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
            except OSError:
                command = '?'
            return f'PID {pid}: {command.strip()[:160]}'
    return ''


def read_state(port):
    opener = build_opener(ProxyHandler({}))   # request nội bộ không đi qua proxy
    with opener.open(f'http://127.0.0.1:{port}/api/state', timeout=2) as response:
        return json.load(response)


class BoardSession:
    def __init__(self, adb, board_dir=BOARD_DIR, board_python=BOARD_PYTHON, tcp_port=5050, web_port=8000,
                 board_web_port=BOARD_WEB_PORT, runner_config=None, root=ROOT, viewer=True, push_models=False,
                 arm_python=ARM_PYTHON, models=MODELS, rehearsal=False, runtime=None):
        self.adb, self.root = adb, Path(root)
        self.runtime = Path(runtime) if runtime else self.root / 'runtime'
        self.where = 'Laptop' if rehearsal else 'Board'
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.board_dir = board_dir.rstrip('/')
        self.board_python_dir = f'{self.board_dir}/python'
        self.python = board_python
        self.arm_python, self.models = Path(arm_python), Path(models)
        self.tcp_port, self.web_port, self.board_web_port = tcp_port, web_port, board_web_port
        self.runner_config = dict(runner_config or {})
        self.viewer, self.push_models, self.rehearsal = viewer, push_models, rehearsal
        if rehearsal:
            self.runner_config['rehearsal'] = True
        self.stop_event = threading.Event()
        self.serial = self.simulator = self.runner = self.sim_log = None
        self.owned_mappings = []
        self.summary = None
        self.lost_usb = False
        self.token = secrets.token_urlsafe(32)
        self.token_path = self.runtime / '.board-token'
        fd = os.open(self.token_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w', encoding='utf8') as stream:
            stream.write(self.token + '\n')
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        self.run_dir = self.runtime / 'board-runs'
        self.run_dir.mkdir(exist_ok=True)
        label = f'{stamp}-rehearsal' if rehearsal else stamp   # tên file tách lượt diễn tập khỏi lượt chạy board
        self.runner_log_path = self.run_dir / f'{label}-runner.log'
        self.summary_path = self.run_dir / f'{label}-summary.json'

    # 1. board
    def wait_for_board(self):
        announced = False
        while not self.stop_event.is_set():
            try:
                serial = self.adb.usb_serial()
                self.adb.verify_ventuno(serial)
                self.serial = serial
                return True
            except LinkError as exc:
                if not announced:
                    say('Đang chờ Ventuno Q qua USB-C (cấp nguồn board, đợi Linux khởi động, cắm cáp dữ liệu)...')
                    announced = True
                if 'không phải Arduino Ventuno Q' in str(exc):
                    say('LỖI: ' + str(exc))
                    return False
            self.stop_event.wait(1)
        return False

    # 2. simulation + đường nối
    def start_simulator(self):
        for port in (self.tcp_port, self.web_port):
            with socket.socket() as check:
                # Giống HTTPServer/ThreadTCP của app.py: kết nối TIME_WAIT của phiên vừa tắt không tính là bận,
                # chỉ báo bận khi thật sự có chương trình đang nghe cổng này.
                check.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    check.bind(('127.0.0.1', port))
                except OSError as exc:
                    owner = port_owner(port)
                    hint = ''
                    if owner:
                        pid = owner.split(':')[0].split()[1]
                        old_sim = 'app.py' in owner and '--mode board' in owner and '--token-file' in owner
                        hint = (f'\n   Đang giữ cổng: {owner}'
                                + ('\n   Đây là simulation board mode cũ còn sót lại.' if old_sim else '')
                                + f'\n   Tắt nó: Ctrl+C ở cửa sổ đang chạy, hoặc `kill {pid}`')
                    if not owner:
                        hint = ('\n   Không thấy chương trình nào trong WSL. Nếu WSL dùng networking mirrored, có thể là '
                                f'chương trình Windows: chạy `netstat -ano | findstr :{port}` trong PowerShell.')
                    raise LinkError(f'Cổng {port} đang bận, không mở được simulation mới.{hint}') from exc
        self.sim_log = (self.runtime / 'board_simulator.log').open('a', encoding='utf8')
        env = dict(os.environ, MUJOCO_GL='egl', PYTHONUNBUFFERED='1')
        server = self.root / 'board_server'
        self.simulator = subprocess.Popen(
            [sys.executable, '-B', str(server / 'app.py'), '--mode', 'board', '--token-file', str(self.token_path),
             '--tcp-port', str(self.tcp_port), '--web-port', str(self.web_port)]
            + ([] if self.viewer else ['--no-viewer']),
            cwd=server, env=env, stdout=self.sim_log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and not self.stop_event.is_set():
            if self.simulator.poll() is not None:
                raise LinkError('Simulation không khởi động được. Xem runtime/board_simulator.log.')
            try:
                if read_state(self.web_port).get('mode') == 'board':
                    return
            except (OSError, ValueError):
                pass
            self.stop_event.wait(0.25)
        raise LinkError('Simulation khởi động quá lâu. Xem runtime/board_simulator.log.')

    def link(self):
        for remote, local in ((self.tcp_port, self.tcp_port), (self.board_web_port, self.web_port)):
            if self.adb.add_reverse(self.serial, remote, local):
                self.owned_mappings.append((remote, local))

    # 3. Python + model trên board
    def model_roots(self):
        if self.rehearsal:
            return (str(self.models), f'{self.board_python_dir}/ai')
        return (f'{self.board_python_dir}/ai', '/home/arduino')

    def find_board_models(self):
        q = shlex.quote
        checks = '; '.join(
            '(' + ' && '.join(f'test -f {q(root + "/" + name)}' for name in MODEL_FILES)
            + f' && ls {q(root)}/smolvla_w8a16/denoise_core_*.onnx >/dev/null 2>&1 && echo MODELS_AT={root})'
            for root in self.model_roots())
        out = self.adb.shell(self.serial, checks + '; true')
        for line in out.splitlines():
            if line.startswith('MODELS_AT='):
                return line.split('=', 1)[1].strip()
        return None

    def check_board(self):
        q = shlex.quote
        fake = bool(self.runner_config.get('fake_model'))
        out = self.adb.shell(self.serial, f'test -x {q(self.python)} && echo HAS_PYTHON; true')
        if 'HAS_PYTHON' not in out:
            raise LinkError(f'Trên board không có Python của model: {self.python}\n'
                            '   Dùng --board-python <đường dẫn venv có onnxruntime-qnn>.')
        if fake:
            return
        probe = ('import json, numpy, PIL, tokenizers, onnxruntime as o; '
                 'print("PROVIDERS=" + json.dumps(o.get_available_providers()))')
        out = self.adb.shell(self.serial, f'{q(self.python)} -c {q(probe)} 2>&1; true', timeout=60)
        providers = next((line[10:] for line in out.splitlines() if line.startswith('PROVIDERS=')), None)
        if providers is None:
            raise LinkError(f'Python trên {self.where.lower()} thiếu thư viện (cần numpy, Pillow, tokenizers, onnxruntime):\n   '
                            + out.strip()[-300:])
        if self.runner_config.get('core_provider', 'qnn') == 'qnn' and 'QNNExecutionProvider' not in providers:
            raise LinkError(f'onnxruntime trên board không có QNNExecutionProvider ({providers}).\n'
                            '   Dùng venv có onnxruntime-qnn, hoặc thử --core-provider cpu.')
        say(f'{self.where}: Python OK, providers {providers}')
        root = self.find_board_models()
        if root is None and self.push_models:
            destination = self.model_roots()[0]
            say(f'Đang chép 2 gói model (khoảng 684 MB) lên board: {destination} ... (vài phút)')
            self.adb.shell(self.serial, f'mkdir -p {q(destination)}')
            for name in MODEL_DIRS:
                self.adb.push(self.serial, self.models / name, destination + '/')
            root = self.find_board_models()
        if root is None:
            raise LinkError('Trên board chưa có model (smolvla_prefix/ và smolvla_w8a16/) ở:\n   '
                            + '\n   '.join(self.model_roots())
                            + '\n   Chạy lại với --push-models để chép từ C:\\RobotArm\\ai (một lần, vài phút).')
        say(f'{self.where}: model ở {root}')
        self.runner_config['model_root'] = root

    def stop_board_runner(self):
        """Dừng runner trên board (cũng dọn runner sót lại từ lần trước)."""
        if not self.serial:
            return
        try:
            self.adb.shell(self.serial,
                           f'p=$(cat {RUNNER_PID_FILE} 2>/dev/null); '
                           '[ -n "$p" ] && grep -q python /proc/$p/cmdline 2>/dev/null && kill $p; true', timeout=10)
        except LinkError:
            pass   # rút USB-C thì runner cũng mất stdout và tự dừng

    # 4. chạy model
    def start_runner(self):
        sys.path.insert(0, str(self.arm_python))
        import board_runner
        config = {'sim_port': self.tcp_port, 'web_port': self.board_web_port, **self.runner_config}
        self.stop_board_runner()
        source = board_runner.bootstrap_source(self.token, config, self.board_python_dir, self.arm_python)
        self.runner = self.adb.start_python(self.serial, self.python, source)
        threading.Thread(target=self._pump, args=(self.runner,), daemon=True, name='runner-output').start()

    def _pump(self, process):
        with self.runner_log_path.open('a', encoding='utf8') as log:
            for raw in iter(process.stdout.readline, b''):
                line = raw.decode('utf8', 'replace').rstrip()
                log.write(f'{datetime.now():%H:%M:%S} {line}\n')
                log.flush()
                if line.startswith('SUMMARY '):
                    try:
                        self.summary = json.loads(line[8:])
                        self.summary_path.write_text(json.dumps(self.summary, ensure_ascii=False, indent=1) + '\n',
                                                     encoding='utf8')
                    except ValueError:
                        pass
                elif not line.startswith('RUNNER_PID'):
                    say('[board] ' + line)
        process.stdout.close()

    def run(self):
        try:
            if not self.wait_for_board():
                return 1
            say('DIỄN TẬP TRÊN LAPTOP: không dùng board, cả hai model chạy CPU. Đang mở simulation...' if self.rehearsal
                else f'Đã thấy Ventuno Q ({self.serial}). Đang mở simulation...')
            self.start_simulator()
            self.link()
            say(f'SIMULATION SẴN SÀNG. Dashboard: http://localhost:{self.web_port}')
            self.check_board()
            say('Đang khởi động board_runner.py ngay trên laptop (prefix CPU + core CPU)...' if self.rehearsal
                else 'Đang khởi động model trên Ventuno Q (prefix CPU + core NPU, không qua STM32)...')
            self.start_runner()
            while not self.stop_event.is_set():
                if self.simulator.poll() is not None:
                    raise LinkError('Simulation đã dừng (đóng cửa sổ MuJoCo cũng tắt simulation). '
                                    'Xem runtime/board_simulator.log.')
                if self.runner is not None and self.runner.poll() is not None:
                    self.runner = None
                    self.report()
                try:
                    if self.adb.usb_serial() != self.serial:
                        raise LinkError('USB đổi thiết bị')
                except LinkError:
                    if not self.lost_usb:
                        self.lost_usb = True
                        say('MẤT USB-C: model dừng, simulation giữ HOLD và không tự chạy lại. '
                            'Ctrl+C rồi gõ lại lệnh để chạy lượt mới.')
                self.stop_event.wait(1)
            return 0 if (self.summary or {}).get('all_cycles_completed') else 1
        except LinkError as exc:
            say(f'LỖI: {exc}')
            return 1
        finally:
            self.close()

    def report(self):
        if self.summary is None:
            say(f'Runner đã thoát mà không có kết quả. Log: {self.runner_log_path}')
        else:
            verdict = 'XONG' if self.summary.get('all_cycles_completed') else 'DỪNG GIỮA CHỪNG'
            episode = (self.summary.get('episode') or {}).get('status')
            say(('[DIỄN TẬP] ' if self.rehearsal else '')
                + f"{verdict}: {self.summary.get('targets_executed', 0)} target từ model đã chạy trong simulation"
                + (f' (lượt chạy: {episode})' if episode else '')
                + f'. Kết quả: {self.summary_path}')
        say('Dashboard vẫn mở để xem lại. Ctrl+C để tắt.')

    def close(self):
        if self.runner is not None:
            self.stop_board_runner()
            stop_process(self.runner)
            self.runner = None
        for remote, local in self.owned_mappings:
            try:
                self.adb.remove_reverse(self.serial, remote, local)
            except LinkError:
                pass   # rút USB-C đã xóa luôn reverse
        self.owned_mappings.clear()
        stop_process(self.simulator)
        if self.sim_log:
            self.sim_log.close()
            self.sim_log = None


def wants_board_mode(argv):
    """`app.py --mode board` do người gõ (không có --token-file) nghĩa là chạy file này."""
    board = '--mode=board' in argv or any(a == '--mode' and argv[i + 1:i + 2] == ['board'] for i, a in enumerate(argv))
    return board and not any(a.split('=')[0] == '--token-file' for a in argv)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='app.py --mode board', description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--mode', choices=('board',), required=True)
    parser.add_argument('--cycles', type=int, default=3, help='số vòng quan sát -> suy luận -> chạy (1..200), mặc định 3')
    parser.add_argument('--k', type=int, default=25, help='số target (30 Hz) chạy từ mỗi chunk 50 bước (1..50), mặc định 25')
    parser.add_argument('--task', default='Pick up the red ball and place it in the box.')
    parser.add_argument('--target', choices=BALLS, default='red_ball', help='bóng mà simulator chấm điểm')
    parser.add_argument('--seed', type=int, default=0, help='seed của RESET')
    parser.add_argument('--think', choices=('hold', 'live'), default='hold',
                        help='hold: simulation dừng khi model suy nghĩ (đã chạy thật 09/11); '
                             'live: thời gian vẫn chạy và simulator chấm được SUCCESS/FAILURE')
    parser.add_argument('--core-provider', choices=('qnn', 'cpu'), default='qnn',
                        help='denoise core chạy trên NPU (qnn) hay CPU của board')
    parser.add_argument('--board-python', default=BOARD_PYTHON, help=f'Python trên board (mặc định {BOARD_PYTHON})')
    parser.add_argument('--board-dir', default=BOARD_DIR, help=f'thư mục app trên board (mặc định {BOARD_DIR})')
    parser.add_argument('--rehearsal', action='store_true',
                        help='diễn tập không cần board: runner + 2 model ONNX chạy CPU ngay trên laptop, '
                             'simulator và giao thức y như board mode (không ADB, không NPU)')
    parser.add_argument('--push-models', action='store_true',
                        help='nếu board chưa có model: chép C:\\RobotArm\\ai lên <board-dir>/python/ai')
    parser.add_argument('--web-port', type=int, default=8000)
    parser.add_argument('--no-viewer', action='store_true', help='không mở cửa sổ MuJoCo, chỉ xem trên dashboard')
    parser.add_argument('--adb', help='đường dẫn adb.exe (mặc định: bản đi kèm Arduino App Lab)')
    parser.add_argument('--fake-model', action='store_true', help=argparse.SUPPRESS)   # chỉ để test
    args = parser.parse_args(argv)
    if not 1 <= args.cycles <= 200 or not 1 <= args.k <= 50 or not 0 <= args.seed < 2**32:
        parser.error('--cycles 1..200, --k 1..50, --seed uint32')
    for label, value in (('--board-dir', args.board_dir), ('--board-python', args.board_python)):
        if not value.startswith('/') or any(c in value for c in ' \n\r\'"'):
            parser.error(f'{label} phải là đường dẫn Linux tuyệt đối, không có dấu cách/nháy')
    runner_config = {'cycles': args.cycles, 'k': args.k, 'task': args.task, 'target': args.target, 'seed': args.seed,
                     'think': args.think, 'core_provider': args.core_provider, 'fake_model': args.fake_model}
    if args.rehearsal:
        if args.push_models:
            parser.error('--push-models không dùng với --rehearsal')
        runner_config['core_provider'] = 'cpu'   # laptop không có NPU
        # "Board" = laptop: Python đang chạy lệnh này, code ở so101arm/python (bootstrap thấy file trùng, không ghi gì).
        session = BoardSession(LocalAdb(), board_dir=str(ARM_PYTHON.parent), board_python=sys.executable,
                               web_port=args.web_port, board_web_port=args.web_port, viewer=not args.no_viewer,
                               runner_config=runner_config, rehearsal=True)
        print('SO101 board mode | DIỄN TẬP TRÊN LAPTOP (không board, không NPU) | Python: ' + sys.executable, flush=True)
    else:
        adb_path = find_adb(args.adb)
        session = BoardSession(Adb(adb_path), board_dir=args.board_dir, board_python=args.board_python,
                               web_port=args.web_port, viewer=not args.no_viewer, push_models=args.push_models,
                               runner_config=runner_config)
        print(f'SO101 board mode | ADB: {adb_path} | board: {args.board_python} | {args.board_dir}', flush=True)
    print('Ctrl+C để tắt. Log: runtime/board_simulator.log, runtime/board-runs/', flush=True)
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: session.stop_event.set())
    return session.run()


if __name__ == '__main__':
    sys.exit(main())
