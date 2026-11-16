"""Regression tests for measured motion, session loss, reset and real contacts."""
from dataclasses import replace
import json
import time
import unittest

import numpy as np

from engine import Simulation
from protocol import ProtocolError, SCHEMA_VERSION


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.sim = Simulation('local')

    def tearDown(self):
        self.sim.close()

    def command(self, kind='ACTION', **fields):
        s = self.sim
        item = {'type': kind, 'schema_version': SCHEMA_VERSION,
                'run_id': s.run_id, 'session_id': s.session_id, **fields}
        return s.command(item, from_board=s.mode == 'board')

    def move(self, sequence=0, delta=.2, **fields):
        q = self.sim._joints()
        q[0] += delta
        return self.command(sequence_id=sequence, joint_targets=q, duration=1, **fields)

    def use_board(self):
        self.sim.close()
        self.sim = Simulation('board')
        self.sim.set_session(True)

    def test_feedback_is_measured_and_completion_is_separate_from_ack(self):
        initial = np.array(self.sim._joints())
        self.move()
        self.assertEqual(self.sim.last_accepted_sequence, 0)
        self.assertEqual(self.sim.last_completed_sequence, -1)
        np.testing.assert_array_equal(self.sim._joints(), initial)
        for _ in range(800):
            self.sim.step()
        self.assertEqual(self.sim.last_completed_sequence, 0)
        self.assertAlmostEqual(self.sim._joints()[0], initial[0] + .2, delta=.005)

    def test_disconnect_destroys_queue_and_reconnect_does_not_move(self):
        self.use_board()
        self.move(delta=.5)
        self.move(sequence=1, delta=.7)
        for _ in range(180):
            self.sim.step()
        self.assertGreater(abs(self.sim.data.qvel[self.sim.vids[0]]), .1)
        old_session = self.sim.session_id
        self.sim.set_session(False, session_id=old_session)
        stopped = self.sim.data.qpos.copy()
        self.sim.set_session(True)
        self.sim.set_session(False, session_id=old_session)  # stale handler cannot close new session
        for _ in range(1000):
            self.sim.step()
        np.testing.assert_array_equal(self.sim.data.qpos, stopped)
        self.assertTrue(self.sim.session_active)
        self.assertTrue(self.sim.hold_latched)
        self.assertIsNone(self.sim.action)
        self.assertFalse(self.sim.actions)
        with self.assertRaises(ProtocolError):
            self.move(sequence=2)
        self.command('RESUME')
        for _ in range(500):
            self.sim.step()
        np.testing.assert_allclose(self.sim.data.qpos[self.sim.qids], stopped[self.sim.qids], atol=.01)

    def test_late_heartbeat_cannot_revive_queued_action(self):
        self.use_board()
        self.move()
        self.sim.last_board_heartbeat -= 3
        self.sim.heartbeat(self.sim.session_id)
        self.assertEqual(self.sim.fault, 'HEARTBEAT_TIMEOUT')
        self.assertTrue(self.sim.hold_latched)
        self.assertFalse(self.sim.actions)

    def test_only_one_gateway_owns_a_session(self):
        self.use_board()
        owner = self.sim.session_id
        with self.assertRaises(ProtocolError):
            self.sim.set_session(True)
        self.assertEqual(self.sim.session_id, owner)

    def test_board_mode_refuses_local_control_and_reference(self):
        self.use_board()
        context = dict(schema_version=SCHEMA_VERSION, run_id=self.sim.run_id, session_id=self.sim.session_id)
        with self.assertRaises(ProtocolError):
            self.sim.command(dict(type='RESET', **context))
        with self.assertRaises(ProtocolError):
            self.sim.start_reference(context)

    def test_abort_requires_explicit_resume_or_reset(self):
        self.move()
        self.command('ABORT')
        self.assertFalse(self.sim.actions)
        with self.assertRaises(ProtocolError):
            self.move(sequence=1)
        self.command('RESET')
        self.assertFalse(self.sim.hold_latched)
        self.assertEqual(self.sim.task.status, 'READY')
        self.assertEqual(self.sim.last_accepted_sequence, -1)

    def test_reset_invalidates_old_run_commands(self):
        old = dict(type='ABORT', schema_version=SCHEMA_VERSION, run_id=self.sim.run_id, session_id=self.sim.session_id)
        self.command('RESET')
        with self.assertRaises(ProtocolError):
            self.sim.command(old)
        self.assertFalse(self.sim.hold_latched)

    def test_missing_version_and_session_are_rejected(self):
        with self.assertRaises(ProtocolError):
            self.sim.command({'type': 'RESET'})
        with self.assertRaises(ProtocolError):
            self.sim.command({'type': 'RESET', 'schema_version': 1, 'run_id': self.sim.run_id, 'session_id': self.sim.session_id})

    def test_seeded_reset_reproduces_objects_and_pose(self):
        self.command('RESET', seed=42, randomize=True)
        first = self.sim.data.qpos.copy()
        for _ in range(100):
            self.sim.step()
        self.command('RESET', seed=42, randomize=True)
        np.testing.assert_array_equal(self.sim.data.qpos, first)
        self.command('RESET', seed=43, randomize=True)
        self.assertFalse(np.array_equal(self.sim.data.qpos, first))

    def test_invalid_chunk_is_rejected_atomically(self):
        q = self.sim._joints()
        q2 = q.copy(); q2[0] += .5
        with self.assertRaises(ProtocolError):
            self.command('ACTION_CHUNK', sequence_id=0, points=[
                {'time_from_start': .1, 'joint_targets': q},
                {'time_from_start': .11, 'joint_targets': q2}])
        self.assertFalse(self.sim.actions)
        self.assertEqual(self.sim.last_accepted_sequence, -1)

    def test_valid_chunk_and_next_action_complete_in_order(self):
        q = self.sim._joints()
        q[0] += .1
        self.command('ACTION_CHUNK', sequence_id=0, points=[{'time_from_start': .5, 'joint_targets': q}])
        q[0] += .1
        self.command(sequence_id=1, joint_targets=q, duration=1)
        completed = []
        for _ in range(1500):
            self.sim.step()
            if self.sim.last_completed_sequence not in completed:
                completed.append(self.sim.last_completed_sequence)
        self.assertEqual(completed, [-1, 0, 1])
        self.assertEqual(self.sim.status, 'DONE')

    def test_expired_queue_item_latches_hold(self):
        self.move()
        self.sim.actions[0] = replace(self.sim.actions[0], valid_until=time.monotonic() - 1)
        self.sim.step()
        self.assertEqual(self.sim.fault, 'STALE_ACTION')
        self.assertEqual(self.sim.last_applied_sequence, -1)

    def test_excess_speed_and_queue_overflow_rejected(self):
        with self.assertRaises(ProtocolError):
            self.move(delta=2)
        for i in range(self.sim.settings['queue_capacity']):
            self.move(sequence=i, delta=0)
        with self.assertRaises(ProtocolError):
            self.move(sequence=20, delta=0)

    def test_ball_already_in_box_is_not_scored_as_success(self):
        s = self.sim
        jid = s.mj.mj_name2id(s.model, s.mj.mjtObj.mjOBJ_JOINT, 'red_ball_free')
        address = s.model.jnt_qposadr[jid]
        s.data.qpos[address:address+3] = [-.18, .16, .028]
        s.mj.mj_forward(s.model, s.data)
        s.task.start(0)
        for _ in range(600):
            s.step()
        self.assertTrue(s.task.in_box)
        self.assertFalse(s.task.grasped)
        self.assertNotEqual(s.task.status, 'SUCCESS')

    def test_reference_grasps_lifts_and_releases_with_real_contacts(self):
        s = self.sim
        s.start_reference(dict(schema_version=SCHEMA_VERSION, run_id=s.run_id, session_id=s.session_id))
        minimum = 1
        for _ in range(9000):
            s.step()
            minimum = min(minimum, s.data.xpos[s.task.bodies['red_ball'], 2])
            if s.hold_latched or (s.task.status == 'SUCCESS' and not s.reference_active):
                break
        self.assertEqual(s.task.status, 'SUCCESS', s.snapshot())
        self.assertGreater(s.task.max_height, .12)
        self.assertGreater(minimum, .015)  # radius 16 mm: table penetration stays below 1 mm
        self.assertFalse(s.task.jaw_contacts(s.data))
        self.assertEqual(s.model.neq, 0)  # no weld/attachment constraint
        json.dumps(s.snapshot(), allow_nan=False)
        json.dumps(s.evaluation(), allow_nan=False)


if __name__ == '__main__':
    unittest.main()
