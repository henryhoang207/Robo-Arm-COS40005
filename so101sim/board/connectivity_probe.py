#!/usr/bin/env python3
"""Run on IQ8 Linux: verify the network path, without ever commanding actuators."""
import argparse, json, socket, time

ap=argparse.ArgumentParser()
ap.add_argument('--host',required=True,help='Laptop IP reachable from IQ8')
ap.add_argument('--port',type=int,default=5050)
ap.add_argument('--token',required=True)
a=ap.parse_args()
with socket.create_connection((a.host,a.port),timeout=5) as s:
    s.settimeout(5)
    read=s.makefile('rb')
    def ask(obj):
        s.sendall((json.dumps(obj)+'\n').encode())
        response=read.readline(16384)
        if not response:raise ConnectionError('Server disconnected')
        result=json.loads(response)
        print(result)
        return result
    hello=ask({'type':'HELLO','token':a.token})
    if hello.get('type')!='WELCOME': raise RuntimeError('Network handshake failed')
    for i in range(3):
        ask({'type':'PING'})
        state=ask({'type':'GET_STATE'})
        assert len(state['joint_positions'])==6
        time.sleep(.5)
print('PASS: IQ8 TCP handshake and joint-state roundtrip; no STM32 validation or motion tested')
