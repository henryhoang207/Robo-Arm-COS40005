"""Board mode không cần board thật: runner (../so101arm/python/board_runner.py) + điều phối laptop (board_mode.py).

- FakeSimulator: TCP schema v2 + HTTP /api/observation tối giản, chuyển động tức thì, kiểm tra ACTION_CHUNK
  theo đúng luật của simulator thật (giới hạn khớp, tốc độ, thời gian tăng dần).
- FakeAdb: thay adb.exe; "board" là chính máy này, runner chạy bằng Python hiện tại qua stdin
  (đúng đường đi thật: bootstrap_source -> python -u -).
- RealSimulatorRunnerTest: runner với model giả chạy vào MuJoCo thật (bỏ qua nếu không có mujoco).
Không có onnxruntime, không có STM32.

    cd so101sim && python -B -m unittest tests.test_board_mode -v
"""
import contextlib
import io
import json
from pathlib import Path
import secrets
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]              # so101sim
ARM_PYTHON = ROOT.parent / 'so101arm' / 'python'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ARM_PYTHON))
import board_mode   # noqa: E402
import board_runner   # noqa: E402

TOKEN = 'x' * 32
LIMITS = [[-1.91986, 1.91986], [-1.74533, 1.74533], [-1.69, 1.69], [-1.65806, 1.65806], [-2.74385, 2.84121],
          [-0.17453, 1.74533]]
SPEEDS = (2.0, 2.0, 2.0, 3.0, 3.0, 4.0)


class Alive:
    """Thay tiến trình simulation (đã có FakeSimulator chạy trong test)."""
    def poll(self):
        return None

    def terminate(self):
        pass

    def wait(self, timeout=None):
        return 0


def chunk_error(points, previous):
    """Luật ACTION_CHUNK của board_server (protocol.parse_action + engine._validate_speed_locked)."""
    if not isinstance(points, list) or not 1 <= len(points) <= 64:
        return 'points must contain 1..64 timed setpoints'
    last_t = 0.0
    for point in points:
        when, targets = point['time_from_start'], point['joint_targets']
        if not 0.01 <= when <= 10.0 or when - last_t < 0.01 - 1e-9:
            return 'bad time_from_start'
        if len(targets) != 6 or any(not lo <= v <= hi for v, (lo, hi) in zip(targets, LIMITS)):
            return 'target outside joint limits'
        if any(abs(a - b) / (when - last_t) > v + 1e-8 for a, b, v in zip(targets, previous, SPEEDS)):
            return 'Chunk exceeds configured target speed'
        previous, last_t = targets, when
    return None


class FakeSimulator:
    def __init__(self, token=TOKEN):
        self.token = token
        self.lock = threading.Lock()
        self.run_id, self.session = 'run-0', 0
        self.joints = [0.0, -0.2, 0.3, 0.1, 0.0, 0.5]
        self.hold, self.accepted, self.completed = False, -1, -1
        self.commands, self.pings = [], 0
        self.episode = {'status': 'READY', 'reason': None}
        self.no_frame_until = 0.0   # như MuJoCo: ngay sau RESET chưa có cặp ảnh -> 503
        sim = self

        class Tcp(socketserver.StreamRequestHandler):
            def handle(self):
                hello = json.loads(self.rfile.readline())
                if hello.get('token') != sim.token:
                    self.send({'type': 'ERROR', 'reason': 'Authentication failed'})
                    return
                with sim.lock:
                    sim.session += 1
                    session = f's{sim.session}'
                self.send({'type': 'WELCOME', 'schema_version': 2, 'run_id': sim.run_id, 'session_id': session,
                           'requires_resume': sim.hold, 'accepted_sequence': sim.accepted})
                try:
                    for line in self.rfile:
                        self.send(sim.handle(json.loads(line), session))
                finally:
                    with sim.lock:   # mất phiên -> HOLD + lượt chạy ABORTED, giống simulator thật
                        sim.hold = True
                        if sim.episode['status'] in ('READY', 'RUNNING'):
                            sim.episode = {'status': 'ABORTED', 'reason': 'CONNECTION_LOST'}

            def send(self, obj):
                self.wfile.write((json.dumps(obj) + '\n').encode())
                self.wfile.flush()

        class Http(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                if self.path == '/api/observation' and time.monotonic() < sim.no_frame_until:
                    self.send_response(503)
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                if self.path == '/api/observation':
                    body = {'image_encoding': 'jpeg/base64', 'stale': False, 'run_id': sim.run_id, 'frame_id': 1,
                            'sim_time': 0.0, 'joint_positions': list(sim.joints), 'images': {}}
                else:
                    body = {'mode': 'board'}
                data = json.dumps(body).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        socketserver.ThreadingTCPServer.allow_reuse_address = True
        self.tcp = socketserver.ThreadingTCPServer(('127.0.0.1', 0), Tcp)
        self.tcp.daemon_threads = True
        self.http = ThreadingHTTPServer(('127.0.0.1', 0), Http)
        self.http.daemon_threads = True
        for server in (self.tcp, self.http):
            threading.Thread(target=server.serve_forever, daemon=True).start()
        self.tcp_port, self.web_port = self.tcp.server_address[1], self.http.server_address[1]

    def handle(self, obj, session):
        kind = obj.get('type')
        with self.lock:
            if kind == 'PING':
                self.pings += 1
                return {'type': 'PONG', 'hold_latched': self.hold, 'run_id': self.run_id, 'session_id': session}
            if kind == 'GET_STATE':
                return {'type': 'STATE', 'schema_version': 2, 'run_id': self.run_id, 'session_id': session,
                        'joint_positions': list(self.joints), 'joint_limits': LIMITS, 'hold_latched': self.hold,
                        'fault': None, 'completed_sequence': self.completed, 'accepted_sequence': self.accepted,
                        'completion_reason': 'TARGET_REACHED' if self.completed >= 0 else None,
                        'sim_time': 0.0, 'episode': dict(self.episode)}
            if (obj.get('schema_version'), obj.get('run_id'), obj.get('session_id')) != (2, self.run_id, session):
                return {'type': 'REJECTED', 'reason': 'stale context'}
            self.commands.append(obj)
            if kind == 'RESET':
                self.run_id = f'run-{len(self.commands)}'
                self.no_frame_until = time.monotonic() + 0.6
                self.hold, self.accepted, self.completed = False, -1, -1
                self.episode = {'status': 'READY', 'reason': None}
                return {'type': 'ACK', 'run_id': self.run_id}
            if kind == 'RESUME':
                self.hold = False
            elif kind == 'ABORT':
                self.hold = True
                if self.episode['status'] in ('READY', 'RUNNING'):
                    self.episode = {'status': 'ABORTED', 'reason': 'USER_ABORT'}
            elif kind == 'ACTION_CHUNK':
                if self.hold or obj['sequence_id'] <= self.accepted:
                    return {'type': 'REJECTED', 'reason': 'hold or replay'}
                error = chunk_error(obj.get('points'), list(self.joints))
                if error:
                    return {'type': 'REJECTED', 'reason': error}
                self.joints = list(obj['points'][-1]['joint_targets'])
                self.accepted = self.completed = obj['sequence_id']
                if self.episode['status'] == 'READY':
                    self.episode = {'status': 'RUNNING', 'reason': None}
            elif kind == 'ACTION':
                return {'type': 'REJECTED', 'reason': 'runner must send ACTION_CHUNK'}
            return {'type': 'ACK'}

    def close(self):
        for server in (self.tcp, self.http):
            server.shutdown()
            server.server_close()


class FakeAdb:
    """adb.exe giả: board = máy này, runner chạy bằng sys.executable."""
    def __init__(self, has_python=True):
        self.calls, self.reverses = [], {}
        self.has_python = has_python

    def usb_serial(self):
        return 'FAKE123'

    def verify_ventuno(self, serial):
        self.calls.append('verify')

    def shell(self, serial, command, timeout=15):
        self.calls.append(command)
        if 'HAS_PYTHON' in command:
            return 'HAS_PYTHON\n' if self.has_python else ''
        return ''

    def add_reverse(self, serial, remote, local):
        self.reverses[remote] = local
        return True

    def remove_reverse(self, serial, remote, local):
        self.reverses.pop(remote, None)

    def start_python(self, serial, python, source):
        self.calls.append(('python', python))
        process = subprocess.Popen([sys.executable, '-u', '-'], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        process.stdin.write(source.encode())
        process.stdin.close()
        return process


class ArgsTests(unittest.TestCase):
    def test_typed_board_command_goes_to_board_mode(self):
        self.assertTrue(board_mode.wants_board_mode(['--mode', 'board']))
        self.assertTrue(board_mode.wants_board_mode(['--mode=board', '--cycles', '1']))
        self.assertFalse(board_mode.wants_board_mode(['--mode', 'board', '--token-file', 't']))
        self.assertFalse(board_mode.wants_board_mode(['--mode', 'local']))
        self.assertFalse(board_mode.wants_board_mode([]))


class ChunkTests(unittest.TestCase):
    def test_slow_targets_keep_30hz(self):
        start = [0.0, -0.2, 0.3, 0.1, 0.0, 0.5]
        rows = [[0.01 * (i + 1), -0.2, 0.3, 0.1, 0.0, 0.5] for i in range(25)]
        points, clipped, duration = board_runner.build_chunk(rows, start, LIMITS)
        self.assertEqual((len(points), clipped), (25, 0))
        self.assertAlmostEqual(duration, 25 * 0.034, places=6)   # 1/30 s làm tròn lên tới ms
        self.assertIsNone(chunk_error(points, start))

    def test_far_or_out_of_range_targets_are_clipped_and_slowed(self):
        start = [0.0, -0.2, 0.3, 0.1, 0.0, 0.5]
        rows = [[0.5, -0.2, 0.3, 0.1, 0.0, 0.5], [0.5, -3.0, 0.3, 0.1, 0.0, 2.5]]
        points, clipped, duration = board_runner.build_chunk(rows, start, LIMITS)
        self.assertEqual(clipped, 1)
        self.assertGreater(points[0]['time_from_start'], 0.5 / 2.0)   # 0,5 rad ở tối đa 2 rad/s
        self.assertIsNone(chunk_error(points, start))
        self.assertLess(points[1]['joint_targets'][5], LIMITS[5][1])

    def test_unreachable_chunk_is_refused(self):
        rows = [[1.9 * (-1) ** i, 0, 0, 0, 0, 0] for i in range(12)]
        with self.assertRaises(RuntimeError):
            board_runner.build_chunk(rows, [0.0] * 6, LIMITS)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.sim = FakeSimulator()
        self.config = {'fake_model': True, 'cycles': 2, 'k': 10, 'link_timeout_s': 5,
                       'sim_port': self.sim.tcp_port, 'web_port': self.sim.web_port}

    def tearDown(self):
        self.sim.close()

    def run_runner(self, config, token=TOKEN):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = board_runner.main(token, config)
        lines = output.getvalue().splitlines()
        summary = json.loads(next(l for l in lines if l.startswith('SUMMARY '))[8:])
        return code, summary, lines

    def test_model_chunks_reach_simulator_without_mcu(self):
        code, summary, lines = self.run_runner(self.config)
        self.assertEqual(code, 0, lines)
        self.assertTrue(summary['all_cycles_completed'])
        self.assertFalse(summary['mcu_involved'])
        chunks = [c for c in self.sim.commands if c['type'] == 'ACTION_CHUNK']
        self.assertEqual([c['sequence_id'] for c in chunks], [0, 1])
        self.assertEqual([len(c['points']) for c in chunks], [10, 10])
        self.assertEqual(summary['targets_executed'], 20)
        self.assertAlmostEqual(self.sim.joints[0], 0.10, places=5)
        self.assertEqual(self.sim.commands[0]['type'], 'RESET')
        self.assertIn('RESUME', [c['type'] for c in self.sim.commands])   # HOLD trong lúc model suy nghĩ
        self.assertEqual(summary['cycles'][0]['completion'], 'TARGET_REACHED')
        self.assertEqual(self.sim.pings, 0)
        self.assertTrue(any(l.startswith('DONE') for l in lines))

    def test_live_mode_keeps_one_session_and_the_episode_running(self):
        def slow(config):
            infer, info = fake(config)

            def wrapped(packet, images):
                time.sleep(1.3)   # đủ lâu để phải có PING
                return infer(packet, images)
            return wrapped, info
        fake = board_runner.make_fake_infer
        with patch.object(board_runner, 'make_fake_infer', slow):
            code, summary, lines = self.run_runner(dict(self.config, think='live'))
        self.assertEqual(code, 0, lines)
        self.assertEqual(self.sim.session, 2)   # 1 phiên thử nối + 1 phiên cho cả lượt chạy
        self.assertGreaterEqual(self.sim.pings, 2)
        self.assertNotIn('RESUME', [c['type'] for c in self.sim.commands])
        self.assertEqual(summary['cycles'][-1]['episode']['status'], 'RUNNING')
        self.assertEqual([c['type'] for c in self.sim.commands].count('ABORT'), 1)   # chỉ khi kết thúc

    def test_wrong_token_stops_without_motion(self):
        code, summary, lines = self.run_runner(dict(self.config, link_timeout_s=1), token='wrong-token-wrong-token')
        self.assertEqual(code, 1)
        self.assertEqual(self.sim.commands, [])
        self.assertTrue(any(l.startswith('STOPPED') for l in lines))

    def test_moved_arm_is_stale_and_stops(self):
        fake = board_runner.make_fake_infer

        def moving(config):
            infer, info = fake(config)

            def wrapped(packet, images):
                self.sim.joints[1] += 0.1   # tay robot bị đẩy trong lúc model suy nghĩ
                return infer(packet, images)
            return wrapped, info
        with patch.object(board_runner, 'make_fake_infer', moving):
            code, summary, _ = self.run_runner(self.config)
        self.assertEqual(code, 1)
        self.assertIn('Quan sát đã cũ', summary['cycles'][0]['error'])
        self.assertEqual([c for c in self.sim.commands if c['type'] == 'ACTION_CHUNK'], [])

    def test_bootstrap_keeps_token_out_of_argv_and_deploys_code(self):
        with tempfile.TemporaryDirectory() as directory:
            source = board_runner.bootstrap_source(TOKEN, dict(self.config, cycles=1), directory)
            self.assertIn(repr(TOKEN), source.splitlines()[-1])
            process = subprocess.run([sys.executable, '-u', '-'], input=source.encode(), capture_output=True,
                                     timeout=60)
            text = process.stdout.decode()
            self.assertEqual(process.returncode, 0, text + process.stderr.decode())
            for name in board_runner.DEPLOYED_FILES:
                self.assertEqual((Path(directory) / name).read_bytes(), (ARM_PYTHON / name).read_bytes())
                self.assertIn(f'DEPLOYED {name}', text)
            self.assertNotIn(TOKEN, text)


class BoardSessionTests(unittest.TestCase):
    def test_one_command_runs_model_on_board_into_simulation(self):
        sim = FakeSimulator()
        adb = FakeAdb()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'so101sim'
            root.mkdir()
            session = board_mode.BoardSession(adb, tcp_port=sim.tcp_port, web_port=sim.web_port,
                                              board_web_port=sim.web_port, root=root,
                                              board_dir=str(Path(directory) / 'board-app'), board_python='/venv/python',
                                              runner_config={'fake_model': True, 'cycles': 1, 'k': 5,
                                                             'link_timeout_s': 5})
            sim.token = session.token   # token phiên do board_mode tạo
            session.simulator = Alive()
            session.start_simulator = lambda: None
            result = {}
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                worker = threading.Thread(target=lambda: result.setdefault('code', session.run()))
                worker.start()
                deadline = time.monotonic() + 30
                while session.summary is None and time.monotonic() < deadline:
                    time.sleep(0.1)
                time.sleep(1.5)   # vòng giám sát in báo cáo
                session.stop_event.set()
                worker.join(10)
            sim.close()
            text = output.getvalue()
            self.assertEqual(result.get('code'), 0, text)
            self.assertTrue(session.summary['all_cycles_completed'])
            self.assertTrue(list((root / 'runtime' / 'board-runs').glob('*-summary.json')))
            self.assertIn('XONG', text)
            self.assertIn(('python', '/venv/python'), adb.calls)
            self.assertTrue((Path(directory) / 'board-app' / 'python' / 'board_runner.py').is_file())
            self.assertEqual(adb.reverses, {})   # đã gỡ reverse khi tắt
            self.assertTrue(any('so101-board-runner.pid' in c for c in adb.calls if isinstance(c, str)))
            self.assertNotIn(session.token, text)

    def test_missing_python_is_reported_before_anything_runs(self):
        adb = FakeAdb(has_python=False)
        with tempfile.TemporaryDirectory() as directory:
            session = board_mode.BoardSession(adb, root=Path(directory))
            session.simulator = Alive()
            session.start_simulator = lambda: None
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(session.run(), 1)
        self.assertIn('không có Python của model', output.getvalue())
        self.assertFalse(any(isinstance(c, tuple) for c in adb.calls))

    def test_missing_models_tell_the_user_how_to_push_them(self):
        class NoModels(FakeAdb):
            def shell(self, serial, command, timeout=15):
                self.calls.append(command)
                if 'HAS_PYTHON' in command:
                    return 'HAS_PYTHON\n'
                if 'PROVIDERS=' in command:
                    return 'PROVIDERS=["QNNExecutionProvider", "CPUExecutionProvider"]\n'
                return ''
        adb = NoModels()
        with tempfile.TemporaryDirectory() as directory:
            session = board_mode.BoardSession(adb, root=Path(directory))
            session.simulator = Alive()
            session.start_simulator = lambda: None
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(session.run(), 1)
        self.assertIn('--push-models', output.getvalue())
        self.assertFalse(any(isinstance(c, tuple) for c in adb.calls))


class RehearsalTests(unittest.TestCase):
    """`--rehearsal`: LocalAdb đóng vai adb, runner chạy ngay trên máy này (ở đây với simulator giả + model giả)."""

    def test_rehearsal_uses_the_board_path_without_adb_and_is_labelled(self):
        sim = FakeSimulator()
        before = {name: (ARM_PYTHON / name).stat().st_mtime_ns for name in board_runner.DEPLOYED_FILES}
        with tempfile.TemporaryDirectory() as directory:
            session = board_mode.BoardSession(board_mode.LocalAdb(), tcp_port=sim.tcp_port, web_port=sim.web_port,
                                              board_web_port=sim.web_port, root=ROOT, runtime=directory,
                                              board_dir=str(ARM_PYTHON.parent), board_python=sys.executable,
                                              runner_config={'fake_model': True, 'cycles': 1, 'k': 5,
                                                             'link_timeout_s': 5}, rehearsal=True)
            sim.token = session.token
            session.simulator = Alive()
            session.start_simulator = lambda: None
            result, output = {}, io.StringIO()
            with contextlib.redirect_stdout(output):
                worker = threading.Thread(target=lambda: result.setdefault('code', session.run()))
                worker.start()
                deadline = time.monotonic() + 30
                while session.summary is None and time.monotonic() < deadline:
                    time.sleep(0.1)
                time.sleep(1.5)
                session.stop_event.set()
                worker.join(10)
            sim.close()
            text = output.getvalue()
            self.assertEqual(result.get('code'), 0, text)
            self.assertEqual(session.summary['mode'], 'laptop_rehearsal_no_board')
            self.assertFalse(session.summary['mcu_involved'])
            self.assertIn('DIỄN TẬP', text)
            self.assertTrue(list((Path(directory) / 'board-runs').glob('*-rehearsal-summary.json')))
            self.assertIn('unchanged', (next((Path(directory) / 'board-runs').glob('*-rehearsal-runner.log'))).read_text())
        after = {name: (ARM_PYTHON / name).stat().st_mtime_ns for name in board_runner.DEPLOYED_FILES}
        self.assertEqual(before, after)   # diễn tập không ghi đè code trong so101arm/python


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


try:
    import mujoco  # noqa: F401
    HAVE_MUJOCO = True
except ImportError:
    HAVE_MUJOCO = False


@unittest.skipUnless(HAVE_MUJOCO, 'cần mujoco (chạy trong venv so101sim)')
class RealSimulatorRunnerTest(unittest.TestCase):
    def run_against_real_server(self, think):
        token = secrets.token_urlsafe(32)
        tcp_port, web_port = free_port(), free_port()
        server = ROOT / 'board_server'
        with tempfile.TemporaryDirectory() as directory:
            token_file = Path(directory) / 'token'
            token_file.write_text(token)
            log = (Path(directory) / 'server.log').open('w')
            process = subprocess.Popen([sys.executable, '-B', str(server / 'app.py'), '--mode', 'board',
                                        '--token-file', str(token_file), '--no-viewer', '--no-logs',
                                        '--tcp-port', str(tcp_port), '--web-port', str(web_port)],
                                       cwd=server, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    try:
                        if board_runner.get_json(web_port, '/api/observation', 2).get('stale') is False:
                            break
                    except (OSError, ValueError):
                        pass
                    time.sleep(0.5)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = board_runner.main(token, {'fake_model': True, 'cycles': 2, 'k': 25, 'think': think,
                                                     'link_timeout_s': 20, 'sim_port': tcp_port, 'web_port': web_port})
                text = output.getvalue()
                self.assertEqual(code, 0, text + '\n' + (Path(directory) / 'server.log').read_text())
                state = board_runner.get_json(web_port, '/api/state')
                self.assertEqual(state['completed_sequence'], 1)
                return json.loads(next(l for l in text.splitlines() if l.startswith('SUMMARY '))[8:])
            finally:
                process.terminate()
                process.wait(10)
                log.close()

    def test_fake_model_drives_real_mujoco_hold(self):
        summary = self.run_against_real_server('hold')
        self.assertEqual(summary['targets_executed'], 50)

    def test_fake_model_drives_real_mujoco_live(self):
        summary = self.run_against_real_server('live')
        self.assertEqual(summary['cycles'][-1]['episode']['status'], 'RUNNING')

    def test_rehearsal_command_starts_the_real_server_and_runs_the_runner(self):
        tcp_port, web_port = free_port(), free_port()
        with tempfile.TemporaryDirectory() as directory:
            session = board_mode.BoardSession(board_mode.LocalAdb(), tcp_port=tcp_port, web_port=web_port,
                                              board_web_port=web_port, root=ROOT, runtime=directory, viewer=False,
                                              board_dir=str(ARM_PYTHON.parent), board_python=sys.executable,
                                              runner_config={'fake_model': True, 'cycles': 2, 'k': 25,
                                                             'link_timeout_s': 30}, rehearsal=True)
            result, output = {}, io.StringIO()
            with contextlib.redirect_stdout(output):
                worker = threading.Thread(target=lambda: result.setdefault('code', session.run()))
                worker.start()
                deadline = time.monotonic() + 120
                while session.summary is None and worker.is_alive() and time.monotonic() < deadline:
                    time.sleep(0.2)
                time.sleep(1.5)
                session.stop_event.set()
                worker.join(20)
            log = Path(directory) / 'board_simulator.log'
            text = output.getvalue() + (log.read_text() if log.is_file() else '')
            self.assertEqual(result.get('code'), 0, text)
            self.assertEqual(session.summary['targets_executed'], 50, text)
            self.assertEqual(session.summary['mode'], 'laptop_rehearsal_no_board')


if __name__ == '__main__':
    unittest.main()
