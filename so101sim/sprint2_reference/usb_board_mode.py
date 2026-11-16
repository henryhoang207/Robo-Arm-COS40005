#!/usr/bin/env python3
"""Run in WSL; use Windows ADB so USB attachment to WSL is unnecessary.

Only a physical USB Ventuno Q can trigger startup. No adb connect/tcpip, LAN
fallback, firmware flashing, or motion commands are used by this supervisor.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import logging
from logging.handlers import RotatingFileHandler
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
from urllib.request import build_opener, ProxyHandler

from board.usb_link_client import bootstrap_source

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / 'runtime'
RELAY_SOURCE = ROOT / 'board' / 'host_relay.py'
BOARD_WEB_PORT = 18000   # board-side end of the dashboard/camera reverse (board uses 8000 itself)
LOG = logging.getLogger('so101.usb')


class LinkError(RuntimeError):
    pass


class Adb:
    def __init__(self, executable):
        self.executable = executable
        self.env = dict(os.environ)
        # A caller's default serial/server must not turn USB discovery into a
        # remote ADB connection. Disable tracing of the stdin token payload.
        for name in ('ANDROID_SERIAL', 'ANDROID_TRANSPORT_ID', 'ADB_SERVER_SOCKET',
                     'ANDROID_ADB_SERVER_ADDRESS', 'ANDROID_ADB_SERVER_PORT', 'ADB_TRACE'):
            self.env.pop(name, None)

    def run(self, *args, timeout=6):
        try:
            result = subprocess.run([self.executable, *args], capture_output=True,
                                    text=True, encoding='utf8', errors='replace', timeout=timeout, env=self.env)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise LinkError('ADB is unavailable or timed out; check the USB connection.') from exc
        if result.returncode:
            # These calls never contain the shared token.
            message = (result.stderr or result.stdout).strip()[:300]
            raise LinkError(message or 'ADB command failed')
        return result.stdout.strip()

    def usb_serial(self):
        # -d explicitly excludes Wi-Fi ADB and emulators, even when ANDROID_SERIAL is set.
        serial = self.run('-d', 'get-serialno')
        if not serial or serial == 'unknown':
            raise LinkError('No USB device found')
        return serial

    def verify_ventuno(self, serial):
        identity = self.run('-s', serial, 'shell', 'cat',
                            '/proc/device-tree/model', '/proc/device-tree/compatible').lower()
        if 'ventuno q' not in identity and 'arduino,monza' not in identity:
            raise LinkError('The connected USB device is not an Arduino Ventuno Q.')

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
                raise LinkError(f'Board port {remote} is already forwarded by another application.')
            return False  # Reuse it without claiming ownership of another application's mapping.
        self.run('-s', serial, 'reverse', '--no-rebind', remote, local)
        return True

    def remove_reverse(self, serial, remote, local):
        remote, local = f'tcp:{remote}', f'tcp:{local}'
        if self.mappings(serial).get(remote) == local:
            self.run('-s', serial, 'reverse', '--remove', remote)

    def start_client(self, serial, token, port, log_file):
        process = subprocess.Popen(
            [self.executable, '-s', serial, 'shell', '-T', 'python3', '-u', '-'],
            stdin=subprocess.PIPE, stdout=log_file, stderr=subprocess.STDOUT, env=self.env)
        try:
            process.stdin.write(bootstrap_source(token, port).encode('utf8'))
            process.stdin.close()
        except (OSError, BrokenPipeError):
            stop_process(process)
            raise LinkError('Could not start the USB link client on the board.')
        return process

    def stage_token(self, serial, app_dir, token):
        """Write <app>/runtime/sim.token on the board. The token travels on stdin only."""
        code = ('import json,os,pathlib,sys\n'
                'p=json.load(sys.stdin); app=pathlib.Path(p["app"])\n'
                'if not (app/"app.yaml").is_file(): print("NO_APP"); sys.exit(3)\n'
                'o=app.stat(); d=app/"runtime"; d.mkdir(exist_ok=True)\n'
                'if d.stat().st_uid!=o.st_uid: os.chown(d,o.st_uid,o.st_gid)\n'
                't=d/"sim.token"\n'
                'if t.is_symlink(): raise SystemExit("symlink token path")\n'
                'fd=os.open(t,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)\n'
                'os.write(fd,(p["token"]+"\\n").encode()); os.close(fd); os.chmod(t,0o600)\n'
                'if t.stat().st_uid!=o.st_uid: os.chown(t,o.st_uid,o.st_gid)\n'
                'print("TOKEN_STAGED")\n')
        try:
            result = subprocess.run([self.executable, '-s', serial, 'shell', '-T', 'python3', '-c', shlex.quote(code)],
                                    input=json.dumps({'app': app_dir, 'token': token}), capture_output=True,
                                    text=True, timeout=15, env=self.env)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise LinkError('Could not stage the simulator token on the board.') from exc
        if 'NO_APP' in result.stdout:
            raise LinkError(f'App {app_dir} not found on the board. Upload it first (upload_board_app.py).')
        if result.returncode or 'TOKEN_STAGED' not in result.stdout:
            raise LinkError('Token staging failed; check ownership of the app folder on the board.')

    def start_relay(self, serial, app_dir, mappings, log_file):
        """host_relay.py runs from stdin on the IQ8 host; nothing is installed on the board."""
        args = ['--app-dir', app_dir] + [a for name, port in mappings for a in ('--map', f'{name}:{port}')]
        process = subprocess.Popen(
            [self.executable, '-s', serial, 'shell', '-T', 'python3', '-u', '-', *map(shlex.quote, args)],
            stdin=subprocess.PIPE, stdout=log_file, stderr=subprocess.STDOUT, env=self.env)
        try:
            process.stdin.write(RELAY_SOURCE.read_bytes())
            process.stdin.close()
        except (OSError, BrokenPipeError):
            stop_process(process)
            raise LinkError('Could not start the relay on the board.')
        return process


def stop_process(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def read_state(port):
    # Local requests must not pass through a corporate HTTP proxy.
    opener = build_opener(ProxyHandler({}))
    with opener.open(f'http://127.0.0.1:{port}/api/state', timeout=2) as response:
        return json.load(response)


def load_token(path):
    if not path.exists():
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf8') as stream:
            stream.write(secrets.token_urlsafe(32) + '\n')
    token = path.read_text(encoding='utf8').strip()
    if len(token) < 16 or token == 'REPLACE_WITH_YOUR_OWN_LONG_RANDOM_TOKEN':
        raise LinkError('Invalid USB token file; restore it or remove it to generate a new token.')
    return token


class UsbBoardMonitor:
    def __init__(self, adb, root=ROOT, tcp_port=5050, web_port=8000, external_gateway=False, board_app=None,
                 on_status=None):
        self.adb, self.root = adb, Path(root)
        self.runtime = self.root / 'runtime'
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.tcp_port, self.web_port = tcp_port, web_port
        # board_app: absolute app folder on the board (App Lab "Robo Arm"). The app's own
        # gateway owns the control session; we only stage the token and run the relay.
        self.board_app = board_app
        self.external_gateway = external_gateway or bool(board_app)
        self.on_status = on_status
        self.stop_event = threading.Event()
        self.simulator = self.client = self.relay = None
        self.sim_log = self.client_log = self.relay_log = None
        self.serial = None
        self.owned_mappings = []
        self.token_path = self.runtime / '.usb-board-token'
        self.token = load_token(self.token_path)
        self.last_status = None

    def status(self, phase, detail):
        state = {'phase': phase, 'detail': detail, 'pid': os.getpid(),
                 'serial': self.serial, 'updated_at': time.time(),
                 'dashboard': f'http://localhost:{self.web_port}',
                 'external_gateway': self.external_gateway}
        temporary = self.runtime / '.usb-board-status.tmp'
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf8')
        temporary.replace(self.runtime / '.usb-board-status.json')
        if self.last_status != (phase, detail):
            LOG.info('%s: %s', phase, detail)
            self.last_status = phase, detail
            if self.on_status:
                self.on_status(phase, detail)

    def ensure_simulator(self):
        if self.simulator is not None and self.simulator.poll() is None:
            return
        if self.sim_log:
            self.sim_log.close()
        # Do not take over or kill a local/LAN simulation (or any other app).
        for port in (self.tcp_port, self.web_port):
            with socket.socket() as check:
                try:
                    check.bind(('127.0.0.1', port))
                except OSError as exc:
                    raise LinkError(f'Port {port} is busy. Stop the existing simulation before USB mode.') from exc
        self.sim_log = (self.runtime / 'usb_simulator.log').open('a', encoding='utf8')
        env = dict(os.environ, MUJOCO_GL='egl', PYTHONUNBUFFERED='1')
        self.simulator = subprocess.Popen(
            [sys.executable, '-B', str(self.root / 'app.py'), '--mode', 'board',
             '--board-link', 'usb', '--token-file', str(self.token_path), '--no-viewer',
             '--tcp-port', str(self.tcp_port), '--web-port', str(self.web_port)],
            cwd=self.root, env=env, stdout=self.sim_log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not self.should_stop():
            if self.simulator.poll() is not None:
                raise LinkError('Simulation could not start. See usb_simulator.log.')
            try:
                state = read_state(self.web_port)
                if state.get('mode') == 'board' and state.get('board_link') == 'usb':
                    return
            except (OSError, ValueError):
                pass
            self.stop_event.wait(0.25)
        stop_process(self.simulator)
        raise LinkError('Timed out while starting simulation. See usb_simulator.log.')

    def attach(self, serial):
        self.adb.verify_ventuno(serial)
        self.serial = serial
        self.status('STARTING', 'Ventuno Q detected over USB-C; starting simulation.')
        self.ensure_simulator()
        # Local control and camera traffic both travel through ADB/USB.
        # Use 18000 on the board to avoid its own web services on port 8000.
        for remote, local in ((self.tcp_port, self.tcp_port), (18000, self.web_port)):
            if self.adb.add_reverse(serial, remote, local):
                self.owned_mappings.append((remote, local))
        if self.board_app:
            self.start_board_link(serial)
        elif not self.external_gateway:
            self.client_log = (self.runtime / 'usb_board_client.log').open('a', encoding='utf8')
            self.client = self.adb.start_client(serial, self.token, self.tcp_port, self.client_log)

    def start_board_link(self, serial):
        """Token + relay so the App Lab container reaches this simulator (restarted on every replug)."""
        self.adb.stage_token(serial, self.board_app, self.token)
        log_path = self.runtime / 'usb_relay.log'
        start = log_path.stat().st_size if log_path.exists() else 0
        self.relay_log = log_path.open('a', encoding='utf8')
        self.relay = self.adb.start_relay(serial, self.board_app,
                                          (('simulator.sock', self.tcp_port), ('camera.sock', BOARD_WEB_PORT)),
                                          self.relay_log)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and not self.should_stop():
            self.relay_log.flush()
            with log_path.open(encoding='utf8', errors='replace') as stream:
                stream.seek(start)
                text = stream.read()
            if 'RELAY_READY' in text:
                return
            if self.relay.poll() is not None:
                raise LinkError('Relay on the board stopped: ' + (text.strip().splitlines() or ['?'])[-1][:200])
            self.stop_event.wait(0.25)
        raise LinkError('Relay on the board did not start; see runtime/usb_relay.log.')

    def detach(self):
        stop_process(self.client)
        self.client = None
        stop_process(self.relay)
        self.relay = None
        if self.relay_log:
            self.relay_log.close()
            self.relay_log = None
        if self.client_log:
            self.client_log.close()
            self.client_log = None
        if self.serial:
            for remote, local in self.owned_mappings:
                try:
                    self.adb.remove_reverse(self.serial, remote, local)
                except LinkError:
                    pass  # USB removal already destroys its forwarding rules.
        self.owned_mappings.clear()
        self.serial = None

    def tick(self):
        try:
            serial = self.adb.usb_serial()
        except LinkError as exc:
            self.detach()
            self.status('WAITING_FOR_USB', str(exc))
            return
        if serial != self.serial:
            self.detach()
            self.attach(serial)
        if self.simulator is None or self.simulator.poll() is not None:
            raise LinkError('Simulation stopped; retrying startup.')
        if self.client is not None and self.client.poll() is not None:
            raise LinkError('USB client stopped; reconnecting. See usb_board_client.log.')
        if self.relay is not None and self.relay.poll() is not None:
            raise LinkError('Relay on the board stopped; restarting. See usb_relay.log.')
        state = read_state(self.web_port)
        if state.get('board_connected') and (state.get('last_board_heartbeat_age_s') or 0) < 2:
            self.status('BOARD_CONNECTED', 'USB-C connected. Dashboard is ready; no automatic motion.')
        elif self.board_app:
            self.status('WAITING_FOR_GATEWAY', 'USB-C + relay ready; waiting for the Robo Arm app '
                        '(Run in App Lab, or the model is thinking).')
        else:
            self.status('WAITING_FOR_GATEWAY', 'USB-C ready; waiting for the board handshake.')

    def should_stop(self):
        return self.stop_event.is_set() or (self.runtime / '.usb-board-stop').exists()

    def run(self):
        self.status('WAITING_FOR_USB', 'Connect a powered Ventuno Q using a USB-C data cable.')
        try:
            while not self.should_stop():
                delay = 1
                try:
                    self.tick()
                except (LinkError, OSError, ValueError) as exc:
                    self.detach()
                    self.status('RETRYING', str(exc))
                    delay = 5
                for _ in range(delay * 4):
                    if self.should_stop():
                        break
                    self.stop_event.wait(0.25)
        finally:
            self.detach()
            stop_process(self.simulator)
            if self.sim_log:
                self.sim_log.close()
            self.status('STOPPED', 'USB auto-connect is stopped.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', default=os.getenv('SO101_ADB') or shutil.which('adb') or shutil.which('adb.exe'))
    parser.add_argument('--external-gateway', action='store_true', help='Prepare USB only; a real MCU gateway owns the control session')
    parser.add_argument('--board-app', help='App folder on the board (e.g. /home/arduino/ArduinoApps/robo-arm): '
                                            'stage token + run the relay for the App Lab container')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--stop', action='store_true')
    args = parser.parse_args(argv)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    if args.stop:
        (RUNTIME / '.usb-board-stop').touch()
        print('Requested USB monitor shutdown.')
        return
    with (RUNTIME / '.usb-board.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            running = False
        except BlockingIOError:
            running = True
        if args.status:
            state_file = RUNTIME / '.usb-board-status.json'
            state = json.loads(state_file.read_text(encoding='utf8')) if state_file.exists() else {}
            print(json.dumps(dict(state, running=running), ensure_ascii=False, indent=2))
            return
        if running:
            print('USB monitor is already running.')
            return
        if not args.adb:
            parser.error('ADB not found. Start with usb_board_mode.ps1 or pass --adb PATH.')
        (RUNTIME / '.usb-board-stop').unlink(missing_ok=True)
        handler = RotatingFileHandler(RUNTIME / 'usb_board_mode.log', maxBytes=2_000_000, backupCount=2, encoding='utf8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        LOG.addHandler(handler)
        LOG.setLevel(logging.INFO)
        monitor = UsbBoardMonitor(Adb(args.adb), external_gateway=args.external_gateway, board_app=args.board_app)
        for signum in (signal.SIGTERM, signal.SIGINT):
            signal.signal(signum, lambda *_: monitor.stop_event.set())
        monitor.run()


if __name__ == '__main__':
    main()
