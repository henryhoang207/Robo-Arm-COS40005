"""Stream LeRobot joint targets through the local MuJoCo position servos."""

import math

import numpy as np


FPS = 30
TARGET_SMOOTHING_SECONDS = 0.05
MAX_TARGET_SPEED_RAD_S = np.r_[np.full(5, 2.0), 12.0]


class JointTargets:
    def __init__(self, sim, zero_rad, rad_per_unit):
        self.sim = sim
        self.zero_rad = zero_rad
        self.rad_per_unit = rad_per_unit
        self.limits = np.asarray(sim.limits)
        timestep = sim.model.opt.timestep
        self.blend = -math.expm1(-timestep / TARGET_SMOOTHING_SECONDS)
        self.max_delta = MAX_TARGET_SPEED_RAD_S * timestep
        self.start_time = float(sim.data.time)
        self.executed = 0

    def prepare(self, actions):
        gripper = np.clip(actions[:, -1], 0, 100)
        bounded = np.column_stack((actions[:, :-1], gripper))
        raw_targets = self.zero_rad + self.rad_per_unit * bounded
        targets = np.clip(raw_targets, self.limits[:, 0], self.limits[:, 1])
        limited = (gripper != actions[:, -1]) | np.any(raw_targets != targets, axis=1)
        return targets, limited

    def apply(self, target):
        sim = self.sim
        self.executed += 1
        deadline = self.start_time + self.executed / FPS
        while sim.data.time + 1e-9 < deadline:
            # Smooth continuously across both recorded frames and policy chunks.
            current = sim.data.ctrl[sim.aids]
            delta = np.clip(self.blend * (target - current), -self.max_delta, self.max_delta)
            sim.data.ctrl[sim.aids] = current + delta
            sim.step()
