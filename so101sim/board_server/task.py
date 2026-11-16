"""Episode evaluation from simulator ground truth, separate from AI observations."""
from __future__ import annotations
import numpy as np

BALLS = ('red_ball', 'green_ball', 'blue_ball', 'yellow_ball')


class TaskEvaluator:
    def __init__(self, mj, model, settings):
        self.mj, self.model, self.settings = mj, model, settings
        self.bodies = {name: mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, name) for name in BALLS}
        self.box = mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, 'drop_box')
        self.jaws = {mj.mj_name2id(model, mj.mjtObj.mjOBJ_BODY, name)
                     for name in ('gripper', 'moving_jaw_so101_v1')}
        self.radii = {name: float(model.geom_size[mj.mj_name2id(model, mj.mjtObj.mjOBJ_GEOM, name + '_geom'), 0])
                      for name in BALLS}
        self.reset('red_ball', 0)

    def reset(self, target, seed):
        self.target, self.seed = target, seed
        self.status, self.reason = 'READY', None
        self.started_at = None
        self.elapsed = 0.0
        self.grasped = self.lifted = False
        self.max_height = 0.0
        self.stable_since = None
        self.contacts = set()
        self.in_box = False
        self.object_speed = 0.0

    def start(self, sim_time):
        if self.status == 'READY':
            self.status, self.started_at = 'RUNNING', sim_time

    def finish(self, status, reason):
        if self.status in ('READY', 'RUNNING'):
            self.status, self.reason = status, reason
            return True
        return False

    def jaw_contacts(self, data, target=None):
        body = self.bodies[target or self.target]
        touched = set()
        for contact in data.contact:
            a, b = (int(self.model.geom_bodyid[g]) for g in (contact.geom1, contact.geom2))
            if a == body and b in self.jaws:
                touched.add(b)
            if b == body and a in self.jaws:
                touched.add(a)
        return touched

    def update(self, data):
        if self.status != 'RUNNING':
            return False
        self.elapsed = float(data.time) - self.started_at
        body = self.bodies[self.target]
        pos = data.xpos[body]
        radius = self.radii[self.target]
        velocity = np.zeros(6)
        self.mj.mj_objectVelocity(self.model, data, self.mj.mjtObj.mjOBJ_BODY, body, velocity, 0)
        self.object_speed = float(np.linalg.norm(velocity[3:]))
        self.contacts = self.jaw_contacts(data)
        self.grasped |= len(self.contacts) == 2
        self.lifted |= bool(self.grasped and pos[2] > 0.05 and len(self.contacts) == 2)
        self.max_height = max(self.max_height, float(pos[2]))
        relative = pos - data.xpos[self.box]
        # Internal width is 0.10 m, floor top is 0.012 m. Allow 2 mm soft-contact margin.
        self.in_box = bool(np.all(np.abs(relative[:2]) <= .05 - radius + .002)
                           and .012 + radius - .003 <= relative[2] <= .012 + radius + .006)
        valid = self.grasped and self.lifted and self.in_box and not self.contacts and self.object_speed < .03
        if valid:
            if self.stable_since is None:
                self.stable_since = float(data.time)
            if data.time - self.stable_since >= self.settings['success_dwell_s']:
                return self.finish('SUCCESS', 'Lifted, released and stable inside the box')
        else:
            self.stable_since = None
        if pos[2] < -.03:
            return self.finish('FAILURE', 'OBJECT_FELL_OFF_TABLE')
        if self.elapsed >= self.settings['episode_timeout_s']:
            return self.finish('FAILURE', 'EPISODE_TIMEOUT')
        return False

    def summary(self):
        return {'status': self.status, 'reason': self.reason, 'target': self.target,
                'seed': self.seed, 'elapsed_sim_s': round(self.elapsed, 4),
                'grasped': self.grasped, 'lifted': self.lifted,
                'max_object_height_m': self.max_height, 'in_box': self.in_box}

    def ground_truth(self, data):
        return {'purpose': 'evaluation/reference controller only; not a vision-policy observation',
                'objects': {name: data.xpos[body].tolist() for name, body in self.bodies.items()},
                'box_position': data.xpos[self.box].tolist(),
                'target_jaw_contact_count': len(self.jaw_contacts(data)),
                'target_speed_m_s': self.object_speed, 'episode': self.summary()}
