#!/usr/bin/env python3
"""ONE canonical MuJoCo process: live web dashboard + local joint control (laptop only).

`python app.py --mode board` is handled by board_mode.py: it starts the schema-v2 simulator in
board_server/ and runs the SmolVLA ONNX runner on VENTUNO Q over USB-C (rebuilt 2026-11-11).
"""
from __future__ import annotations
import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from engine import ROOT, Simulation
from protocol import parse_action, ProtocolError

LOOPBACK = ('127.0.0.1', '::1')


def make_web_handler(sim: Simulation):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            if not self.path.startswith('/api/'):
                super().log_message(fmt,*args)
        def send_bytes(self, content, mime='application/json', status=200):
            self.send_response(status)
            self.send_header('Content-Type',mime)
            self.send_header('Content-Length',str(len(content)))
            self.send_header('Cache-Control','no-store, max-age=0')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('X-Frame-Options','DENY')
            self.end_headers()
            self.wfile.write(content)
        def json_response(self, data, status=200):
            self.send_bytes(json.dumps(data,ensure_ascii=False).encode('utf8'),'application/json; charset=utf-8',status)
        def do_GET(self):
            route=urlsplit(self.path).path
            if route in ('/','/index.html'):
                self.send_bytes((ROOT/'web'/'index.html').read_bytes(),'text/html; charset=utf-8')
            elif route=='/api/state':
                self.json_response(sim.snapshot())
            elif route in ('/api/camera/overhead','/api/camera/wrist'):
                pic=sim.get_frame(route.rsplit('/',1)[1])
                if not pic:
                    self.json_response({'error':'Camera not ready. Inspect /api/state camera_error.'},503)
                else:
                    self.send_bytes(pic,'image/jpeg')
            else:
                self.json_response({'error':'Not found'},404)
        def do_POST(self):
            if urlsplit(self.path).path != '/api/action':
                self.json_response({'error':'Not found'},404);return
            # Joint commands are accepted from this computer only.
            if self.client_address[0] not in LOOPBACK:
                self.json_response({'error':'Web control is only accepted from localhost'},403);return
            # Basic cross-origin protection (not an internet-facing API)
            origin=self.headers.get('Origin')
            if origin:
                good={f'http://localhost:{self.server.server_port}',f'http://127.0.0.1:{self.server.server_port}'}
                if origin not in good:
                    self.json_response({'error':'Cross-origin command rejected'},403);return
            try:
                size=int(self.headers.get('Content-Length',0))
                if not 0<size<=4096:raise ProtocolError('Invalid JSON body length')
                obj=json.loads(self.rfile.read(size))
                action=parse_action(obj,sim.limits,sim.last_accepted_sequence)
                sim.enqueue(action)
                self.json_response({'type':'ACK','sequence_id':action.sequence_id,'meaning':'Queued, NOT completed'},202)
            except (ProtocolError,ValueError,TypeError,json.JSONDecodeError) as exc:
                self.json_response({'type':'REJECTED','reason':str(exc)},400)
    return Handler



def main():
    import sys
    from board_mode import wants_board_mode
    if wants_board_mode(sys.argv[1:]):
        from board_mode import main as board_mode_main
        raise SystemExit(board_mode_main(sys.argv[1:]))
    parser=argparse.ArgumentParser(description='SO-101 MuJoCo scene + web dashboard (local mode)')
    parser.add_argument('--mode',choices=('local',),default='local',help='local = this file; `--mode board` runs board_mode.py (see README)')
    parser.add_argument('--web-host',default='127.0.0.1',help='Use 0.0.0.0 only on trusted LAN')
    parser.add_argument('--web-port',type=int,default=8000)
    parser.add_argument('--no-viewer',action='store_true',help='Headless simulation, web still works if OpenGL renderer does')
    # Ignored: kept so older commands still start. The dataset-matched scene is always used.
    parser.add_argument('--match-dataset',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    # Decision 0009: the only local scene is the episode-230 Desk Cleanup scene with cameras and
    # look fitted to the recording. The four-ball and "calibrated" variants are retired here.
    import desk_cleanup
    sim=desk_cleanup.create_simulation(match_dataset=True)
    scene_text='episode-230 Desk Cleanup (dataset-matched): 1 ball, 1 bowl, start pose = dataset frame 100'
    web=ThreadingHTTPServer((args.web_host,args.web_port),make_web_handler(sim))
    threading.Thread(target=web.serve_forever,daemon=True,name='web').start()
    print(f'WEB: http://127.0.0.1:{args.web_port}  MODE: local',flush=True)
    print(f'SO-101: 6 joints, overhead and wrist cameras; scene = {scene_text}',flush=True)
    print('NOTE: included STL are PROXY meshes; import OFFICIAL meshes before evaluating grasp physics.',flush=True)
    viewer=None
    ctx=None
    try:
        if not args.no_viewer:
            import mujoco.viewer
            ctx=mujoco.viewer.launch_passive(sim.model,sim.data,show_left_ui=False,show_right_ui=False)
            viewer=ctx.__enter__()
        sim.capture()
        timestep=float(sim.model.opt.timestep)
        latest_capture=time.monotonic()
        t0=time.monotonic()
        accumulator=0.0
        while viewer is None or viewer.is_running():
            now=time.monotonic()
            accumulator=min(0.10,accumulator+max(0,now-t0))
            t0=now
            n=0
            while accumulator>=timestep and n<50:
                sim.step();accumulator-=timestep;n+=1
            if now-latest_capture>=sim.camera_interval:
                sim.capture();latest_capture=now
            if viewer:viewer.sync()
            time.sleep(0.008)
    except KeyboardInterrupt:
        print('\nStopping...',flush=True)
    finally:
        web.shutdown();web.server_close()
        sim.close()
        if ctx:ctx.__exit__(None,None,None)

if __name__=='__main__':main()
