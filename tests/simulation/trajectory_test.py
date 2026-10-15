import time

import mujoco
import mujoco.viewer
import numpy as np
from pathlib import Path

JOINT_NAMES = (
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
)


class SO101TrajectoryController:
    def __init__(self, model_path):
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)

        mujoco.mj_forward(self.model, self.data)

        self.joints = {}

        for name in JOINT_NAMES:
            joint_id = mujoco.mj_name2id(
                self.model,
                mujoco.mjtObj.mjOBJ_JOINT,
                name,
            )

            actuator_id = mujoco.mj_name2id(
                self.model,
                mujoco.mjtObj.mjOBJ_ACTUATOR,
                name,
            )

            qpos_index = self.model.jnt_qposadr[joint_id]

            joint_min, joint_max = self.model.jnt_range[joint_id]
            ctrl_min, ctrl_max = self.model.actuator_ctrlrange[actuator_id]

            self.joints[name] = {
                "joint_id": joint_id,
                "actuator_id": actuator_id,
                "qpos_index": qpos_index,
                "lower": max(float(joint_min), float(ctrl_min)),
                "upper": min(float(joint_max), float(ctrl_max)),
            }

        self.hold_current_position()

    def hold_current_position(self):
        for name in JOINT_NAMES:
            info = self.joints[name]

            self.data.ctrl[info["actuator_id"]] = (
                self.data.qpos[info["qpos_index"]]
            )

    def get_positions(self):
        return {
            name: float(
                self.data.qpos[self.joints[name]["qpos_index"]]
            )
            for name in JOINT_NAMES
        }

    def validate_targets(self, targets):
        for name in JOINT_NAMES:
            if name not in targets:
                raise ValueError(f"Missing target for {name}")

            target = float(targets[name])
            info = self.joints[name]

            if target < info["lower"] or target > info["upper"]:
                raise ValueError(
                    f"{name}: {target:.4f} rad outside "
                    f"[{info['lower']:.4f}, {info['upper']:.4f}]"
                )

    @staticmethod
    def smoothstep5(u):
        """
        Quintic interpolation:
        velocity = 0 at start/end
        acceleration = 0 at start/end
        """
        return (
            10.0 * u**3
            - 15.0 * u**4
            + 6.0 * u**5
        )

    def run_trajectory(self, viewer, targets, duration):
        self.validate_targets(targets)

        start_positions = self.get_positions()

        print("\nSTART POSITIONS")
        print("-" * 65)

        for name in JOINT_NAMES:
            print(
                f"{name:16s} "
                f"{start_positions[name]:8.4f} rad"
            )

        print("\nTARGET POSITIONS")
        print("-" * 65)

        for name in JOINT_NAMES:
            print(
                f"{name:16s} "
                f"{targets[name]:8.4f} rad"
            )

        start_time = self.data.time

        while viewer.is_running():
            elapsed = self.data.time - start_time
            u = min(elapsed / duration, 1.0)

            blend = self.smoothstep5(u)

            for name in JOINT_NAMES:
                start = start_positions[name]
                target = targets[name]

                command = start + blend * (target - start)

                actuator_id = self.joints[name]["actuator_id"]
                self.data.ctrl[actuator_id] = command

            mujoco.mj_step(self.model, self.data)
            viewer.sync()

            time.sleep(self.model.opt.timestep)

            if u >= 1.0:
                break

        # Hold final target briefly so the simulated actuators can settle.
        settle_start = self.data.time

        while (
            viewer.is_running()
            and self.data.time - settle_start < 1.0
        ):
            for name in JOINT_NAMES:
                actuator_id = self.joints[name]["actuator_id"]
                self.data.ctrl[actuator_id] = targets[name]

            mujoco.mj_step(self.model, self.data)
            viewer.sync()

            time.sleep(self.model.opt.timestep)

    def print_result(self, targets):
        actual = self.get_positions()

        print("\nFINAL RESULT")
        print("-" * 75)
        print(
            f"{'Joint':16s}"
            f"{'Target':>12s}"
            f"{'Actual':>12s}"
            f"{'Error':>12s}"
        )
        print("-" * 75)

        passed = True
        tolerance = 0.01

        for name in JOINT_NAMES:
            target = targets[name]
            measured = actual[name]
            error = target - measured

            if abs(error) > tolerance:
                passed = False

            print(
                f"{name:16s}"
                f"{target:12.4f}"
                f"{measured:12.4f}"
                f"{error:12.6f}"
            )

        print("-" * 75)

        if passed:
            print("SYNCHRONIZED TRAJECTORY TEST: PASS")
        else:
            print("SYNCHRONIZED TRAJECTORY TEST: FAIL")


MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "SO-ARM100-main"
    / "Simulation"
    / "SO101"
    / "scene.xml"
)

controller = SO101TrajectoryController(str(MODEL_PATH))

targets = {
    "shoulder_pan": 0.60,
    "shoulder_lift": 0.50,
    "elbow_flex": -0.45,
    "wrist_flex": 0.30,
    "wrist_roll": 0.60,
    "gripper": 0.70,
}

motion_duration = 4.0

print("=" * 65)
print("SO-101 SYNCHRONIZED TRAJECTORY TEST")
print("=" * 65)

print(f"\nMotion duration: {motion_duration:.1f} seconds")

with mujoco.viewer.launch_passive(
    controller.model,
    controller.data,
) as viewer:

    controller.run_trajectory(
        viewer,
        targets,
        motion_duration,
    )

controller.print_result(targets)