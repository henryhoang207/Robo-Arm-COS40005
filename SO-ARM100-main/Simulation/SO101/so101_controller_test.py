import math
import time

import mujoco
import mujoco.viewer


class SO101Controller:
    JOINT_NAMES = (
        "shoulder_pan",
        "shoulder_lift",
        "elbow_flex",
        "wrist_flex",
        "wrist_roll",
        "gripper",
    )

    def __init__(self, model_path: str):
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)

        mujoco.mj_forward(self.model, self.data)

        self.joints = {}

        for name in self.JOINT_NAMES:
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

            if joint_id < 0:
                raise RuntimeError(f"Joint not found: {name}")

            if actuator_id < 0:
                raise RuntimeError(f"Actuator not found: {name}")

            qpos_index = self.model.jnt_qposadr[joint_id]

            joint_min, joint_max = self.model.jnt_range[joint_id]
            ctrl_min, ctrl_max = self.model.actuator_ctrlrange[actuator_id]

            self.joints[name] = {
                "joint_id": joint_id,
                "actuator_id": actuator_id,
                "qpos_index": qpos_index,
                "joint_min": float(joint_min),
                "joint_max": float(joint_max),
                "ctrl_min": float(ctrl_min),
                "ctrl_max": float(ctrl_max),
            }

        self.hold_current_position()

    def hold_current_position(self):
        for name in self.JOINT_NAMES:
            info = self.joints[name]

            current_position = self.data.qpos[info["qpos_index"]]

            self.data.ctrl[info["actuator_id"]] = current_position

    def get_positions(self):
        state = {}

        for name in self.JOINT_NAMES:
            info = self.joints[name]

            state[name] = float(
                self.data.qpos[info["qpos_index"]]
            )

        return state

    def validate_targets(self, targets):
        for name, target in targets.items():
            if name not in self.joints:
                raise ValueError(f"Unknown joint: {name}")

            if not math.isfinite(target):
                raise ValueError(
                    f"{name}: target must be a finite number"
                )

            info = self.joints[name]

            lower = max(
                info["joint_min"],
                info["ctrl_min"],
            )

            upper = min(
                info["joint_max"],
                info["ctrl_max"],
            )

            if target < lower or target > upper:
                raise ValueError(
                    f"{name}: target {target:.4f} rad "
                    f"is outside [{lower:.4f}, {upper:.4f}]"
                )

    def set_targets(self, targets):
        self.validate_targets(targets)

        for name, target in targets.items():
            actuator_id = self.joints[name]["actuator_id"]
            self.data.ctrl[actuator_id] = target

    def step(self):
        mujoco.mj_step(self.model, self.data)

    def print_limits(self):
        print("\nJOINT LIMITS")
        print("-" * 65)

        for name in self.JOINT_NAMES:
            info = self.joints[name]

            print(
                f"{name:16s} "
                f"[{info['joint_min']:8.4f}, "
                f"{info['joint_max']:8.4f}] rad"
            )

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

        for name, target in targets.items():
            measured = actual[name]
            error = target - measured

            if abs(error) > 0.01:
                passed = False

            print(
                f"{name:16s}"
                f"{target:12.4f}"
                f"{measured:12.4f}"
                f"{error:12.6f}"
            )

        print("-" * 75)

        if passed:
            print("6-JOINT CONTROL TEST: PASS")
        else:
            print("6-JOINT CONTROL TEST: FAIL")


controller = SO101Controller("scene.xml")

controller.print_limits()

targets = {
    "shoulder_pan": 0.30,
    "shoulder_lift": 0.35,
    "elbow_flex": -0.30,
    "wrist_flex": 0.20,
    "wrist_roll": 0.35,
    "gripper": 0.50,
}

print("\nCOMMAND TARGETS")

for name, value in targets.items():
    print(f"{name:16s} -> {value:.4f} rad")

controller.set_targets(targets)

with mujoco.viewer.launch_passive(
    controller.model,
    controller.data,
) as viewer:

    start_time = time.time()

    while viewer.is_running():
        controller.step()
        viewer.sync()

        time.sleep(controller.model.opt.timestep)

        if time.time() - start_time >= 6.0:
            break

controller.print_result(targets)


print("\nINVALID COMMAND TEST")
print("-" * 65)

try:
    controller.set_targets({
        "shoulder_pan": 10.0
    })

    print("INVALID COMMAND TEST: FAIL")

except ValueError as error:
    print("Rejected correctly:")
    print(error)
    print("INVALID COMMAND TEST: PASS")