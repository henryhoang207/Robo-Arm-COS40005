"""End-to-end HTTP, paired cameras and TCP execution with a simulated gateway.

No physical board, MCU approval or AI inference is exercised by this test.
"""
import base64
import io
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]          # so101sim/board_server
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))                # so101sim (board_mode.py)
from board_mode import stop_process
from runtime_support import RUNTIME


def free_port():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


def check():
    output = RUNTIME / 'validation'
    output.mkdir(parents=True, exist_ok=True)
    reports = []
    opener = build_opener(ProxyHandler({}))
    for mode in ('local', 'board'):
        web_port, tcp_port = free_port(), free_port()
        base = f'http://127.0.0.1:{web_port}'

        def request(route, payload=None, expected=200):
            data = None if payload is None else json.dumps(payload).encode()
            req = Request(base + route, data=data, headers={'Content-Type': 'application/json'})
            try:
                response = opener.open(req, timeout=5)
            except HTTPError as exc:
                response = exc
            with response:
                assert response.status == expected, (route, response.status, response.read())
                return json.load(response)

        def wait_for(predicate, timeout=30):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                try:
                    state = request('/api/state')
                    if predicate(state):
                        return state
                except OSError:
                    pass
                time.sleep(.1)
            raise AssertionError(f'{mode}: state not reached: {state}')

        def context(state):
            return {k: state[k] for k in ('schema_version', 'run_id', 'session_id')}

        with tempfile.TemporaryDirectory(prefix='runtime-check-', dir=output) as directory:
            token = secrets.token_urlsafe(32)
            token_file = Path(directory) / 'token'
            token_file.write_text(token)
            log = (output / (mode + '-server.log')).open('w', encoding='utf8')
            process = subprocess.Popen([sys.executable, '-B', str(ROOT / 'app.py'), '--mode', mode,
                                        '--token-file', str(token_file), '--no-viewer', '--web-port', str(web_port),
                                        '--tcp-port', str(tcp_port)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            client = stream = None
            try:
                state = wait_for(lambda s: s['frame_id'] is not None)
                observation = request('/api/observation')
                assert not observation['stale']
                assert observation['run_id'] == state['run_id']
                assert len(observation['joint_positions']) == 6
                assert 'objects' not in observation
                for name in ('overhead', 'wrist'):
                    blob = base64.b64decode(observation['images'][name])
                    assert Image.open(io.BytesIO(blob)).size == (640, 480)
                    (output / (name + '-initial.jpg')).write_bytes(blob)
                if mode == 'local':
                    stale = context(state)
                    reply = request('/api/reset', dict(**stale, seed=5, randomize=True), 202)
                    assert reply['run_id'] != state['run_id']
                    request('/api/abort', stale, 400)
                    state = request('/api/state')
                    request('/api/reference', context(state), 202)
                    state = wait_for(lambda s: s['reference_active'])
                    request('/api/abort', context(state), 202)
                    held = request('/api/state')
                    time.sleep(.3)
                    assert request('/api/state')['sim_time'] == held['sim_time']
                    request('/api/reset', context(held), 202)
                    state = request('/api/state')
                    request('/api/reference', context(state), 202)
                    state = wait_for(lambda s: s['episode']['status'] == 'SUCCESS' and not s['reference_active'])
                    assert state['completed_sequence'] == 7 and not state['fault']
                    assert state['metrics']['real_time_factor'] > .85, state['metrics']
                    assert not state['logging']['error'] and state['logging']['dropped_records'] == 0
                    pair = request('/api/observation')
                    for name in ('overhead', 'wrist'):
                        (output / (name + '-success.jpg')).write_bytes(base64.b64decode(pair['images'][name]))
                    assert pair['frame_id'] > observation['frame_id'] and pair['run_id'] == state['run_id']
                else:
                    for route in ('action', 'reset', 'abort', 'resume', 'reference'):
                        request('/api/' + route, context(state), 403)

                    def connect(secret):
                        client = socket.create_connection(('127.0.0.1', tcp_port), timeout=3)
                        return client, client.makefile('rwb')

                    def exchange(item):
                        stream.write((json.dumps(item) + '\n').encode()); stream.flush()
                        return json.loads(stream.readline())

                    client, stream = connect(token)
                    assert exchange({'type': 'HELLO', 'token': 'wrong-token'})['type'] == 'ERROR'
                    stream.close(); client.close()
                    client, stream = connect(token)
                    welcome = exchange({'type': 'HELLO', 'token': token})
                    assert welcome['schema_version'] == 2
                    state = exchange({'type': 'GET_STATE'})
                    q = state['joint_positions'].copy(); q[0] += .15
                    ack = exchange({'type': 'ACTION', **context(state), 'sequence_id': 0,
                                    'joint_targets': q, 'duration': 1, 'timeout': 4})
                    assert ack['type'] == 'ACK' and ack['meaning'] == 'Queued, NOT completed'
                    for _ in range(30):
                        state = exchange({'type': 'GET_STATE'})
                        if state['completed_sequence'] == 0:
                            break
                        time.sleep(.1)
                    assert state['completed_sequence'] == 0
                    assert abs(state['joint_positions'][0] - q[0]) < .005
                    stream.close(); client.close(); stream = client = None
                    held = wait_for(lambda s: not s['board_connected'])
                    assert held['hold_latched'] and held['fault'] == 'CONNECTION_LOST'
                    client, stream = connect(token)
                    welcome = exchange({'type': 'HELLO', 'token': token})
                    assert welcome['requires_resume']
                    time.sleep(.2)
                    state = exchange({'type': 'GET_STATE'})
                    assert state['sim_time'] == held['sim_time']
                    old = context(state)
                    reset = exchange({'type': 'RESET', **old})
                    assert reset['type'] == 'ACK' and reset['run_id'] != old['run_id']
                    assert exchange({'type': 'ABORT', **old})['type'] == 'REJECTED'
                reports.append({'mode': mode, 'run_id': state['run_id'], 'episode': state['episode'],
                                'model_sha256': state['model_sha256'], 'render': state['render'],
                                'metrics': state['metrics'], 'physical_board_tested': False})
                print('PASS:', mode, 'end-to-end API and cameras', json.dumps(state['render']), flush=True)
            finally:
                if stream:
                    stream.close()
                if client:
                    client.close()
                stop_process(process)
                log.close()
    (output / 'runtime-report.json').write_text(json.dumps(reports, indent=2) + '\n')


if __name__ == '__main__':
    check()
