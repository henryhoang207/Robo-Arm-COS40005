#!/usr/bin/env python3
"""Copy C:\\RobotArm\\robo-arm (firmware + bridge + model runner) into ~/ArduinoApps/robo-arm on the board.

Run in WSL with the board on USB-C:   python upload_board_app.py   [--mode smoke] [--cycles 1]

- Only app.yaml, config.json, python/*.py, python/requirements.txt and sketch/* are written.
  smol/ (the model), data and caches on the board are never touched.
- The previous app.yaml/config.json/python/sketch are copied to .backup-<time>/ first.
- Every file is checked with SHA-256 after the copy.
- Nothing is started or flashed here: open "Robo Arm" in App Lab and press Run.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
LOCAL_APP = ROOT.parent / 'robo-arm'
sys.path.insert(0, str(ROOT))
from board_mode import DEFAULT_BOARD_APP, find_adb   # noqa: E402
from usb_board_mode import Adb, LinkError           # noqa: E402

MODES = ('policy', 'smoke', 'probe', 'direct')


def app_files():
    files = ['app.yaml', 'config.json', 'python/requirements.txt']
    files += sorted(p.relative_to(LOCAL_APP).as_posix() for p in (LOCAL_APP / 'python').glob('*.py'))
    files += sorted(p.relative_to(LOCAL_APP).as_posix() for p in (LOCAL_APP / 'sketch').iterdir() if p.is_file())
    return files


def windows_path(path, adb_path):
    if not adb_path.lower().endswith('.exe'):
        return str(path)
    return subprocess.check_output(['wslpath', '-w', str(path)], text=True).strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--board-app', default=DEFAULT_BOARD_APP)
    parser.add_argument('--adb')
    parser.add_argument('--mode', choices=MODES, help='write this mode into config.json on the board')
    parser.add_argument('--cycles', type=int, help='write this number of model cycles (1..20)')
    args = parser.parse_args(argv)
    if args.cycles is not None and not 1 <= args.cycles <= 20:
        parser.error('--cycles must be 1..20')
    app = args.board_app.rstrip('/')
    if not app.startswith('/') or any(c in app for c in ' \n\r\'"'):
        parser.error('--board-app must be an absolute Linux path without spaces/quotes')
    adb_path = find_adb(args.adb)
    adb = Adb(adb_path)
    try:
        serial = adb.usb_serial()
        adb.verify_ventuno(serial)
    except LinkError as exc:
        raise SystemExit(f'LỖI: không thấy Ventuno Q qua USB-C ({exc}).')
    shell = lambda command, timeout=60: adb.run('-s', serial, 'shell', command, timeout=timeout)   # noqa: E731
    q = shlex.quote(app)
    if 'YES' not in shell(f'test -d {q} && echo YES || echo NO'):
        raise SystemExit(f'LỖI: trên board không có {app}. Tạo app "Robo Arm" trong App Lab trước '
                         '(hoặc dùng --board-app).')
    if 'YES' not in shell(f'test -d {q}/smol && echo YES || echo NO'):
        print(f'CẢNH BÁO: không thấy {app}/smol (model SmolVLA). Mode probe/smoke vẫn chạy được.')

    config = json.loads((LOCAL_APP / 'config.json').read_text(encoding='utf8'))
    if args.mode:
        config['mode'] = args.mode
    if args.cycles:
        config['cycles'] = args.cycles
    with tempfile.TemporaryDirectory(dir=ROOT / 'runtime') as staging:
        staged_config = Path(staging) / 'config.json'
        staged_config.write_text(json.dumps(config, indent=2) + '\n', encoding='utf8')
        sources = {rel: (staged_config if rel == 'config.json' else LOCAL_APP / rel) for rel in app_files()}

        backup = f'{app}/.backup-{datetime.now():%Y%m%d-%H%M%S}'
        shell(f'mkdir -p {shlex.quote(backup)} && cd {q} && '
              f'for f in app.yaml config.json python sketch; do [ -e "$f" ] && cp -a "$f" {shlex.quote(backup)}/; done; '
              f'mkdir -p python sketch runtime; true')
        print(f'Đã sao lưu app cũ vào {backup}')
        for rel, source in sources.items():
            adb.run('-s', serial, 'push', windows_path(source, adb_path), f'{app}/{rel}', timeout=120)
        remote = shell(f'cd {q} && sha256sum ' + ' '.join(shlex.quote(r) for r in sources))
        for rel, source in sources.items():
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            if not any(line.startswith(digest) and line.endswith(rel) for line in remote.splitlines()):
                raise SystemExit(f'LỖI: SHA-256 khác nhau trên board: {rel}')
    print(f'Đã chép {len(sources)} file vào {app}, SHA-256 khớp. config.json: mode={config["mode"]}, '
          f'cycles={config["cycles"]}')
    print('Tiếp theo: python app.py --mode board (laptop), rồi App Lab -> "Robo Arm" -> Run.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
