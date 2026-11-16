"""Laptop tests for the model -> MCU -> simulator loop, using the SAME C++ supervisor.

The simulator here is a small in-memory stand-in (instant motion); the real MuJoCo
path is exercised at the lab. No torch/LeRobot is needed.
"""
import json
import math
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'robo-arm' / 'python'))
sys.path.insert(0, str(ROOT / 'tests'))
from policy_loop import SCHEMA, plan_duration, run_policy   # noqa: E402
import smolvla as policy_runner                             # noqa: E402  (mapping helpers)
from test_bridge import NativeBridge, POSE                  # noqa: E402

START = [q / 1e6 for q in POSE]


class World:
    def __init__(self):
        self.q, self.hold, self.accepted, self.run_id = START.copy(), True, -1, 'run-A'
        self.sent, self.sessions = [], 0


class Conn:
    def __init__(self, world):
        self.w, self.sock = world, object()
        world.sessions += 1
        self.session = f's{world.sessions}'

    def state(self):
        w = self.w
        return {'joint_positions': w.q.copy(), 'hold_latched': w.hold, 'queue_depth': 0,
                'run_id': w.run_id, 'session_id': self.session, 'accepted_sequence': w.accepted,
                'completed_sequence': w.accepted, 'fault': None, 'completion_reason': 'TARGET_REACHED',
                'sim_time': 1.0}

    def command(self, kind, **fields):
        w = self.w
        w.sent.append((kind, fields.get('sequence_id')))
        if kind == 'RESET':
            w.q, w.hold, w.accepted = START.copy(), False, -1
        elif kind == 'RESUME':
            w.hold = False
        elif kind == 'ABORT':
            w.hold = True
        elif kind == 'ACTION':
            assert not w.hold and fields['sequence_id'] > w.accepted
            w.q, w.accepted = list(fields['joint_targets']), fields['sequence_id']
        return {'type': 'ACK'}

    def close(self):
        self.sock = None
        self.w.hold = True     # disconnect latches HOLD, like the real simulator


def fake_runner(directory, cycles, make_actions, stop):
    """Plays the IQ8 host runner: waits for ready-k, writes chunk-k."""
    for cycle in range(cycles):
        path = directory / f'ready-{cycle}.json'
        while not path.exists():
            if stop.is_set():
                return
            time.sleep(.01)
        ready = json.loads(path.read_text())
        chunk = {'schema': SCHEMA, 'session': ready['session'], 'cycle': cycle, 'run_id': ready['run_id'],
                 'observation_joint_positions': ready['joint_positions'],
                 'actions_rad': make_actions(ready['joint_positions'])}
        (directory / f'chunk-{cycle}.json').write_text(json.dumps(chunk))


def drift_actions(q):
    # 50 small steps on shoulder_pan, like a smooth VLA chunk.
    return [[q[0] + 0.002 * (i + 1), *q[1:]] for i in range(50)]


class PolicyLoopTests(unittest.TestCase):
    def run_loop(self, cycles, make_actions):
        world, bridge, events, stop = World(), NativeBridge(), [], threading.Event()
        with tempfile.TemporaryDirectory() as td:
            runtime = Path(td)
            (runtime / 'policy').mkdir()
            thread = threading.Thread(target=fake_runner, args=(runtime / 'policy', cycles, make_actions, stop))
            thread.start()
            try:
                summary = run_policy(bridge, {'mode': 'policy', 'cycles': cycles, 'stride': 5,
                                              'chunk_timeout_s': 10}, runtime,
                                     lambda **e: events.append(e), lambda: Conn(world),
                                     log=lambda *a, **k: None)
                results = [json.loads(p.read_text()) for p in sorted((runtime / 'policy').glob('result-*.json'))]
            finally:
                stop.set(); thread.join(5); bridge.close()
        return summary, results, world, events

    def test_two_cycles_every_action_mcu_approved(self):
        summary, results, world, events = self.run_loop(2, drift_actions)
        self.assertTrue(summary['all_cycles_completed'])
        self.assertEqual([len(r['executed']) for r in results], [10, 10])
        actions = [s for k, s in world.sent if k == 'ACTION']
        self.assertEqual(actions, list(range(20)))            # sequence continues across sessions
        approvals = [e for e in events if e.get('event') == 'mcu_reply' and e['operation'] == 3]
        self.assertEqual(len(approvals), 20)                   # one STM32 approval per forwarded ACTION
        self.assertIn(('RESUME', None), world.sent)
        self.assertAlmostEqual(world.q[0], START[0] + 0.2, places=5)
        self.assertTrue(world.hold)                            # ends held

    def test_out_of_range_action_refused_by_firmware(self):
        def bad(q):
            return [[q[0] + 0.002, *q[1:]], *[[2.5, *q[1:]]] * 49]   # shoulder_pan beyond +1.92 rad
        summary, results, world, events = self.run_loop(3, bad)
        self.assertFalse(summary['all_cycles_completed'])
        self.assertEqual(len(results), 1)                      # fail closed: no further cycles
        self.assertEqual(results[0]['status'], 'mcu_rejected')
        self.assertEqual(results[0]['code'], 'LIMIT')
        self.assertEqual([s for k, s in world.sent if k == 'ACTION'], [])
        self.assertTrue(any(e.get('event') == 'mcu_rejected' and e['code_name'] == 'LIMIT' for e in events))

    def test_stale_observation_never_reaches_mcu(self):
        def stale_world_actions(q):
            return drift_actions(q)
        world = World()
        original = fake_runner

        def moved_runner(directory, cycles, make_actions, stop):
            path = directory / 'ready-0.json'
            while not path.exists():
                time.sleep(.01)
            ready = json.loads(path.read_text())
            observed = ready['joint_positions'].copy(); observed[1] += 0.1
            chunk = {'schema': SCHEMA, 'session': ready['session'], 'cycle': 0, 'run_id': ready['run_id'],
                     'observation_joint_positions': observed, 'actions_rad': drift_actions(observed)}
            (directory / 'chunk-0.json').write_text(json.dumps(chunk))
        bridge, events = NativeBridge(), []
        with tempfile.TemporaryDirectory() as td:
            runtime = Path(td); (runtime / 'policy').mkdir()
            t = threading.Thread(target=moved_runner, args=(runtime / 'policy', 1, None, None)); t.start()
            try:
                summary = run_policy(bridge, {'cycles': 1, 'chunk_timeout_s': 10}, runtime,
                                     lambda **e: events.append(e), lambda: Conn(world), log=lambda *a, **k: None)
                result = json.loads((runtime / 'policy/result-0.json').read_text())
            finally:
                t.join(5); bridge.close()
        self.assertEqual(result['status'], 'stopped')
        self.assertIn('Stale observation', result['error'])
        self.assertFalse(any(e.get('event') == 'mcu_reply' and e['operation'] == 1 for e in events))
        self.assertEqual([k for k, _ in world.sent], ['RESET'])

    def test_duration_respects_firmware_speed_rule(self):
        measured = START.copy(); target = measured.copy(); target[0] += 0.5
        duration = plan_duration(target, measured, 5 / 30)
        self.assertLessEqual(1.875 * 0.5 / duration, 2.0)
        self.assertEqual(plan_duration(measured, measured, 5 / 30), round(5 / 30, 3))

    def test_mapping_round_trip_and_ranges(self):
        rad = [-0.75, -0.2, 0.2, 1.4, 0.0, 0.8]
        back = policy_runner.to_radians(policy_runner.to_dataset(rad))
        for a, b in zip(rad, back):
            self.assertAlmostEqual(a, b, places=9)
        self.assertAlmostEqual(policy_runner.to_dataset([0, 0, 0, 0, 0, -0.17453])[5], 0.0, places=6)
        self.assertAlmostEqual(policy_runner.to_radians([90, 0, 0, 0, 0, 100])[0], math.pi / 2)



if __name__ == '__main__':
    unittest.main()
