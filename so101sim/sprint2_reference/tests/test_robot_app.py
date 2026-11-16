"""The Robo Arm App Lab app (robo-arm/python/robot_app.py) against the REAL simulator.

Same code the board runs after pressing Run, except: Arduino Bridge -> NativeBridge (the same
controller.h compiled with g++), SmolVLA -> a fixed small chunk, camera images -> /api/state
(read through camera.sock, so the relay HTTP path is still used). No torch needed.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'robo-arm' / 'python'))
sys.path.insert(0, str(ROOT / 'tests'))
import robot_app                                   # noqa: E402
import smolvla                                     # noqa: E402
from test_bridge import BoardRehearsal, NativeBridge   # noqa: E402

QUIET = dict(log=lambda *a, **k: None)


def state_observe(camera_socket):
    return smolvla.http_get_json(camera_socket, '/api/state'), {}


def stub_loader(offset=0.01, count=10):
    def load(_config, _smol):
        def infer(packet, _images):
            base = packet['joint_positions']
            chunk = []
            for step in range(count):
                target = list(base)
                target[0] += offset * (step + 1)
                chunk.append(smolvla.to_dataset(target))   # the model speaks dataset units
            return chunk, {'inference_t1_t2_s': 0.0}
        return infer, 'stub-model'
    return load


class NoBridge:
    def call(self, *args, **kwargs):
        raise AssertionError('direct mode must not call the STM32')


class RobotAppTests(unittest.TestCase):
    def config(self, **changes):
        config = dict(robot_app.DEFAULTS, cycles=2, stride=5)
        config.update(changes)
        return config

    def run_app(self, config, bridge=None, loader=None, board=None):
        bridge = bridge or NativeBridge()
        try:
            with patch.object(smolvla, 'observe', state_observe):
                return robot_app.run(config, board.app, bridge, load_model=loader, wait_timeout_s=20, **QUIET)
        finally:
            if isinstance(bridge, NativeBridge):
                bridge.close()

    def test_policy_every_model_action_goes_through_the_stm32(self):
        board = BoardRehearsal()
        try:
            result = self.run_app(self.config(), loader=stub_loader(), board=board)
            policy = board.app / 'runtime' / 'policy'
            summary = json.loads((policy / 'summary.json').read_text())
            results = [json.loads((policy / f'result-{k}.json').read_text()) for k in (0, 1)]
            traces = [json.loads(line) for p in (board.app / 'runtime').glob('robot-*.jsonl')
                      for line in p.read_text().splitlines()]
        finally:
            board.close()
        self.assertEqual(result, 'POLICY_PIPELINE_PASS')
        self.assertEqual([c['executed'] for c in summary['cycles']], [2, 2])
        self.assertEqual([a['sequence_id'] for r in results for a in r['executed']], [0, 1, 2, 3])
        approvals = [e for e in traces if e.get('event') == 'mcu_reply' and e.get('operation') == 3]
        self.assertEqual(len(approvals), 4)   # one STM32 approval per forwarded action
        for r in results:
            for action in r['executed']:
                self.assertAlmostEqual(action['reached_rad'][0], action['target_rad'][0], delta=0.03)

    def test_out_of_range_model_action_is_refused_by_firmware(self):
        board = BoardRehearsal()
        try:
            result = self.run_app(self.config(cycles=3), loader=stub_loader(offset=0.6), board=board)
            first = json.loads((board.app / 'runtime/policy/result-0.json').read_text())
            later = (board.app / 'runtime/policy/result-1.json').exists()
        finally:
            board.close()
        self.assertEqual(result, 'POLICY_STOPPED')
        self.assertEqual(first['status'], 'mcu_rejected')
        self.assertIn(first['code'], ('LIMIT', 'SPEED'))
        self.assertFalse(later)   # fail closed: no further cycles

    def test_smoke_mode(self):
        board = BoardRehearsal()
        try:
            self.assertEqual(self.run_app(self.config(mode='smoke'), board=board), 'SMOKE_PASS')
        finally:
            board.close()

    def test_direct_mode_never_calls_the_stm32(self):
        board = BoardRehearsal()
        try:
            result = self.run_app(self.config(mode='direct'), bridge=NoBridge(), loader=stub_loader(), board=board)
            summary = json.loads((board.app / 'runtime/policy/summary.json').read_text())
        finally:
            board.close()
        self.assertEqual(result, 'DIRECT_PIPELINE_PASS')
        self.assertFalse(summary['mcu_involved'])

    def test_probe_needs_no_laptop(self):
        with tempfile.TemporaryDirectory() as app:
            bridge = NativeBridge()
            try:
                result = robot_app.run(self.config(mode='probe'), app, bridge, **QUIET)
            finally:
                bridge.close()
        self.assertEqual(result, 'PROBE_PASS')

    def test_without_laptop_it_stops_instead_of_moving(self):
        with tempfile.TemporaryDirectory() as app:
            bridge = NativeBridge()
            try:
                result = robot_app.run(self.config(mode='smoke'), app, bridge, wait_timeout_s=1, **QUIET)
            finally:
                bridge.close()
        self.assertEqual(result, 'STOPPED')

    def test_config_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            path.write_text(json.dumps({'mode': 'fly'}))
            with self.assertRaises(ValueError):
                robot_app.read_config(path)
            path.write_text(json.dumps({'mode': 'smoke'}))
            self.assertEqual(robot_app.read_config(path)['cycles'], 3)
        self.assertEqual(json.loads((ROOT.parent / 'robo-arm/config.json').read_text())['mode'], 'policy')


if __name__ == '__main__':
    unittest.main()
