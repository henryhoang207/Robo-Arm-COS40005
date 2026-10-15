import math
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
    REJECTED = "REJECTED"
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
    def __init__(
        self,
        model_path,
        heartbeat_timeout=0.5,
        position_tolerance=0.01,
    ):
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)

        mujoco.mj_forward(self.model, self.data)

        self.heartbeat_timeout = heartbeat_timeout
        self.position_tolerance = position_tolerance

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
        self.last_accepted_sequence_id = -1
        self.fault_code = None

        self.current_action = None
        self.action_start_time = None
        self.start_positions = None

        self.last_heartbeat_time = None

        self.hold_current_position()

    def get_positions(self):
        return {
            name: float(
                self.data.qpos[
                    self.joints[name]["qpos_index"]
                ]
            )
            for name in JOINT_NAMES
        }

    def hold_current_position(self):
        positions = self.get_positions()

        for name in JOINT_NAMES:
            actuator_id = self.joints[name]["actuator_id"]

            self.data.ctrl[actuator_id] = positions[name]

    def create_state_packet(self):
        return StatePacket(
            sequence_id=self.sequence_id,
            state=self.state.value,
            positions=self.get_positions(),
            fault_code=self.fault_code,
        )

    def receive_heartbeat(self):
        self.last_heartbeat_time = self.data.time

    def validate_action(self, packet):
        if not isinstance(packet.sequence_id, int):
            raise ValueError("INVALID_SEQUENCE_ID")

        if packet.sequence_id <= self.last_accepted_sequence_id:
            raise ValueError("STALE_OR_REPLAYED_SEQUENCE")

        if not math.isfinite(packet.duration):
            raise ValueError("INVALID_DURATION")

        if packet.duration <= 0:
            raise ValueError("INVALID_DURATION")

        if not math.isfinite(packet.timeout):
            raise ValueError("INVALID_TIMEOUT")

        if packet.timeout <= packet.duration:
            raise ValueError("INVALID_TIMEOUT")

        if not isinstance(packet.targets, dict):
            raise ValueError("MALFORMED_TARGET_SET")

        if set(packet.targets.keys()) != set(JOINT_NAMES):
            raise ValueError("INCOMPLETE_TARGET_SET")

        for name in JOINT_NAMES:
            target = packet.targets[name]

            if not isinstance(target, (int, float)):
                raise ValueError(
                    f"INVALID_TARGET_{name}"
                )

            target = float(target)

            if not math.isfinite(target):
                raise ValueError(
                    f"INVALID_TARGET_{name}"
                )

            info = self.joints[name]

            if (
                target < info["lower"]
                or target > info["upper"]
            ):
                raise ValueError(
                    f"JOINT_LIMIT_{name}"
                )

    def submit_action(self, packet):
        if self.state == ExecutionState.RUNNING:
            self.state = ExecutionState.REJECTED
            self.fault_code = "CONTROLLER_BUSY"

            return self.create_state_packet()

        self.sequence_id = packet.sequence_id
        self.fault_code = None

        try:
            self.validate_action(packet)

        except ValueError as error:
            self.state = ExecutionState.REJECTED
            self.fault_code = str(error)

            return self.create_state_packet()

        self.last_accepted_sequence_id = packet.sequence_id

        self.current_action = packet
        self.start_positions = self.get_positions()
        self.action_start_time = self.data.time

        self.state = ExecutionState.RUNNING
        self.fault_code = None

        return self.create_state_packet()

    @staticmethod
    def smoothstep5(u):
        return (
            10.0 * u**3
            - 15.0 * u**4
            + 6.0 * u**5
        )

    def enter_fault(self, fault_code):
        self.state = ExecutionState.FAULT
        self.fault_code = fault_code

        self.current_action = None

        self.hold_current_position()

    def check_watchdog(self):
        if self.last_heartbeat_time is None:
            return

        heartbeat_age = (
            self.data.time
            - self.last_heartbeat_time
        )

        if heartbeat_age > self.heartbeat_timeout:
            self.enter_fault("WATCHDOG_TIMEOUT")

    def target_reached(self):
        if self.current_action is None:
            return False

        positions = self.get_positions()

        for name in JOINT_NAMES:
            error = (
                self.current_action.targets[name]
                - positions[name]
            )

            if abs(error) > self.position_tolerance:
                return False

        return True

    def update_motion_command(self):
        if self.state != ExecutionState.RUNNING:
            return

        packet = self.current_action

        elapsed = (
            self.data.time
            - self.action_start_time
        )

        if elapsed > packet.timeout:
            self.enter_fault("EXECUTION_TIMEOUT")
            return

        u = min(
            elapsed / packet.duration,
            1.0,
        )

        blend = self.smoothstep5(u)

        for name in JOINT_NAMES:
            start = self.start_positions[name]
            target = packet.targets[name]

            command = (
                start
                + blend * (target - start)
            )

            actuator_id = self.joints[name]["actuator_id"]

            self.data.ctrl[actuator_id] = command

        if u >= 1.0:
            for name in JOINT_NAMES:
                actuator_id = self.joints[name]["actuator_id"]

                self.data.ctrl[actuator_id] = (
                    packet.targets[name]
                )

    def tick(self):
        self.check_watchdog()

        if self.state == ExecutionState.FAULT:
            mujoco.mj_step(
                self.model,
                self.data,
            )
            return

        self.update_motion_command()

        mujoco.mj_step(
            self.model,
            self.data,
        )

        if (
            self.state == ExecutionState.RUNNING
            and self.data.time - self.action_start_time
            >= self.current_action.duration
            and self.target_reached()
        ):
            self.state = ExecutionState.DONE
            self.fault_code = None

            self.current_action = None


def print_state(title, packet):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

    print(f"sequence_id : {packet.sequence_id}")
    print(f"state       : {packet.state}")
    print(f"fault_code  : {packet.fault_code}")


stm32 = SimulatedSTM32(
    "scene.xml",
    heartbeat_timeout=0.5,
)


# ------------------------------------------------------------
# TEST 1
# Fresh valid action
# ------------------------------------------------------------

valid_action = ActionPacket(
    sequence_id=3,

    targets={
        "shoulder_pan": 0.40,
        "shoulder_lift": 0.35,
        "elbow_flex": -0.35,
        "wrist_flex": 0.20,
        "wrist_roll": 0.40,
        "gripper": 0.55,
    },

    duration=2.0,
    timeout=3.0,
)


stm32.receive_heartbeat()

accepted_packet = stm32.submit_action(
    valid_action
)

print_state(
    "TEST 1 - FRESH COMMAND ACCEPTED",
    accepted_packet,
)


with mujoco.viewer.launch_passive(
    stm32.model,
    stm32.data,
) as viewer:

    next_heartbeat = stm32.data.time

    while (
        viewer.is_running()
        and stm32.state == ExecutionState.RUNNING
    ):
        if stm32.data.time >= next_heartbeat:
            stm32.receive_heartbeat()

            next_heartbeat += 0.1

        stm32.tick()

        viewer.sync()

        time.sleep(
            stm32.model.opt.timestep
        )


result = stm32.create_state_packet()

print_state(
    "TEST 1 - FINAL STATE",
    result,
)


if (
    result.state == "DONE"
    and result.fault_code is None
):
    print("TEST 1: PASS")
else:
    print("TEST 1: FAIL")


# ------------------------------------------------------------
# TEST 2
# Replay the same sequence ID
# ------------------------------------------------------------

positions_before = stm32.get_positions()

replay_result = stm32.submit_action(
    valid_action
)

positions_after = stm32.get_positions()

print_state(
    "TEST 2 - REPLAYED COMMAND",
    replay_result,
)


motion_changed = any(
    abs(
        positions_before[name]
        - positions_after[name]
    ) > 1e-9
    for name in JOINT_NAMES
)


if (
    replay_result.state == "REJECTED"
    and replay_result.fault_code
    == "STALE_OR_REPLAYED_SEQUENCE"
    and not motion_changed
):
    print("TEST 2: PASS")
else:
    print("TEST 2: FAIL")


# ------------------------------------------------------------
# TEST 3
# Malformed packet: gripper is missing
# ------------------------------------------------------------

malformed_action = ActionPacket(
    sequence_id=4,

    targets={
        "shoulder_pan": 0.0,
        "shoulder_lift": 0.0,
        "elbow_flex": 0.0,
        "wrist_flex": 0.0,
        "wrist_roll": 0.0,
    },

    duration=1.0,
    timeout=2.0,
)


malformed_result = stm32.submit_action(
    malformed_action
)


print_state(
    "TEST 3 - MALFORMED COMMAND",
    malformed_result,
)


if (
    malformed_result.state == "REJECTED"
    and malformed_result.fault_code
    == "INCOMPLETE_TARGET_SET"
):
    print("TEST 3: PASS")
else:
    print("TEST 3: FAIL")


# ------------------------------------------------------------
# TEST 4
# Heartbeat disappears
# ------------------------------------------------------------

stm32.receive_heartbeat()

watchdog_start = stm32.data.time


while (
    stm32.data.time - watchdog_start
    < 1.0
):
    stm32.tick()

    if stm32.state == ExecutionState.FAULT:
        break


watchdog_result = stm32.create_state_packet()


print_state(
    "TEST 4 - WATCHDOG",
    watchdog_result,
)


if (
    watchdog_result.state == "FAULT"
    and watchdog_result.fault_code
    == "WATCHDOG_TIMEOUT"
):
    print("TEST 4: PASS")
else:
    print("TEST 4: FAIL")