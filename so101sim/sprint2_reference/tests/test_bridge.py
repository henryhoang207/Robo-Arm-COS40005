"""STM32 firmware logic + Robo Arm gateway, on the laptop.

NativeBridge runs the SAME robo-arm/sketch/controller.h compiled with g++
(tests/native_driver.cpp -> runtime/native-driver); it stands in for Arduino Bridge.
"""
import json
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT.parent / 'robo-arm'               # the App Lab app that goes to the board
sys.path.insert(0, str(APP / 'python'))
from gateway import Gateway, Simulator, probe   # noqa: E402


POSE = [-750000, -200000, 200000, 1400000, 0, 800000]


class NativeBridge:
    """Test-only Arduino Bridge stand-in running the SAME C++ supervisor source."""
    def __init__(self):
        self.process = subprocess.Popen([str(ROOT / 'runtime/native-driver')], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, text=True)
        self.origin = time.monotonic()
        self.now = None

    def call(self, method, packet, timeout=1):
        assert method == 'so101_exchange_v1'
        now = self.now if self.now is not None else int((time.monotonic()-self.origin)*1000)
        self.process.stdin.write(' '.join(map(str, [now, *packet])) + '\n')
        self.process.stdin.flush()
        return list(map(int, self.process.stdout.readline().split()))

    def close(self):
        self.process.stdin.close()
        self.process.wait(timeout=2)
        self.process.stdout.close()


class FirmwareTests(unittest.TestCase):
    def setUp(self):
        self.bridge = NativeBridge(); self.bridge.now = 0

    def tearDown(self):
        self.bridge.close()

    def rpc(self, op, *data, epoch=77):
        return self.bridge.call('so101_exchange_v1', [1, op, epoch, *data])

    def opened(self):
        self.assertEqual(self.rpc(1, *POSE)[1:5], [0, 1, 77, -1])

    def approve(self, q=None, seq=0, duration=2000, timeout=5000):
        return self.rpc(3, seq, duration, timeout, 0, *(q or POSE))

    def test_boot_stays_held_and_probe_is_read_only(self):
        self.assertEqual(probe(self.bridge)[2], 0)
        self.assertNotEqual(self.approve()[1], 0)

    def test_complete_lifecycle_echoes_action(self):
        self.opened()
        q=POSE.copy(); q[0]+=120000
        r=self.approve(q)
        self.assertEqual(r[1:3], [0,2]); self.assertEqual(r[4:], [0,2000,5000,0,*q])
        self.assertEqual(self.rpc(4,0)[2],3)
        self.assertEqual(self.rpc(5,0,0,*POSE)[2],3)
        self.assertEqual(self.rpc(5,0,1,*q)[2],1)

    def test_invalid_length_protocol_and_joint_bounds(self):
        self.opened()
        self.assertEqual(self.rpc(3,0)[1],1)
        self.assertEqual(self.bridge.call('so101_exchange_v1',[9,2,77])[1],1)
        q=POSE.copy();q[0]=2000000
        self.assertEqual(self.approve(q)[1],6)

    def test_excess_speed_and_invalid_timing(self):
        self.opened(); q=POSE.copy();q[0]+=1000000
        self.assertEqual(self.approve(q,duration=100)[1],7)
        self.assertEqual(self.approve(timeout=2000)[1],1)

    def test_old_epoch_and_duplicate_sequence_rejected(self):
        self.opened()
        self.assertEqual(self.rpc(2,epoch=78)[1],2)
        self.approve();self.rpc(4,0);self.rpc(5,0,1,*POSE)
        self.assertEqual(self.approve()[1],5)

    def test_busy_and_feedback_sequence_rejected(self):
        self.opened();self.approve()
        self.assertEqual(self.rpc(1,*POSE,epoch=78)[1],4)
        self.rpc(4,0)
        self.assertEqual(self.rpc(5,9,1,*POSE)[1],5)

    def test_late_heartbeat_cannot_resume(self):
        self.opened(); self.bridge.now=1500
        self.assertEqual(self.rpc(2)[1:3],[3,0])
        self.assertEqual(self.rpc(1,*POSE)[1],2)
        self.assertEqual(self.rpc(1,*POSE,epoch=78)[1:3],[0,1])

    def test_pending_approval_expires_even_with_heartbeat(self):
        self.opened();self.approve();self.bridge.now=700;self.rpc(2)
        self.bridge.now=1000
        self.assertEqual(self.rpc(4,0)[1:3],[3,0])

    def test_execution_deadline_independent_of_heartbeat(self):
        self.opened();self.approve(timeout=2500);self.rpc(4,0)
        for now in (1000,2000):self.bridge.now=now;self.rpc(2)
        self.bridge.now=2500
        self.assertEqual(self.rpc(2)[1:3],[3,0])

    def test_timer_wrap_and_abort(self):
        self.bridge.now=2**32-1000;self.opened()
        self.bridge.now=100
        self.assertEqual(self.rpc(2)[1],0)
        self.assertEqual(self.rpc(6)[2],0)
        self.assertEqual(self.rpc(2)[1],3)


class FakeSimulator:
    def __init__(self):self.sent=[];self.context={}
    def state(self):return {'joint_positions':[q/1e6 for q in POSE], 'hold_latched':False,
                           'queue_depth':0,'run_id':'test-run','session_id':'test-session'}
    def command(self,kind,**fields):self.sent.append(kind)
    def close(self):pass


class GatewayRejectionTests(unittest.TestCase):
    def test_rpc_unavailable_never_forwards_action(self):
        class Broken:
            def call(self,*args,**kwargs):raise TimeoutError('MCU missing')
        sim=FakeSimulator(); gateway=Gateway(Broken(),sim)
        with self.assertRaises(TimeoutError):gateway.execute([q/1e6 for q in POSE])
        self.assertEqual(sim.sent,['ABORT'])

    def test_approval_payload_mismatch_never_forwards(self):
        bridge=NativeBridge();sim=FakeSimulator();gateway=Gateway(bridge,sim)
        try:
            gateway.open_episode()
            original=bridge.call
            def tampered(method,packet,timeout=1):
                r=original(method,packet,timeout)
                if packet[1]==3:r[-1]+=1
                return r
            bridge.call=tampered
            with self.assertRaisesRegex(RuntimeError,'does not match'):
                gateway.execute([q/1e6 for q in POSE])
            self.assertNotIn('ACTION',sim.sent)
            self.assertEqual(sim.sent[-1],'ABORT')
        finally:bridge.close()






def free_port():
    with socket.socket() as reserve:
        reserve.bind(('127.0.0.1', 0))
        return reserve.getsockname()[1]


class BoardRehearsal:
    """Laptop copy of the real USB setup, everything production code except the hardware:
    real MuJoCo (app.py --mode board) <- TCP <- board/host_relay.py <- runtime/*.sock <- robo-arm code.
    The temporary folder plays ~/ArduinoApps/robo-arm (Unix sockets need the Linux filesystem)."""

    def __init__(self, cameras=False):
        self.tmp = tempfile.TemporaryDirectory(prefix='so101-robo-arm-')
        self.app = Path(self.tmp.name)
        (self.app / 'app.yaml').write_text('name: test\n')
        (self.app / 'runtime').mkdir()
        self.token = self.app / 'runtime' / 'sim.token'
        self.token.write_text(secrets.token_urlsafe(32))
        self.tcp, self.web = free_port(), free_port()
        self.log = (ROOT / 'runtime/integration-server.log').open('w')
        extra = [] if cameras else ['--no-cameras']
        self.sim = subprocess.Popen([sys.executable, '-B', str(ROOT / 'app.py'), '--mode', 'board', '--no-viewer',
                                     '--no-logs', *extra, '--token-file', str(self.token),
                                     '--web-port', str(self.web), '--tcp-port', str(self.tcp)],
                                    cwd=ROOT, stdout=self.log, stderr=subprocess.STDOUT)
        self.relay = None
        self.start_relay()

    def start_relay(self):
        self.relay = subprocess.Popen([sys.executable, '-B', str(ROOT / 'board/host_relay.py'), '--app-dir',
                                       str(self.app), '--map', f'simulator.sock:{self.tcp}',
                                       '--map', f'camera.sock:{self.web}'], stdout=self.log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 15
        while not (self.app / 'runtime/camera.sock').exists() and time.monotonic() < deadline:
            time.sleep(.05)

    def simulator(self, timeout_s=20):
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                return Simulator(self.token, unix_socket=self.app / 'runtime/simulator.sock')
            except (OSError, ValueError, RuntimeError):
                if time.monotonic() > deadline:
                    raise
                time.sleep(.1)

    def close(self):
        for child in (self.relay, self.sim):
            if child and child.poll() is None:
                child.terminate()
                child.wait(timeout=8)
        self.log.close()
        self.tmp.cleanup()


class EndToEndTests(unittest.TestCase):
    def test_cpp_supervisor_gateway_relay_and_real_simulator(self):
        board, bridge, sim, events = BoardRehearsal(), NativeBridge(), None, []
        try:
            sim = board.simulator()
            gateway = Gateway(bridge, sim, lambda **event: events.append(event))
            gateway.open_episode()
            initial = sim.state()['joint_positions']; q = initial.copy(); q[0] += .12
            result = gateway.execute(q)
            self.assertEqual(result['completed_sequence'], 0)
            self.assertAlmostEqual(result['joint_positions'][0], q[0], delta=.005)
            self.assertEqual(gateway.execute(initial)['completed_sequence'], 1)
            # Lose the MCU while the simulator connection remains open: fail closed.
            def lost(*args, **kwargs):
                raise ConnectionError('Injected MCU link loss')
            bridge.call = lost
            with self.assertRaises(ConnectionError):
                gateway.execute(q)
            self.assertTrue(sim.state()['hold_latched'])
            report = {'transport': 'native C++ supervisor + host_relay unix socket, NOT hardware RPC',
                      'physical_board_tested': False, 'events': events, 'result': 'PASS'}
            (ROOT / 'runtime/integration-report.json').write_text(json.dumps(report, indent=2))
        finally:
            if sim:
                sim.close()
            bridge.close()
            board.close()

    def test_relay_loss_holds_the_simulator(self):
        board, bridge, sim = BoardRehearsal(), NativeBridge(), None
        try:
            sim = board.simulator()
            Gateway(bridge, sim).open_episode()
            self.assertFalse(sim.state()['hold_latched'])
            board.relay.terminate(); board.relay.wait(5)   # like pulling the USB cable
            with self.assertRaises((OSError, ConnectionError, ValueError)):
                for _ in range(30):
                    sim.state()
                    time.sleep(.1)
            sim.close(); sim = None
            time.sleep(.3)
            check = Simulator(board.token, port=board.tcp)   # laptop-side look at the simulator
            self.assertTrue(check.state()['hold_latched'])   # never resumes by itself
            check.close()
        finally:
            if sim:
                sim.close()
            bridge.close()
            board.close()


if __name__ == '__main__':
    unittest.main()
