"""One MuJoCo instance: all mutations and GL rendering occur on the main thread."""
from __future__ import annotations
import json
import io
import math
import threading
import queue
import time
from pathlib import Path
from typing import Optional

from protocol import JOINT_NAMES, Action

ROOT = Path(__file__).resolve().parent
MODEL_FILE = ROOT/'models'/'SO101'/'workspace.xml'
POSE_FILE = ROOT/'ready_pose.json'

class Simulation:
    def __init__(self, mode: str, camera_interval: float = 0.25, *, model=None, ready_pose=None):
        import mujoco
        self.mj = mujoco
        self.mode = mode
        self.model = mujoco.MjModel.from_xml_path(str(MODEL_FILE)) if model is None else model
        self.ready_pose = ready_pose
        self.data = mujoco.MjData(self.model)
        names = tuple(mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
                      for i in range(self.model.nu))
        if names != JOINT_NAMES:
            raise RuntimeError(f'Wrong actuator list: {names}')
        self.aids = []
        self.qids = []
        self.limits = []
        for name in JOINT_NAMES:
            jid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name)
            aid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, name)
            if jid < 0 or aid < 0:
                raise RuntimeError('Missing joint/actuator '+name)
            if self.model.jnt_type[jid] != mujoco.mjtJoint.mjJNT_HINGE:
                raise RuntimeError('Not a hinge joint: '+name)
            self.qids.append(int(self.model.jnt_qposadr[jid]))
            self.aids.append(aid)
            joint_lo, joint_hi = self.model.jnt_range[jid]
            ctrl_lo, ctrl_hi = self.model.actuator_ctrlrange[aid]
            self.limits.append((max(float(joint_lo),float(ctrl_lo)), min(float(joint_hi),float(ctrl_hi))))
        for camera in ('overhead_camera','wrist_camera'):
            if mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_CAMERA, camera) < 0:
                raise RuntimeError('Missing camera: '+camera)
        if model is None:
            for body in ('red_ball', 'green_ball','blue_ball','yellow_ball','drop_box'):
                if mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_BODY, body) < 0:
                    raise RuntimeError('Missing object: '+body)
        self.lock=threading.RLock()
        self.actions: queue.Queue[Action] = queue.Queue(maxsize=1)
        self.session_active = False
        self.last_board_heartbeat = 0.0
        self.board_client = None
        self.last_accepted_sequence = -1
        self.last_applied_sequence = -1
        self.status = 'LOCAL_TEST' if mode == 'local' else 'WAITING_FOR_BOARD'
        self.fault: Optional[str]=None
        self.action = None
        self.start_q = None
        self.action_start = None
        self.images = {}
        self.renderer = None
        self.camera_error = None
        self.camera_interval = camera_interval
        self.snapshot_state = {}
        self._set_initial_pose()
        self._publish_locked()

    def _set_initial_pose(self):
        pose = self.ready_pose
        if pose is None:
            pose = json.loads(POSE_FILE.read_text('utf8'))['joints']
        self.mj.mj_resetData(self.model,self.data)
        for index,name in enumerate(JOINT_NAMES):
            val = float(pose[name])
            lo,hi=self.limits[index]
            if not math.isfinite(val) or not lo <= val <= hi:
                raise ValueError(f'Invalid ready pose {name}={val}; [{lo},{hi}]')
            self.data.qpos[self.qids[index]]=val
            self.data.ctrl[self.aids[index]]=val
        self.mj.mj_forward(self.model,self.data)

    def _joints(self):
        return [float(self.data.qpos[i]) for i in self.qids]

    def _publish_locked(self):
        self.snapshot_state = {
            'status':self.status, 'mode':self.mode,'fault':self.fault,
            'joint_names':list(JOINT_NAMES),'joint_positions':self._joints(),
            'joint_limits':self.limits, 'target_positions':[float(self.data.ctrl[i]) for i in self.aids],
            'sim_time':round(float(self.data.time),4),
            'accepted_sequence':self.last_accepted_sequence,
            'applied_sequence':self.last_applied_sequence,
            'cameras':{c: c in self.images for c in ('overhead','wrist')},
            'camera_error':self.camera_error,
            'board_connected':self.session_active,
            'last_board_heartbeat_age_s':(round(time.monotonic()-self.last_board_heartbeat,2)
                                          if self.session_active else None),
            'geometry':'PROXY MESHES — import official STL before task benchmarking',
        }

    def snapshot(self):
        with self.lock:
            return dict(self.snapshot_state)

    def get_frame(self, camera):
        with self.lock:
            return self.images.get(camera)

    def set_session(self, enabled: bool, peer: Optional[str] = None):
        with self.lock:
            self.session_active=enabled
            self.board_client=peer if enabled else None
            self.last_board_heartbeat=time.monotonic() if enabled else 0.0
            if enabled:
                self.fault=None
                self.status='BOARD_CONNECTED'
            else:
                self.action=None
                self.status='WAITING_FOR_BOARD' if self.mode=='board' else 'LOCAL_TEST'
                while True:
                    try: self.actions.get_nowait()
                    except queue.Empty: break
            self._publish_locked()

    def heartbeat(self):
        with self.lock:
            if self.session_active:
                self.last_board_heartbeat=time.monotonic()

    def enqueue(self, action: Action, from_board: bool) -> None:
        with self.lock:
            if from_board and (self.mode != 'board' or not self.session_active):
                raise ValueError('Board control session not active')
            if not from_board and self.mode != 'local':
                raise ValueError('Web commands disabled in board mode')
            if action.sequence_id <= self.last_accepted_sequence:
                raise ValueError('Out-of-order sequence_id')
            if self.action is not None or self.actions.full():
                raise ValueError('Controller busy')
            self.actions.put_nowait(action)
            self.last_accepted_sequence=action.sequence_id
            self._publish_locked()

    def step(self):
        # Only called by main simulation thread.
        with self.lock:
            if self.mode=='board':
                healthy=self.session_active and (time.monotonic()-self.last_board_heartbeat < 2.0)
                if not healthy:
                    if self.session_active:
                        self.fault='HEARTBEAT_TIMEOUT'
                    self.action=None
                    self.status='WAITING_FOR_BOARD'
                    self._publish_locked()
                    return  # no physics or autonomous motion without connected board
            if self.action is None:
                try: self.action=self.actions.get_nowait()
                except queue.Empty: pass
                else:
                    self.start_q = self._joints()
                    self.action_start = float(self.data.time)
                    self.last_applied_sequence=self.action.sequence_id
                    self.fault=None
                    self.status='RUNNING'
            if self.action is not None:
                elapsed=float(self.data.time)-self.action_start
                action=self.action
                if elapsed > action.timeout:
                    self.fault='EXECUTION_TIMEOUT'
                    self.status='FAULT'
                    self.action=None
                    # hold where arm currently is; NOT a physical emergency stop
                    for i,aid in enumerate(self.aids): self.data.ctrl[aid]=self.data.qpos[self.qids[i]]
                else:
                    u=min(max(elapsed/action.duration,0.0),1.0)
                    blend=u*u*u*(10-15*u+6*u*u)
                    for i,aid in enumerate(self.aids):
                        self.data.ctrl[aid]=self.start_q[i]+blend*(action.targets[i]-self.start_q[i])
                    if elapsed>=action.duration:
                        for i,aid in enumerate(self.aids): self.data.ctrl[aid]=action.targets[i]
            self.mj.mj_step(self.model,self.data)
            if self.action is not None and self.data.time-self.action_start>=self.action.duration:
                err=max(abs(a-b) for a,b in zip(self._joints(),self.action.targets))
                if err<=0.025:
                    self.status='DONE'
                    self.action=None
            self._publish_locked()

    def capture(self):
        # Renderer and Viewer have GL contexts: call only from the simulation main thread.
        if self.renderer is None and self.camera_error is None:
            try:
                self.renderer=self.mj.Renderer(self.model, height=480, width=640)
            except Exception as exc:
                self.camera_error=f'{type(exc).__name__}: {exc}'
        if self.renderer is None:
            with self.lock:self._publish_locked()
            return
        from PIL import Image
        for label, camera in [('overhead','overhead_camera'),('wrist','wrist_camera')]:
            try:
                self.renderer.update_scene(self.data,camera=camera)
                pixels=self.renderer.render()
                output=io.BytesIO()
                Image.fromarray(pixels).save(output,format='JPEG',quality=78)
                with self.lock:self.images[label]=output.getvalue()
            except Exception as exc:
                self.camera_error=f'{type(exc).__name__}: {exc}'
                break
        with self.lock:self._publish_locked()

    def close(self):
        if self.renderer is not None:
            self.renderer.close()
            self.renderer=None
