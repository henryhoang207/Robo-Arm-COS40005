import math
import struct
import time
import zlib
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import mujoco
import mujoco.viewer


# ============================================================
# Protocol definition
# ============================================================

MAGIC = 0xA55A
VERSION = 1

JOINT_NAMES = (
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
)


class MessageType(IntEnum):
    ACTION = 1
    STATE = 2
    HEARTBEAT = 3


class ExecutionState(IntEnum):
    IDLE = 0
    RUNNING = 1
    DONE = 2
    REJECTED = 3
    FAULT = 4


class FaultCode(IntEnum):
    NONE = 0
    INVALID_PACKET = 1
    STALE_OR_REPLAYED_SEQUENCE = 2
    JOINT_LIMIT = 3
    WATCHDOG_TIMEOUT = 4
    EXECUTION_TIMEOUT = 5
    CONTROLLER_BUSY = 6
    INVALID_ACTION = 7


@dataclass
class ActionPacket:
    sequence_id: int
    targets: dict
    duration: float
    timeout: float


@dataclass
class StatePacket:
    sequence_id: int
    state: ExecutionState
    fault_code: FaultCode
    fault_detail: int
    positions: dict


HEADER_FORMAT = "<HBBIH"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

ACTION_PAYLOAD_FORMAT = "<8f"
ACTION_PAYLOAD_SIZE = struct.calcsize(
    ACTION_PAYLOAD_FORMAT
)

STATE_PAYLOAD_FORMAT = "<HHHH6f"
STATE_PAYLOAD_SIZE = struct.calcsize(
    STATE_PAYLOAD_FORMAT
)

CRC_FORMAT = "<I"
CRC_SIZE = struct.calcsize(CRC_FORMAT)


# ============================================================
# Binary protocol
# ============================================================

def calculate_crc(data):
    return zlib.crc32(data) & 0xFFFFFFFF


def encode_frame(
    message_type,
    sequence_id,
    payload,
):
    header = struct.pack(
        HEADER_FORMAT,
        MAGIC,
        VERSION,
        int(message_type),
        sequence_id,
        len(payload),
    )

    body = header + payload
    crc = calculate_crc(body)

    return (
        body
        + struct.pack(
            CRC_FORMAT,
            crc,
        )
    )


def decode_frame(frame):
    if len(frame) < HEADER_SIZE + CRC_SIZE:
        raise ValueError("FRAME_TOO_SHORT")

    (
        magic,
        version,
        raw_message_type,
        sequence_id,
        payload_length,
    ) = struct.unpack(
        HEADER_FORMAT,
        frame[:HEADER_SIZE],
    )

    if magic != MAGIC:
        raise ValueError("INVALID_MAGIC")

    if version != VERSION:
        raise ValueError("UNSUPPORTED_VERSION")

    expected_length = (
        HEADER_SIZE
        + payload_length
        + CRC_SIZE
    )

    if len(frame) != expected_length:
        raise ValueError("INVALID_FRAME_LENGTH")

    payload_end = (
        HEADER_SIZE + payload_length
    )

    payload = frame[
        HEADER_SIZE:payload_end
    ]

    received_crc = struct.unpack(
        CRC_FORMAT,
        frame[payload_end:],
    )[0]

    calculated_crc = calculate_crc(
        frame[:payload_end]
    )

    if received_crc != calculated_crc:
        raise ValueError("CRC_MISMATCH")

    try:
        message_type = MessageType(
            raw_message_type
        )
    except ValueError:
        raise ValueError(
            "UNKNOWN_MESSAGE_TYPE"
        )

    return (
        message_type,
        sequence_id,
        payload,
    )


def encode_action_packet(packet):
    values = [
        float(packet.targets[name])
        for name in JOINT_NAMES
    ]

    values.extend([
        float(packet.duration),
        float(packet.timeout),
    ])

    payload = struct.pack(
        ACTION_PAYLOAD_FORMAT,
        *values,
    )

    return encode_frame(
        MessageType.ACTION,
        packet.sequence_id,
        payload,
    )


def decode_action_payload(
    sequence_id,
    payload,
):
    if len(payload) != ACTION_PAYLOAD_SIZE:
        raise ValueError(
            "INVALID_ACTION_PAYLOAD_LENGTH"
        )

    values = struct.unpack(
        ACTION_PAYLOAD_FORMAT,
        payload,
    )

    targets = {
        name: float(values[index])
        for index, name
        in enumerate(JOINT_NAMES)
    }

    return ActionPacket(
        sequence_id=sequence_id,
        targets=targets,
        duration=float(values[6]),
        timeout=float(values[7]),
    )


def encode_state_packet(packet):
    positions = [
        float(packet.positions[name])
        for name in JOINT_NAMES
    ]

    payload = struct.pack(
        STATE_PAYLOAD_FORMAT,
        int(packet.state),
        int(packet.fault_code),
        int(packet.fault_detail),
        0,
        *positions,
    )

    return encode_frame(
        MessageType.STATE,
        packet.sequence_id,
        payload,
    )


def decode_state_packet(frame):
    (
        message_type,
        sequence_id,
        payload,
    ) = decode_frame(frame)

    if message_type != MessageType.STATE:
        raise ValueError(
            "EXPECTED_STATE_PACKET"
        )

    if len(payload) != STATE_PAYLOAD_SIZE:
        raise ValueError(
            "INVALID_STATE_PAYLOAD_LENGTH"
        )

    values = struct.unpack(
        STATE_PAYLOAD_FORMAT,
        payload,
    )

    positions = {
        name: float(values[index + 4])
        for index, name
        in enumerate(JOINT_NAMES)
    }

    return StatePacket(
        sequence_id=sequence_id,
        state=ExecutionState(values[0]),
        fault_code=FaultCode(values[1]),
        fault_detail=values[2],
        positions=positions,
    )


def encode_heartbeat(sequence_id):
    return encode_frame(
        MessageType.HEARTBEAT,
        sequence_id,
        b"",
    )


# ============================================================
# Simulated STM32
# ============================================================

class SimulatedSTM32:
    def __init__(
        self,
        model_path,
        heartbeat_timeout=0.5,
        position_tolerance=0.01,
    ):
        self.model = mujoco.MjModel.from_xml_path(
            model_path
        )

        self.data = mujoco.MjData(
            self.model
        )

        mujoco.mj_forward(
            self.model,
            self.data,
        )

        self.heartbeat_timeout = (
            heartbeat_timeout
        )

        self.position_tolerance = (
            position_tolerance
        )

        self.joints = {}

        for index, name in enumerate(
            JOINT_NAMES
        ):
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

            qpos_index = (
                self.model.jnt_qposadr[
                    joint_id
                ]
            )

            joint_min, joint_max = (
                self.model.jnt_range[
                    joint_id
                ]
            )

            ctrl_min, ctrl_max = (
                self.model.actuator_ctrlrange[
                    actuator_id
                ]
            )

            self.joints[name] = {
                "index": index,
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

        self.active_sequence_id = 0
        self.last_accepted_sequence_id = -1

        self.fault_code = FaultCode.NONE
        self.fault_detail = 0

        self.current_action = None
        self.start_positions = None
        self.action_start_time = None

        self.last_heartbeat_time = None

        self.last_transport_error = None

        self.hold_current_position()

    def get_positions(self):
        return {
            name: float(
                self.data.qpos[
                    self.joints[name][
                        "qpos_index"
                    ]
                ]
            )
            for name in JOINT_NAMES
        }

    def hold_current_position(self):
        positions = self.get_positions()

        for name in JOINT_NAMES:
            actuator_id = (
                self.joints[name][
                    "actuator_id"
                ]
            )

            self.data.ctrl[
                actuator_id
            ] = positions[name]

    def build_state_packet(
        self,
        sequence_id=None,
    ):
        if sequence_id is None:
            sequence_id = (
                self.active_sequence_id
            )

        return StatePacket(
            sequence_id=sequence_id,
            state=self.state,
            fault_code=self.fault_code,
            fault_detail=self.fault_detail,
            positions=self.get_positions(),
        )

    def validate_action(self, packet):
        if (
            packet.sequence_id
            <= self.last_accepted_sequence_id
        ):
            return (
                FaultCode.STALE_OR_REPLAYED_SEQUENCE,
                0,
            )

        if (
            not math.isfinite(
                packet.duration
            )
            or packet.duration <= 0
        ):
            return (
                FaultCode.INVALID_ACTION,
                1,
            )

        if (
            not math.isfinite(
                packet.timeout
            )
            or packet.timeout
            <= packet.duration
        ):
            return (
                FaultCode.INVALID_ACTION,
                2,
            )

        for name in JOINT_NAMES:
            target = packet.targets[name]
            info = self.joints[name]

            if not math.isfinite(target):
                return (
                    FaultCode.INVALID_ACTION,
                    info["index"],
                )

            if (
                target < info["lower"]
                or target > info["upper"]
            ):
                return (
                    FaultCode.JOINT_LIMIT,
                    info["index"],
                )

        return (
            FaultCode.NONE,
            0,
        )

    def submit_action(self, packet):
        if self.state == ExecutionState.RUNNING:
            self.state = (
                ExecutionState.REJECTED
            )

            self.fault_code = (
                FaultCode.CONTROLLER_BUSY
            )

            self.fault_detail = 0

            return self.build_state_packet(
                packet.sequence_id
            )

        (
            error,
            detail,
        ) = self.validate_action(packet)

        if error != FaultCode.NONE:
            self.state = (
                ExecutionState.REJECTED
            )

            self.fault_code = error
            self.fault_detail = detail

            return self.build_state_packet(
                packet.sequence_id
            )

        self.active_sequence_id = (
            packet.sequence_id
        )

        self.last_accepted_sequence_id = (
            packet.sequence_id
        )

        self.current_action = packet

        self.start_positions = (
            self.get_positions()
        )

        self.action_start_time = (
            self.data.time
        )

        self.state = ExecutionState.RUNNING
        self.fault_code = FaultCode.NONE
        self.fault_detail = 0

        return self.build_state_packet()

    def receive_binary_frame(self, frame):
        try:
            (
                message_type,
                sequence_id,
                payload,
            ) = decode_frame(frame)

        except ValueError as error:
            self.last_transport_error = str(
                error
            )

            packet = StatePacket(
                sequence_id=0,
                state=ExecutionState.REJECTED,
                fault_code=(
                    FaultCode.INVALID_PACKET
                ),
                fault_detail=0,
                positions=self.get_positions(),
            )

            return encode_state_packet(
                packet
            )

        self.last_transport_error = None

        if (
            message_type
            == MessageType.HEARTBEAT
        ):
            if len(payload) != 0:
                packet = StatePacket(
                    sequence_id=sequence_id,
                    state=(
                        ExecutionState.REJECTED
                    ),
                    fault_code=(
                        FaultCode.INVALID_PACKET
                    ),
                    fault_detail=0,
                    positions=self.get_positions(),
                )

                return encode_state_packet(
                    packet
                )

            self.last_heartbeat_time = (
                self.data.time
            )

            return None

        if (
            message_type
            == MessageType.ACTION
        ):
            try:
                action = decode_action_payload(
                    sequence_id,
                    payload,
                )

            except ValueError:
                packet = StatePacket(
                    sequence_id=sequence_id,
                    state=(
                        ExecutionState.REJECTED
                    ),
                    fault_code=(
                        FaultCode.INVALID_PACKET
                    ),
                    fault_detail=0,
                    positions=self.get_positions(),
                )

                return encode_state_packet(
                    packet
                )

            state_packet = (
                self.submit_action(action)
            )

            return encode_state_packet(
                state_packet
            )

        packet = StatePacket(
            sequence_id=sequence_id,
            state=ExecutionState.REJECTED,
            fault_code=(
                FaultCode.INVALID_PACKET
            ),
            fault_detail=0,
            positions=self.get_positions(),
        )

        return encode_state_packet(packet)

    @staticmethod
    def smoothstep5(u):
        return (
            10.0 * u**3
            - 15.0 * u**4
            + 6.0 * u**5
        )

    def enter_fault(
        self,
        fault_code,
        detail=0,
    ):
        self.state = ExecutionState.FAULT
        self.fault_code = fault_code
        self.fault_detail = detail

        self.current_action = None

        self.hold_current_position()

    def check_watchdog(self):
        if self.last_heartbeat_time is None:
            return

        heartbeat_age = (
            self.data.time
            - self.last_heartbeat_time
        )

        if (
            heartbeat_age
            > self.heartbeat_timeout
        ):
            self.enter_fault(
                FaultCode.WATCHDOG_TIMEOUT
            )

    def target_reached(self):
        if self.current_action is None:
            return False

        positions = self.get_positions()

        for name in JOINT_NAMES:
            error = (
                self.current_action.targets[
                    name
                ]
                - positions[name]
            )

            if (
                abs(error)
                > self.position_tolerance
            ):
                return False

        return True

    def update_motion(self):
        if (
            self.state
            != ExecutionState.RUNNING
        ):
            return

        packet = self.current_action

        elapsed = (
            self.data.time
            - self.action_start_time
        )

        if elapsed > packet.timeout:
            self.enter_fault(
                FaultCode.EXECUTION_TIMEOUT
            )
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
                + blend * (
                    target - start
                )
            )

            actuator_id = (
                self.joints[name][
                    "actuator_id"
                ]
            )

            self.data.ctrl[
                actuator_id
            ] = command

        if u >= 1.0:
            for name in JOINT_NAMES:
                actuator_id = (
                    self.joints[name][
                        "actuator_id"
                    ]
                )

                self.data.ctrl[
                    actuator_id
                ] = packet.targets[name]

    def tick(self):
        self.check_watchdog()

        if self.state == ExecutionState.FAULT:
            mujoco.mj_step(
                self.model,
                self.data,
            )
            return

        self.update_motion()

        mujoco.mj_step(
            self.model,
            self.data,
        )

        if (
            self.state
            == ExecutionState.RUNNING
            and self.current_action
            is not None
        ):
            elapsed = (
                self.data.time
                - self.action_start_time
            )

            if (
                elapsed
                >= self.current_action.duration
                and self.target_reached()
            ):
                self.state = (
                    ExecutionState.DONE
                )

                self.fault_code = (
                    FaultCode.NONE
                )

                self.fault_detail = 0

                self.current_action = None


# ============================================================
# Mock IQ8
# ============================================================

class MockIQ8:
    def __init__(self):
        self.heartbeat_sequence = 1

    def make_action_frame(
        self,
        packet,
    ):
        return encode_action_packet(packet)

    def make_heartbeat_frame(self):
        frame = encode_heartbeat(
            self.heartbeat_sequence
        )

        self.heartbeat_sequence += 1

        return frame

    def read_state_frame(
        self,
        frame,
    ):
        return decode_state_packet(frame)


def print_state(
    title,
    packet,
):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)

    print(
        f"sequence_id : "
        f"{packet.sequence_id}"
    )

    print(
        f"state       : "
        f"{packet.state.name}"
    )

    print(
        f"fault_code  : "
        f"{packet.fault_code.name}"
    )

    print(
        f"fault_detail: "
        f"{packet.fault_detail}"
    )


# ============================================================
# Instantiate both sides
# ============================================================

iq8 = MockIQ8()

MODEL_PATH = (
    Path(__file__).resolve().parent / "scene.xml"
)

stm32 = SimulatedSTM32(
    str(MODEL_PATH),
    heartbeat_timeout=0.5,
)

# ============================================================
# TEST 1
# Full valid end-to-end command
# ============================================================

print("=" * 72)
print("TEST 1 - VALID END-TO-END COMMAND")
print("=" * 72)


action = ActionPacket(
    sequence_id=200,

    targets={
        "shoulder_pan": 0.55,
        "shoulder_lift": 0.45,
        "elbow_flex": -0.40,
        "wrist_flex": 0.30,
        "wrist_roll": 0.50,
        "gripper": 0.65,
    },

    duration=2.5,
    timeout=4.0,
)


# IQ8: Python object -> binary frame
action_frame = iq8.make_action_frame(
    action
)

print(
    f"IQ8 transmitted "
    f"{len(action_frame)} bytes"
)


# Heartbeat before requesting motion
heartbeat_frame = (
    iq8.make_heartbeat_frame()
)

stm32.receive_binary_frame(
    heartbeat_frame
)


# STM32 receives and decodes ActionPacket
response_frame = (
    stm32.receive_binary_frame(
        action_frame
    )
)


initial_state = (
    iq8.read_state_frame(
        response_frame
    )
)


print_state(
    "STM32 INITIAL RESPONSE",
    initial_state,
)


with mujoco.viewer.launch_passive(
    stm32.model,
    stm32.data,
) as viewer:

    next_heartbeat = (
        stm32.data.time
    )

    while (
        viewer.is_running()
        and stm32.state
        == ExecutionState.RUNNING
    ):
        if (
            stm32.data.time
            >= next_heartbeat
        ):
            heartbeat_frame = (
                iq8.make_heartbeat_frame()
            )

            stm32.receive_binary_frame(
                heartbeat_frame
            )

            next_heartbeat += 0.1

        stm32.tick()

        viewer.sync()

        time.sleep(
            stm32.model.opt.timestep
        )


# STM32: physical result -> StatePacket -> binary
final_state_frame = (
    encode_state_packet(
        stm32.build_state_packet()
    )
)


print(
    f"\nSTM32 transmitted "
    f"{len(final_state_frame)} bytes"
)


# IQ8 decodes the response
final_state = (
    iq8.read_state_frame(
        final_state_frame
    )
)


print_state(
    "IQ8 FINAL DECODED STATE",
    final_state,
)


max_error = max(
    abs(
        action.targets[name]
        - final_state.positions[name]
    )
    for name in JOINT_NAMES
)


print(
    f"\nMaximum joint error: "
    f"{max_error:.6f} rad"
)


if (
    final_state.state
    == ExecutionState.DONE
    and final_state.fault_code
    == FaultCode.NONE
    and max_error < 0.01
):
    print(
        "TEST 1: PASS"
    )
else:
    print(
        "TEST 1: FAIL"
    )


# ============================================================
# TEST 2
# Replay exactly the same binary command
# ============================================================

print("\n" + "=" * 72)
print("TEST 2 - REPLAYED BINARY COMMAND")
print("=" * 72)


replay_response_frame = (
    stm32.receive_binary_frame(
        action_frame
    )
)


replay_state = (
    iq8.read_state_frame(
        replay_response_frame
    )
)


print_state(
    "IQ8 REPLAY RESPONSE",
    replay_state,
)


if (
    replay_state.state
    == ExecutionState.REJECTED
    and replay_state.fault_code
    == FaultCode.STALE_OR_REPLAYED_SEQUENCE
):
    print(
        "TEST 2: PASS"
    )
else:
    print(
        "TEST 2: FAIL"
    )


# ============================================================
# TEST 3
# Valid binary frame but unsafe joint target
# ============================================================

print("\n" + "=" * 72)
print("TEST 3 - JOINT LIMIT THROUGH BINARY INTERFACE")
print("=" * 72)


unsafe_action = ActionPacket(
    sequence_id=201,

    targets={
        "shoulder_pan": 10.0,
        "shoulder_lift": 0.0,
        "elbow_flex": 0.0,
        "wrist_flex": 0.0,
        "wrist_roll": 0.0,
        "gripper": 0.0,
    },

    duration=2.0,
    timeout=3.0,
)


unsafe_frame = (
    iq8.make_action_frame(
        unsafe_action
    )
)


unsafe_response_frame = (
    stm32.receive_binary_frame(
        unsafe_frame
    )
)


unsafe_state = (
    iq8.read_state_frame(
        unsafe_response_frame
    )
)


print_state(
    "IQ8 UNSAFE COMMAND RESPONSE",
    unsafe_state,
)


if (
    unsafe_state.state
    == ExecutionState.REJECTED
    and unsafe_state.fault_code
    == FaultCode.JOINT_LIMIT
    and unsafe_state.fault_detail == 0
):
    print(
        "TEST 3: PASS"
    )
else:
    print(
        "TEST 3: FAIL"
    )


# ============================================================
# TEST 4
# Corrupted binary transport
# ============================================================

print("\n" + "=" * 72)
print("TEST 4 - CORRUPTED BINARY FRAME")
print("=" * 72)


corruption_action = ActionPacket(
    sequence_id=202,

    targets={
        "shoulder_pan": 0.0,
        "shoulder_lift": 0.0,
        "elbow_flex": 0.0,
        "wrist_flex": 0.0,
        "wrist_roll": 0.0,
        "gripper": 0.0,
    },

    duration=1.5,
    timeout=2.5,
)


corrupted_frame = bytearray(
    iq8.make_action_frame(
        corruption_action
    )
)


# Corrupt one byte without updating CRC.
corrupted_frame[16] ^= 0x01


corruption_response_frame = (
    stm32.receive_binary_frame(
        bytes(corrupted_frame)
    )
)


corruption_state = (
    iq8.read_state_frame(
        corruption_response_frame
    )
)


print(
    "STM32 parser detected: "
    f"{stm32.last_transport_error}"
)


print_state(
    "IQ8 CORRUPTION RESPONSE",
    corruption_state,
)


if (
    stm32.last_transport_error
    == "CRC_MISMATCH"
    and corruption_state.state
    == ExecutionState.REJECTED
    and corruption_state.fault_code
    == FaultCode.INVALID_PACKET
):
    print(
        "TEST 4: PASS"
    )
else:
    print(
        "TEST 4: FAIL"
    )


# ============================================================
# Final summary
# ============================================================

print("\n" + "=" * 72)
print("END-TO-END SAMPLE TEST COMPLETE")
print("=" * 72)

print(
    "Mock IQ8"
    " -> binary ActionPacket"
    " -> Simulated STM32"
    " -> SO-101 MuJoCo"
    " -> binary StatePacket"
    " -> Mock IQ8"
)