#!/usr/bin/env python3
"""SO-101 simulator server, schema v2 (dùng cho board mode).

Người dùng không gọi file này trực tiếp: `python app.py --mode board` ở thư mục so101sim chạy
../board_mode.py, và board_mode.py mở server này với --token-file.
Chạy tay để xem/kiểm tra (không cần board):
  python board_server/app.py --mode local    dashboard schema v2 + bài gắp mẫu
"""
from __future__ import annotations
import argparse
import hmac
import json
import os
from pathlib import Path
import signal
import socketserver
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from engine import Simulation
from protocol import JOINT_NAMES, MAX_LINE, SCHEMA_VERSION, ProtocolError
from runtime_support import ROOT, RUNTIME


def make_web_handler(sim):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            if not self.path.startswith('/api/'):
                super().log_message(fmt, *args)

        def send_bytes(self, content, mime='application/json', status=200, headers=None):
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store, max-age=0')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            for key, val in (headers or {}).items():
                self.send_header(key, str(val))
            self.end_headers()
            try:
                self.wfile.write(content)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def json_response(self, data, status=200):
            self.send_bytes(json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf8'),
                            'application/json; charset=utf-8', status)

        def do_GET(self):
            route = urlsplit(self.path).path
            if route in ('/', '/index.html'):
                self.send_bytes((ROOT / 'web/index.html').read_bytes(), 'text/html; charset=utf-8')
            elif route == '/api/state':
                self.json_response(sim.snapshot())
            elif route == '/api/evaluation':
                self.json_response(sim.evaluation())
            elif route == '/api/identity':
                self.json_response(sim.identity)
            elif route == '/api/observation':
                frame = sim.observation()
                self.json_response(frame or {'error': 'Camera pair not ready'}, 200 if frame else 503)
            elif route in ('/api/camera/overhead', '/api/camera/wrist'):
                packet = sim.get_frame_packet(route.rsplit('/', 1)[1])
                if packet is None:
                    self.json_response({'error': 'Camera not ready; inspect camera_error in /api/state'}, 503)
                else:
                    picture, metadata = packet
                    self.send_bytes(picture, 'image/jpeg', headers={
                        'X-Frame-Id': metadata['frame_id'], 'X-Run-Id': metadata['run_id'],
                        'X-Sim-Time': metadata['sim_time'],
                        'X-Captured-Monotonic-Ns': metadata['captured_monotonic_ns']})
            else:
                self.json_response({'error': 'Not found'}, 404)

        def do_POST(self):
            route = urlsplit(self.path).path
            kinds = {'/api/action': None, '/api/reset': 'RESET', '/api/abort': 'ABORT',
                     '/api/resume': 'RESUME', '/api/reference': 'REFERENCE'}
            if route not in kinds:
                self.json_response({'error': 'Not found'}, 404)
                return
            if sim.mode != 'local' or self.client_address[0] not in ('127.0.0.1', '::1'):
                self.json_response({'error': 'Web control disabled in board mode; use the authenticated gateway'}, 403)
                return
            origin = self.headers.get('Origin')
            allowed = {f'http://localhost:{self.server.server_port}', f'http://127.0.0.1:{self.server.server_port}'}
            if origin and origin not in allowed:
                self.json_response({'error': 'Cross-origin command rejected'}, 403)
                return
            try:
                size = int(self.headers.get('Content-Length', 0))
                if not 0 < size <= MAX_LINE:
                    raise ProtocolError('Invalid JSON body length')
                self.connection.settimeout(3)
                obj = json.loads(self.rfile.read(size))
                if not isinstance(obj, dict):
                    raise ProtocolError('Expected JSON object')
                if kinds[route]:
                    obj['type'] = kinds[route]
                if route == '/api/reference':
                    reply = sim.start_reference(obj)
                else:
                    reply = sim.command(obj)
                self.json_response(reply, 202)
            except (ValueError, TypeError, KeyError, OSError) as exc:
                self.json_response({'type': 'REJECTED', 'reason': str(exc)}, 400)
    return Handler


def make_tcp_handler(sim, token, allowed_ip):
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            if self.client_address[0] != allowed_ip:
                return
            self.connection.settimeout(2.5)
            owned_session = None
            try:
                hello = self.read_obj()
                if not isinstance(hello, dict) or hello.get('type') != 'HELLO' or not hmac.compare_digest(
                        str(hello.get('token', '')), token):
                    self.write_obj({'type': 'ERROR', 'reason': 'Authentication failed'})
                    return
                owned_session = sim.set_session(True, self.client_address[0])
                self.write_obj({'type': 'WELCOME', 'schema_version': SCHEMA_VERSION,
                                'joint_names': list(JOINT_NAMES), 'units': 'radians',
                                'status': 'USB_LINK_SIMULATION_ONLY',
                                'heartbeat_timeout_seconds': sim.settings['heartbeat_timeout_s'],
                                'run_id': sim.run_id, 'session_id': owned_session,
                                'requires_resume': sim.hold_latched,
                                'accepted_sequence': sim.last_accepted_sequence})
                while True:
                    obj = self.read_obj()
                    if obj is None:
                        break
                    try:
                        if not isinstance(obj, dict):
                            raise ProtocolError('Expected JSON object')
                        kind = obj.get('type')
                        if kind in ('PING', 'GET_STATE'):
                            sim.heartbeat(owned_session)
                            self.write_obj({'type': 'STATE', **sim.snapshot()} if kind == 'GET_STATE'
                                           else {'type': 'PONG', 'hold_latched': sim.hold_latched,
                                                 'run_id': sim.run_id, 'session_id': owned_session})
                        else:
                            reply = sim.command(obj, from_board=True)
                            sim.heartbeat(owned_session)
                            self.write_obj(reply)
                    except (ValueError, TypeError, KeyError) as exc:
                        self.write_obj({'type': 'REJECTED', 'reason': str(exc)})
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                pass
            finally:
                if owned_session is not None:
                    sim.set_session(False, session_id=owned_session)

        def read_obj(self):
            line = self.rfile.readline(MAX_LINE + 1)
            if not line:
                return None
            if len(line) > MAX_LINE or not line.endswith(b'\n'):
                raise ProtocolError('Invalid or oversized frame')
            return json.loads(line)

        def write_obj(self, obj):
            self.wfile.write((json.dumps(obj, separators=(',', ':'), allow_nan=False) + '\n').encode('utf8'))
            self.wfile.flush()
    return Handler


class ThreadTCP(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='SO-101 simulation, cameras, episodes and USB board link')
    parser.add_argument('--mode', choices=('local', 'board'), default='local')
    parser.add_argument('--web-port', type=int, default=8000)
    parser.add_argument('--tcp-port', type=int, default=5050)
    parser.add_argument('--token-file', type=Path, help='Nội bộ: board_mode.py truyền token phiên USB')
    parser.add_argument('--no-viewer', action='store_true')
    parser.add_argument('--no-cameras', action='store_true', help='Physics-only diagnostic run')
    parser.add_argument('--camera-fps', type=float, help='Override settings.json, 1..60 paired frames/s')
    parser.add_argument('--no-logs', action='store_true', help='Disable episode recording for temporary tests')
    args = parser.parse_args(argv)
    if args.camera_fps is not None and not 1 <= args.camera_fps <= 60:
        parser.error('--camera-fps must be in [1, 60]')
    if not 1 <= args.web_port <= 65535 or not 1 <= args.tcp_port <= 65535 or args.web_port == args.tcp_port:
        parser.error('Ports must be different integers in [1, 65535]')
    # Chỉ localhost: board nối qua ADB reverse của USB-C, không có LAN.
    args.web_host = args.tcp_host = args.allowed_ip = '127.0.0.1'
    args.token = None
    if args.token_file is not None:
        try:
            args.token = args.token_file.read_text(encoding='utf8').strip()
        except OSError as exc:
            parser.error(f'Cannot read token file: {exc}')
    if args.mode == 'board' and (not args.token or len(args.token) < 16):
        parser.error('board mode needs --token-file with >=16 characters (run `python app.py --mode board` in so101sim)')
    return args


def main():
    args = parse_args()
    stopping = threading.Event()
    def stop(*_):
        stopping.set()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, stop)
    settings = {'camera_fps': args.camera_fps} if args.camera_fps else None
    sim = Simulation(args.mode, board_link='usb', settings=settings,
                     log_dir=None if args.no_logs else RUNTIME / 'runs')
    web = tcp = viewer = context = None
    web_thread = tcp_thread = None
    try:
        web = ThreadingHTTPServer((args.web_host, args.web_port), make_web_handler(sim))
        web.daemon_threads = True
        web_thread = threading.Thread(target=web.serve_forever, daemon=True, name='web')
        web_thread.start()
        if args.mode == 'board':
            tcp = ThreadTCP((args.tcp_host, args.tcp_port), make_tcp_handler(sim, args.token, args.allowed_ip))
            tcp_thread = threading.Thread(target=tcp.serve_forever, daemon=True, name='gateway')
            tcp_thread.start()
        if not args.no_cameras:
            sim.start_cameras()
        if not args.no_viewer:
            import mujoco.viewer
            context = mujoco.viewer.launch_passive(sim.model, sim.data, show_left_ui=False, show_right_ui=False)
            viewer = context.__enter__()
        print(f'WEB http://127.0.0.1:{args.web_port} | {args.mode.upper()} | schema v{SCHEMA_VERSION}', flush=True)
        print('Simulation only. Board mode: SmolVLA ONNX on the Ventuno Q, no STM32 in the loop.', flush=True)
        timestep = float(sim.model.opt.timestep)
        last = rate_start = time.monotonic()
        rate_sim = float(sim.data.time)
        rate_run = sim.run_id
        accumulator = 0.0
        next_view = last
        while not stopping.is_set() and (viewer is None or viewer.is_running()):
            now = time.monotonic()
            elapsed = max(0, now - last)
            last = now
            accumulator += elapsed
            if accumulator > .1:
                with sim.lock:
                    sim.metrics['discarded_wall_time_s'] += accumulator - .1
                accumulator = .1
            while accumulator >= timestep:
                sim.step()
                accumulator -= timestep
            if rate_run != sim.run_id:
                rate_run = sim.run_id
                rate_start, rate_sim = now, float(sim.data.time)
                with sim.lock:
                    sim.metrics['real_time_factor'] = 0.0
            elif now - rate_start >= 1:
                with sim.lock:
                    sim.metrics['real_time_factor'] = (float(sim.data.time) - rate_sim) / (now - rate_start)
                    rate_sim = float(sim.data.time)
                rate_start = now
            if viewer is not None and now >= next_view:
                with sim.lock:
                    viewer.sync()
                next_view = now + 1 / 60
            stopping.wait(max(0, timestep - accumulator))
    finally:
        if web:
            if web_thread:
                web.shutdown()
            web.server_close()
        if tcp:
            if tcp_thread:
                tcp.shutdown()
            tcp.server_close()
        if context:
            context.__exit__(None, None, None)
        sim.close()


if __name__ == '__main__':
    main()
