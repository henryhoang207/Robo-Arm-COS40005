import time
from dataclasses import dataclass
from enum import Enum

import mujoco
import mujoco.viewer


JOINT_NAMES = (
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
)


class ExecutionState(Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAULT = "FAULT"


@dataclass
class ActionPacket:
    sequence_id: int
    targets: dict
    duration: float
    timeout: float


@dataclass
class StatePacket:
    sequence_id: int
    state: str
    positions: dict
    fault_code: str | None


class SimulatedSTM32:
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

            if joint_id < 0:
                raise RuntimeError(f"Missing joint: {name}")

            if actuator_id < 0:
                raise RuntimeError(f"Missing actuator: {name}")

            qpos_index = self.model.jnt_qposadr[joint_id]

            joint_min, joint_max = self.model.jnt_range[joint_id]
            ctrl_min, ctrl_max = self.model.actuator_ctrlrange[
                actuator_id
            ]

            self.joints[name] = {
                "joint_id": joint_id,
                "actuator_id": actuator_id,
                "qpos_index": qpos_index,
                "lower": max(
                    float(joint_min),
                    float(ctrl_min),
                ),
                "upper": min(
                    float(joint_max),
                    float(ctrl_max),
                ),
            }

        self.state = ExecutionState.IDLE
        self.sequence_id = 0
        self.fault_code = None

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
                self.data.qpos[
                    self.joints[name]["qpos_index"]
                ]
            )
            for name in JOINT_NAMES
        }

    def create_state_packet(self):
        return StatePacket(
            sequence_id=self.sequence_id,
            state=self.state.value,
            positions=self.get_positions(),
            fault_code=self.fault_code,
        )

    def validate_action(self, packet):
        if packet.duration <= 0:
            raise ValueError("INVALID_DURATION")

        if packet.timeout <= packet.duration:
            raise ValueError("INVALID_TIMEOUT")

        if set(packet.targets.keys()) != set(JOINT_NAMES):
            raise ValueError("INCOMPLETE_TARGET_SET")

        for name in JOINT_NAMES:
            target = float(packet.targets[name])
            info = self.joints[name]

            if target < info["lower"] or target > info["upper"]:
                raise ValueError(
                    f"JOINT_LIMIT_{name}"
                )

    @staticmethod
    def smoothstep5(u):
        return (
            10.0 * u**3
            - 15.0 * u**4
            + 6.0 * u**5
        )

    def execute(self, viewer, packet):
        self.sequence_id = packet.sequence_id
        self.fault_code = None

        try:
            self.validate_action(packet)

        except ValueError as error:
            self.state = ExecutionState.FAULT
            self.fault_code = str(error)

            return self.create_state_packet()

        self.state = ExecutionState.RUNNING

        start_positions = self.get_positions()
        start_time = self.data.time

        while viewer.is_running():
            elapsed = self.data.time - start_time

            if elapsed > packet.timeout:
                self.state = ExecutionState.FAULT
                self.fault_code = "EXECUTION_TIMEOUT"

                return self.create_state_packet()

            u = min(
                elapsed / packet.duration,
                1.0,
            )

            blend = self.smoothstep5(u)

            for name in JOINT_NAMES:
                start = start_positions[name]
                target = packet.targets[name]

                command = (
                    start
                    + blend * (target - start)
                )

                actuator_id = self.joints[name]["actuator_id"]

                self.data.ctrl[actuator_id] = command

            mujoco.mj_step(
                self.model,
                self.data,
            )

            viewer.sync()

            time.sleep(
                self.model.opt.timestep
            )

            if u >= 1.0:
                break

        return self.wait_for_target(
            viewer,
            packet,
            start_time,
        )

    def wait_for_target(
        self,
        viewer,
        packet,
        action_start_time,
    ):
        tolerance = 0.01

        while viewer.is_running():

            positions = self.get_positions()

            reached = True

            for name in JOINT_NAMES:
                error = (
                    packet.targets[name]
                    - positions[name]
                )

                if abs(error) > tolerance:
                    reached = False
                    break

            if reached:
                self.state = ExecutionState.DONE
                self.fault_code = None

                return self.create_state_packet()

            elapsed = (
                self.data.time
                - action_start_time
            )

            if elapsed > packet.timeout:
                self.state = ExecutionState.FAULT
                self.fault_code = "TARGET_NOT_REACHED"

                return self.create_state_packet()

            for name in JOINT_NAMES:
                actuator_id = self.joints[name]["actuator_id"]

                self.data.ctrl[actuator_id] = (
                    packet.targets[name]
                )

            mujoco.mj_step(
                self.model,
                self.data,
            )

            viewer.sync()

            time.sleep(
                self.model.opt.timestep
            )


def print_state_packet(packet):
    print("\nSTATE PACKET")
    print("-" * 70)

    print(
        f"sequence_id : {packet.sequence_id}"
    )

    print(
        f"state       : {packet.state}"
    )

    print(
        f"fault_code  : {packet.fault_code}"
    )

    print("\npositions:")

    for name, value in packet.positions.items():
        print(
            f"  {name:16s} {value:8.4f} rad"
        )


stm32 = SimulatedSTM32("scene.xml")


valid_action = ActionPacket(
    sequence_id=1,

    targets={
        "shoulder_pan": 0.50,
        "shoulder_lift": 0.40,
        "elbow_flex": -0.40,
        "wrist_flex": 0.25,
        "wrist_roll": 0.50,
        "gripper": 0.60,
    },

    duration=3.0,
    timeout=5.0,
)


print("=" * 70)
print("VALID ACTION PACKET TEST")
print("=" * 70)

print(valid_action)


with mujoco.viewer.launch_passive(
    stm32.model,
    stm32.data,
) as viewer:

    state_packet = stm32.execute(
        viewer,
        valid_action,
    )


print_state_packet(state_packet)


if (
    state_packet.state == "DONE"
    and state_packet.fault_code is None
):
    print("\nVALID ACTION TEST: PASS")
else:
    print("\nVALID ACTION TEST: FAIL")


print("\n" + "=" * 70)
print("INVALID ACTION PACKET TEST")
print("=" * 70)


invalid_action = ActionPacket(
    sequence_id=2,

    targets={
        "shoulder_pan": 10.0,
        "shoulder_lift": 0.0,
        "elbow_flex": 0.0,
        "wrist_flex": 0.0,
        "wrist_roll": 0.0,
        "gripper": 0.0,
    },

    duration=3.0,
    timeout=5.0,
)


state_packet = stm32.execute(
    viewer=None,
    packet=invalid_action,
)


print_state_packet(state_packet)


if (
    state_packet.state == "FAULT"
    and state_packet.fault_code
    == "JOINT_LIMIT_shoulder_pan"
):
    print("\nINVALID ACTION TEST: PASS")
else:
    print("\nINVALID ACTION TEST: FAIL")