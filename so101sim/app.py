#!/usr/bin/env python3
"""ONE canonical MuJoCo process: TCP from IQ8 + live read-only web + optional local dev control."""
from __future__ import annotations
import argparse
import ipaddress
import hmac
import json
import os
import socketserver
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from engine import ROOT, Simulation
from protocol import parse_action, ProtocolError, MAX_LINE


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
            # Lab/board deployment is read-only from web; local mode only on loopback.
            if sim.mode != 'local' or self.client_address[0] not in ('127.0.0.1','::1'):
                self.json_response({'error':'Web control is disabled; only VENTUNO gateway may command board mode'},403);return
            # Basic cross-origin protection in local mode (not an internet-facing API)
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
                sim.enqueue(action, from_board=False)
                self.json_response({'type':'ACK','sequence_id':action.sequence_id,'meaning':'Queued, NOT completed'},202)
            except (ProtocolError,ValueError,TypeError,json.JSONDecodeError) as exc:
                self.json_response({'type':'REJECTED','reason':str(exc)},400)
    return Handler


def make_tcp_handler(sim:Simulation,token:str,allowed_ip:str):
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            ip=self.client_address[0]
            if ip!=allowed_ip:
                print('TCP rejected IP:',ip,flush=True);return
            self.connection.settimeout(2.5)
            if sim.session_active:
                self.write_obj({'type':'ERROR','reason':'Another gateway is connected'});return
            owned=False
            try:
                line=self.rfile.readline(MAX_LINE+1)
                if not line or len(line)>MAX_LINE: return
                hello=json.loads(line)
                if not isinstance(hello,dict) or hello.get('type')!='HELLO' or not hmac.compare_digest(str(hello.get('token','')),token):
                    self.write_obj({'type':'ERROR','reason':'Authentication failed'});return
                if sim.session_active: return
                sim.set_session(True,ip);owned=True
                self.write_obj({'type':'WELCOME','joint_names':list(sim.snapshot()['joint_names']),
                                'units':'radians','status':'NETWORK_LINK_ONLY_STM32_NOT_ATTESTED',
                                'heartbeat_timeout_seconds':2.0})
                print('VENTUNO TCP session:',ip,flush=True)
                while True:
                    try: line=self.rfile.readline(MAX_LINE+1)
                    except TimeoutError:
                        # Idle gateway is disconnected; physics is already paused after 2s.
                        break
                    if not line: break
                    if len(line)>MAX_LINE:
                        self.write_obj({'type':'ERROR','reason':'Frame too long'});break
                    try:
                        msg=json.loads(line)
                        if not isinstance(msg,dict):raise ProtocolError('Object required')
                        kind=msg.get('type')
                        if kind in ('PING','GET_STATE'):
                            sim.heartbeat()
                            if kind=='PING':self.write_obj({'type':'PONG'})
                            else:self.write_obj({'type':'STATE',**sim.snapshot()})
                            continue
                        action=parse_action(msg,sim.limits,sim.last_accepted_sequence)
                        sim.heartbeat()
                        sim.enqueue(action,from_board=True)
                        self.write_obj({'type':'ACK','sequence_id':action.sequence_id,'meaning':'Queued, NOT completed'})
                    except (ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
                        self.write_obj({'type':'REJECTED','reason':str(exc)})
            except (OSError,TimeoutError,ValueError,json.JSONDecodeError) as exc:
                print('Gateway disconnected:',type(exc).__name__,str(exc)[:120],flush=True)
            finally:
                if owned:sim.set_session(False)
        def write_obj(self,obj):
            self.wfile.write((json.dumps(obj,separators=(',',':'))+'\n').encode('utf8'))
            self.wfile.flush()
    return Handler

class ThreadTCP(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True


def main():
    parser=argparse.ArgumentParser(description='SO-101 ONE scene + web dashboard + VENTUNO Q TCP')
    parser.add_argument('--mode',choices=('local','board'),default='local',help='local: dev commands; board: only VENTUNO TCP actions')
    parser.add_argument('--web-host',default='127.0.0.1',help='Use 0.0.0.0 only on trusted LAN')
    parser.add_argument('--web-port',type=int,default=8000)
    parser.add_argument('--tcp-port',type=int,default=5050)
    parser.add_argument('--allowed-ip',help='Actual IQ8 Linux IP; required in board mode')
    parser.add_argument('--token',default=os.getenv('SO101_TOKEN'),help='Long random token; do not commit')
    parser.add_argument('--no-viewer',action='store_true',help='Headless simulation, web still works if OpenGL renderer does')
    args=parser.parse_args()
    if args.mode=='board' and (not args.allowed_ip or not args.token or len(args.token)<16):
        parser.error('board mode requires --allowed-ip and --token with >=16 characters (or SO101_TOKEN environment)')
    if args.mode=='board':
        try:
            args.allowed_ip=str(ipaddress.IPv4Address(args.allowed_ip))
        except ipaddress.AddressValueError:
            parser.error('--allowed-ip must be a real IPv4 address, not BOARD_IP; for example 10.1.1.72')
        if args.token == 'REPLACE_WITH_YOUR_OWN_LONG_RANDOM_TOKEN':
            parser.error('Replace the example token with your own shared token before using board mode')
    sim=Simulation(args.mode)
    web=ThreadingHTTPServer((args.web_host,args.web_port),make_web_handler(sim))
    threading.Thread(target=web.serve_forever,daemon=True,name='web').start()
    tcp=None
    if args.mode=='board':
        tcp=ThreadTCP(('0.0.0.0',args.tcp_port),make_tcp_handler(sim,args.token,args.allowed_ip))
        threading.Thread(target=tcp.serve_forever,daemon=True,name='ventuno-tcp').start()
        print(f'TCP: :{args.tcp_port} (restricted to IQ8={args.allowed_ip})',flush=True)
    print(f'WEB: http://127.0.0.1:{args.web_port}  MODE: {args.mode}',flush=True)
    print('SO-101: 6 joints, 4 balls, tray, overhead and wrist cameras',flush=True)
    print('NOTE: included STL are PROXY meshes; import OFFICIAL meshes before evaluating grasp physics.',flush=True)
    print('NOTE: an IQ8 TCP connection is not proof of STM32H5F5 validation.',flush=True)
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
        if tcp:tcp.shutdown();tcp.server_close()
        sim.close()
        if ctx:ctx.__exit__(None,None,None)

if __name__=='__main__':main()
