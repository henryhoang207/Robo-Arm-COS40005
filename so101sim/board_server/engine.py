"""Thread-safe simulation state and execution. Camera workers render a separate data copy."""
from __future__ import annotations

from collections import deque
from dataclasses import asdict
import copy
import json
import math
from pathlib import Path
import threading
import time
import uuid

import numpy as np

from protocol import (JOINT_NAMES, SCHEMA_VERSION, Action, ProtocolError, parse_action,
                      validate_context, number)
from runtime_support import ROOT, Recorder, configure_graphics, model_identity
from task import BALLS, TaskEvaluator

MODEL_FILE = ROOT / 'models/SO101/workspace.xml'
POSE_FILE = ROOT / 'ready_pose.json'


class Simulation:
    def __init__(self, mode: str, camera_interval=None, board_link='usb', log_dir=None, settings=None):
        configure_graphics()
        import mujoco
        self.mj = mujoco
        if mode not in ('local', 'board'):
            raise ValueError('mode must be local or board')
        self.mode = mode
        self.board_link = board_link if mode == 'board' else None
        self.settings = json.loads((ROOT / 'settings.json').read_text('utf8'))
        if settings:
            self.settings.update(settings)
        for key in ('camera_fps', 'heartbeat_timeout_s', 'queue_horizon_s',
                    'position_tolerance_rad', 'settle_speed_rad_s', 'settle_time_s',
                    'episode_timeout_s', 'success_dwell_s', 'log_state_interval_s'):
            number(self.settings[key], key, .001, 3600)
        for key in ('queue_capacity', 'camera_width', 'camera_height'):
            value = self.settings[key]
            if type(value) is not int or not 1 <= value <= 4096:
                raise ValueError(f'Invalid {key}')
        self.max_speeds = np.array(self.settings['max_target_speed_rad_s'], dtype=float)
        if self.max_speeds.shape != (6,) or not np.all(np.isfinite(self.max_speeds)) or np.any(self.max_speeds <= 0):
            raise ValueError('max_target_speed_rad_s must contain six positive finite speeds')
        self.model = mujoco.MjModel.from_xml_path(str(MODEL_FILE))
        self.model.vis.global_.offwidth = max(self.model.vis.global_.offwidth, self.settings['camera_width'])
        self.model.vis.global_.offheight = max(self.model.vis.global_.offheight, self.settings['camera_height'])
        self.data = mujoco.MjData(self.model)
        self.identity = model_identity()
        self.lock = threading.RLock()
        names = tuple(mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
                      for i in range(self.model.nu))
        if names != JOINT_NAMES:
            raise RuntimeError(f'Wrong actuator list: {names}')
        self.aids, self.qids, self.vids, self.limits = [], [], [], []
        for name in JOINT_NAMES:
            jid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name)
            aid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, name)
            if jid < 0 or self.model.jnt_type[jid] != mujoco.mjtJoint.mjJNT_HINGE:
                raise RuntimeError('Missing hinge joint: ' + name)
            self.qids.append(int(self.model.jnt_qposadr[jid]))
            self.vids.append(int(self.model.jnt_dofadr[jid]))
            self.aids.append(aid)
            lo, hi = self.model.jnt_range[jid]
            clo, chi = self.model.actuator_ctrlrange[aid]
            self.limits.append((max(float(lo), float(clo)), min(float(hi), float(chi))))
        for name in ('overhead_camera', 'wrist_camera'):
            if mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_CAMERA, name) < 0:
                raise RuntimeError('Missing camera: ' + name)
        self.task = TaskEvaluator(mujoco, self.model, self.settings)
        self.recorder = Recorder(log_dir) if log_dir else None
        self.actions = deque()
        self.session_active = False
        self.session_id = uuid.uuid4().hex
        self.last_board_heartbeat = 0.0
        self.board_client = None
        self.hold_latched = False
        self.fault = None
        self.action = None
        self.reference_active = False
        self.action_start = 0.0
        self.start_q = None
        self.settled_since = None
        self.completion_reason = None
        self.camera_interval = camera_interval or 1.0 / self.settings['camera_fps']
        self.images = {}
        self.frame_bundle = None
        self.frame_id = 0
        self.camera_error = None
        self.camera_worker = None
        self.renderer = None
        self.render_info = {}
        self.metrics = {'real_time_factor': 0.0, 'discarded_wall_time_s': 0.0, 'physics_steps': 0}
        self.run_id = ''
        self.closed = False
        self._reset_locked(0, 'red_ball', False)

    def _event(self, kind, **fields):
        if self.recorder:
            self.recorder.emit(self.run_id, kind, sim_time=float(self.data.time), **fields)

    def _reset_locked(self, seed, target, randomize):
        if self.run_id:
            self.task.finish('ABORTED', 'RESET')
            self._event('run_end', episode=self.task.summary())
        self.mj.mj_resetData(self.model, self.data)
        pose = json.loads(POSE_FILE.read_text('utf8'))['joints']
        for i, name in enumerate(JOINT_NAMES):
            val = number(pose[name], name, *self.limits[i])
            self.data.qpos[self.qids[i]] = val
            self.data.ctrl[self.aids[i]] = val
        rng = np.random.default_rng(seed)
        if randomize:
            for name in BALLS:
                jid = self.mj.mj_name2id(self.model, self.mj.mjtObj.mjOBJ_JOINT, name + '_free')
                address = int(self.model.jnt_qposadr[jid])
                self.data.qpos[address:address + 2] += rng.uniform(-.008, .008, 2)
        self.mj.mj_forward(self.model, self.data)
        self.actions.clear()
        self.action = None
        self.reference_active = False
        self.hold_latched = False
        self.fault = None
        self.last_accepted_sequence = self.last_applied_sequence = self.last_completed_sequence = -1
        self.settled_since = None
        self.completion_reason = None
        self.run_id = uuid.uuid4().hex
        self.images = {}
        self.frame_bundle = None
        self.task.reset(target, seed)
        self.next_log_time = 0.0
        self.status = 'LOCAL_TEST' if self.mode == 'local' else ('BOARD_CONNECTED' if self.session_active else 'WAITING_FOR_BOARD')
        self._event('run_start', schema_version=SCHEMA_VERSION, mode=self.mode, seed=seed,
                    randomize=randomize, target=target, identity=self.identity, settings=self.settings,
                    mujoco_version=self.mj.__version__)

    def _joints(self):
        return self.data.qpos[self.qids].tolist()

    def _state_locked(self):
        frame = self.frame_bundle
        age = None if not frame else max(0.0, (time.monotonic_ns() - frame['captured_monotonic_ns']) / 1e9)
        return {
            'schema_version': SCHEMA_VERSION, 'run_id': self.run_id, 'session_id': self.session_id,
            'status': self.status, 'mode': self.mode, 'board_link': self.board_link, 'fault': self.fault,
            'hold_latched': self.hold_latched, 'joint_names': list(JOINT_NAMES), 'units': 'radians',
            'joint_positions': self._joints(), 'joint_velocities': self.data.qvel[self.vids].tolist(),
            'joint_limits': self.limits, 'target_positions': self.data.ctrl[self.aids].tolist(),
            'final_target_positions': list(self.action.targets) if self.action else None,
            'sim_time': round(float(self.data.time), 6), 'server_monotonic_ns': time.monotonic_ns(),
            'accepted_sequence': self.last_accepted_sequence, 'applied_sequence': self.last_applied_sequence,
            'completed_sequence': self.last_completed_sequence, 'completion_reason': self.completion_reason,
            'queue_depth': len(self.actions), 'queue_capacity': self.settings['queue_capacity'],
            'phase': self.action.label if self.action else None, 'reference_active': self.reference_active,
            'episode': self.task.summary(), 'board_connected': self.session_active,
            'last_board_heartbeat_age_s': max(0.0, time.monotonic() - self.last_board_heartbeat) if self.session_active else None,
            'mcu_execution_verified': False,
            'cameras': {name: name in self.images for name in ('overhead', 'wrist')},
            'camera_error': self.camera_error, 'frame_id': frame['frame_id'] if frame else None,
            'frame_sim_time': frame['sim_time'] if frame else None, 'frame_age_s': age,
            'frame_stale': age is None or age > max(1.0, 3 * self.camera_interval),
            'render': dict(self.render_info), 'metrics': dict(self.metrics),
            'geometry': self.identity['contact_model'], 'model_sha256': self.identity['model_sha256'],
            'logging': {'enabled': self.recorder is not None,
                        'dropped_records': self.recorder.dropped if self.recorder else 0,
                        'error': self.recorder.error if self.recorder else None},
        }

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self._state_locked())

    def evaluation(self):
        with self.lock:
            return {'run_id': self.run_id, 'sim_time': float(self.data.time), **self.task.ground_truth(self.data)}

    def get_frame(self, camera):
        with self.lock:
            return self.images.get(camera)

    def get_frame_packet(self, camera):
        with self.lock:
            if not self.frame_bundle or camera not in self.images:
                return None
            return self.images[camera], {key: self.frame_bundle[key] for key in
                                       ('frame_id', 'run_id', 'sim_time', 'captured_monotonic_ns')}

    def observation(self):
        from base64 import b64encode
        with self.lock:
            if self.frame_bundle is None:
                return None
            packet = copy.deepcopy(self.frame_bundle)
            images = dict(self.images)
        packet['image_encoding'] = 'jpeg/base64'
        packet['images'] = {name: b64encode(blob).decode('ascii') for name, blob in images.items()}
        packet['frame_age_s'] = max(0.0, (time.monotonic_ns() - packet['captured_monotonic_ns']) / 1e9)
        packet['stale'] = packet['frame_age_s'] > max(1.0, 3 * self.camera_interval)
        return packet

    def _hold_locked(self, reason, status='HOLD'):
        self.action = None
        self.actions.clear()
        self.reference_active = False
        self.data.ctrl[self.aids] = self.data.qpos[self.qids]
        # An explicit simulator pause: discard stored momentum, including free objects.
        # This is not a physical robot emergency stop.
        self.data.qvel[:] = 0
        self.data.qacc_warmstart[:] = 0
        self.mj.mj_forward(self.model, self.data)
        self.hold_latched = True
        self.fault = reason
        self.status = status
        self.settled_since = None
        self.task.finish('ABORTED', reason)
        self._event('hold', reason=reason, episode=self.task.summary())

    def _check_heartbeat_locked(self):
        if self.mode == 'board' and self.session_active:
            if time.monotonic() - self.last_board_heartbeat >= self.settings['heartbeat_timeout_s']:
                if self.fault != 'HEARTBEAT_TIMEOUT':
                    self._hold_locked('HEARTBEAT_TIMEOUT', 'WAITING_FOR_BOARD')
                return False
        return self.mode == 'local' or self.session_active

    def set_session(self, enabled, peer=None, session_id=None):
        with self.lock:
            if enabled:
                if self.session_active:
                    raise ProtocolError('Another gateway is connected')
                self.session_active = True
                self.session_id = uuid.uuid4().hex
                self.board_client = peer
                self.last_board_heartbeat = time.monotonic()
                self.status = 'HOLD' if self.hold_latched else 'BOARD_CONNECTED'
                self._event('connected', session_id=self.session_id)
                return self.session_id
            if session_id is not None and session_id != self.session_id:
                return
            if self.session_active:
                self._hold_locked('CONNECTION_LOST', 'WAITING_FOR_BOARD')
            self.session_active = False
            self.board_client = None
            self.last_board_heartbeat = 0.0

    def heartbeat(self, session_id=None):
        with self.lock:
            if session_id is not None and session_id != self.session_id:
                raise ProtocolError('Session is no longer active')
            self._check_heartbeat_locked()  # Late traffic must not erase the timeout.
            if self.session_active:
                self.last_board_heartbeat = time.monotonic()

    def _check_authority_locked(self, from_board):
        if self.mode == 'board':
            if not from_board or not self.session_active:
                raise ProtocolError('Only the authenticated board gateway may control board mode')
            self._check_heartbeat_locked()
        elif from_board:
            raise ProtocolError('Board control is unavailable in local mode')

    def _validate_speed_locked(self, action, previous):
        previous = np.array(previous)
        if action.points:
            last_t = 0.0
            for point in action.points:
                speed = np.abs(np.array(point.targets) - previous) / (point.time - last_t)
                if np.any(speed > self.max_speeds + 1e-8):
                    raise ProtocolError('Chunk exceeds configured target speed; increase time_from_start')
                previous, last_t = np.array(point.targets), point.time
        elif np.any(1.875 * np.abs(np.array(action.targets) - previous) / action.duration > self.max_speeds + 1e-8):
            raise ProtocolError('Move exceeds configured target speed; increase duration')

    def enqueue(self, action: Action, from_board=False, reference=False):
        with self.lock:
            self._check_authority_locked(from_board)
            if self.hold_latched:
                raise ProtocolError('Execution is on HOLD; send RESUME or RESET explicitly')
            if self.reference_active and not reference:
                raise ProtocolError('Reference run active; ABORT before manual control')
            if action.sequence_id <= self.last_accepted_sequence:
                raise ProtocolError('Stale or duplicated sequence_id')
            if len(self.actions) >= self.settings['queue_capacity']:
                raise ProtocolError('Queue full')
            if action.valid_until <= time.monotonic():
                raise ProtocolError('Action expired before acceptance')
            remaining = sum(a.duration for a in self.actions)
            if self.action:
                remaining += max(0.0, self.action.duration - (self.data.time - self.action_start))
            if remaining + action.duration > self.settings['queue_horizon_s']:
                raise ProtocolError('Queue time horizon exceeded')
            previous = (self.actions[-1].targets if self.actions else
                        self.action.targets if self.action else self._joints())
            self._validate_speed_locked(action, previous)
            self.actions.append(action)
            self.last_accepted_sequence = action.sequence_id
            self.task.start(float(self.data.time))
            record = asdict(action)
            record.pop('valid_until', None)
            self._event('accepted', action=record)

    def command(self, obj, from_board=False):
        with self.lock:
            self._check_authority_locked(from_board)
            validate_context(obj, self.run_id, self.session_id)
            kind = obj.get('type')
            if kind in ('ACTION', 'ACTION_CHUNK'):
                action = parse_action(obj, self.limits, self.last_accepted_sequence)
                self.enqueue(action, from_board)
                return {'type': 'ACK', 'sequence_id': action.sequence_id, 'meaning': 'Queued, NOT completed',
                        'run_id': self.run_id, 'queue_depth': len(self.actions)}
            if kind == 'ABORT':
                self._hold_locked('USER_ABORT')
            elif kind == 'RESUME':
                if not self._check_heartbeat_locked():
                    raise ProtocolError('Cannot resume without a healthy gateway')
                self.hold_latched = False
                self.fault = None
                self.status = 'IDLE'
                self._event('resumed')
            elif kind == 'RESET':
                seed = obj.get('seed', 0)
                target = obj.get('target', 'red_ball')
                randomize = obj.get('randomize', False)
                if type(seed) is not int or not 0 <= seed < 2**32:
                    raise ProtocolError('seed must be uint32')
                if target not in BALLS or type(randomize) is not bool:
                    raise ProtocolError('Invalid target or randomize flag')
                if self.mode == 'board' and not self._check_heartbeat_locked():
                    raise ProtocolError('Cannot reset without a healthy gateway')
                self._reset_locked(seed, target, randomize)
            else:
                raise ProtocolError('Unknown command type')
            return {'type': 'ACK', 'command': kind, 'run_id': self.run_id,
                    'session_id': self.session_id, 'status': self.status}

    def start_reference(self, context):
        with self.lock:
            if self.mode != 'local':
                raise ProtocolError('Local reference playback is disabled in board mode')
            validate_context(context, self.run_id, self.session_id)
            if self.action or self.actions or self.hold_latched or self.task.status != 'READY':
                raise ProtocolError('RESET to a fresh episode before reference playback')
            from reference import build_plan
            plan = build_plan(self)
            # Validate the entire plan before admitting any motion.
            previous = self._joints()
            actions = [parse_action(item, self.limits, self.last_accepted_sequence) for item in plan]
            for action in actions:
                self._validate_speed_locked(action, previous)
                previous = action.targets
            if len(actions) > self.settings['queue_capacity'] or sum(a.duration for a in actions) > self.settings['queue_horizon_s']:
                raise ProtocolError('Reference plan exceeds queue bounds')
            for action in actions:
                self.enqueue(action, False, reference=True)
            self.reference_active = True
            return {'type': 'ACK', 'meaning': 'Local reference plan queued', 'run_id': self.run_id,
                    'action_count': len(actions), 'controller': 'ground-truth reference, not AI'}

    def _control_target_locked(self, elapsed):
        action = self.action
        if not action.points:
            u = min(max(elapsed / action.duration, 0), 1)
            blend = u**3 * (10 - 15*u + 6*u*u)
            return self.start_q + blend * (np.array(action.targets) - self.start_q)
        previous, previous_t = self.start_q, 0.0
        for point in action.points:
            if elapsed <= point.time:
                u = np.clip((elapsed - previous_t) / (point.time - previous_t), 0, 1)
                return previous + u * (np.array(point.targets) - previous)
            previous, previous_t = np.array(point.targets), point.time
        return np.array(action.targets)

    def step(self):
        with self.lock:
            if not self._check_heartbeat_locked() or self.hold_latched:
                return
            if self.action is None and self.actions:
                action = self.actions.popleft()
                if time.monotonic() > action.valid_until:
                    self._hold_locked('STALE_ACTION', 'FAULT')
                    return
                self.action = action
                self.start_q = self.data.ctrl[self.aids].copy() if action.points else self.data.qpos[self.qids].copy()
                self.action_start = float(self.data.time)
                self.last_applied_sequence = action.sequence_id
                self.settled_since = None
                self.completion_reason = None
                self.status = 'RUNNING'
                self._event('applied', sequence_id=action.sequence_id, label=action.label)
            if self.action:
                elapsed = float(self.data.time) - self.action_start
                if elapsed > self.action.timeout:
                    self._hold_locked('EXECUTION_TIMEOUT', 'FAULT')
                    return
                self.data.ctrl[self.aids] = self._control_target_locked(elapsed)
            self.mj.mj_step(self.model, self.data)
            self.metrics['physics_steps'] += 1
            if not np.all(np.isfinite(self.data.qpos)) or not np.all(np.isfinite(self.data.qvel)):
                self._hold_locked('NONFINITE_PHYSICS', 'FAULT')
                return
            # Forward computes positions and contacts for the same post-step qpos used by feedback.
            self.mj.mj_forward(self.model, self.data)
            if self.action and self.data.time - self.action_start >= self.action.duration:
                error = np.abs(self.data.qpos[self.qids] - np.array(self.action.targets))
                tolerance = self.settings['position_tolerance_rad']
                grip_contact = (self.action.allow_gripper_contact and self.action.targets[5] < self.start_q[5]
                                and any(len(self.task.jaw_contacts(self.data, name)) == 2 for name in BALLS))
                reached = bool(np.all(error[:5] <= tolerance) and (error[5] <= tolerance or grip_contact))
                slow = bool(np.max(np.abs(self.data.qvel[self.vids])) <= self.settings['settle_speed_rad_s'])
                if reached and slow:
                    if self.settled_since is None:
                        self.settled_since = float(self.data.time)
                    if self.data.time - self.settled_since >= self.settings['settle_time_s']:
                        self.last_completed_sequence = self.action.sequence_id
                        self.completion_reason = 'GRIPPER_CONTACT' if grip_contact and error[5] > tolerance else 'TARGET_REACHED'
                        self._event('completed', sequence_id=self.action.sequence_id, reason=self.completion_reason)
                        self.action = None
                        self.status = 'DONE'
                        if not self.actions:
                            self.reference_active = False
                else:
                    self.settled_since = None
            if self.task.update(self.data):
                self._event('episode_result', episode=self.task.summary())
                if self.task.status == 'FAILURE':
                    self._hold_locked(self.task.reason, 'FAULT')
            if self.data.time >= self.next_log_time:
                self._event('state', sequence_id=self.last_applied_sequence, joint_positions=self._joints(),
                            joint_velocities=self.data.qvel[self.vids].tolist(),
                            target_positions=self.data.ctrl[self.aids].tolist(),
                            evaluation=self.task.ground_truth(self.data))
                self.next_log_time = float(self.data.time) + self.settings['log_state_interval_s']

    def capture(self):
        # Synchronous capture is useful for diagnostics; app.py uses the independent worker.
        from cameras import capture_pair
        if self.renderer is None:
            self.renderer = self.mj.Renderer(self.model, height=self.settings['camera_height'],
                                            width=self.settings['camera_width'])
        capture_pair(self, self.renderer, self.mj.MjData(self.model))

    def start_cameras(self):
        from cameras import CameraWorker
        if self.camera_worker is None:
            self.camera_worker = CameraWorker(self)
            self.camera_worker.start()

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.camera_worker:
            self.camera_worker.stop()
        if self.renderer:
            self.renderer.close()
        with self.lock:
            self.task.finish('ABORTED', 'APPLICATION_CLOSED')
            self._event('run_end', episode=self.task.summary())
        if self.recorder:
            self.recorder.close()
