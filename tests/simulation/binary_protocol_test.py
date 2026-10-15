import struct
import zlib
from dataclasses import dataclass
from enum import IntEnum


# ============================================================
# Protocol constants
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
    TARGET_NOT_REACHED = 6
    CONTROLLER_BUSY = 7


# Little-endian:
#
# H = uint16
# B = uint8
# I = uint32
#
# Header:
# magic, version, type, sequence_id, payload_length

HEADER_FORMAT = "<HBBIH"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# 6 joint targets + duration + timeout
ACTION_PAYLOAD_FORMAT = "<8f"
ACTION_PAYLOAD_SIZE = struct.calcsize(
    ACTION_PAYLOAD_FORMAT
)

# state, fault_code, fault_detail, reserved
# + six measured joint positions
STATE_PAYLOAD_FORMAT = "<HHHH6f"
STATE_PAYLOAD_SIZE = struct.calcsize(
    STATE_PAYLOAD_FORMAT
)

CRC_FORMAT = "<I"
CRC_SIZE = struct.calcsize(CRC_FORMAT)


# ============================================================
# Packet objects
# ============================================================

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


# ============================================================
# Generic helpers
# ============================================================

def calculate_crc(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def encode_frame(
    message_type: MessageType,
    sequence_id: int,
    payload: bytes,
) -> bytes:

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

    return body + struct.pack(
        CRC_FORMAT,
        crc,
    )


def decode_frame(frame: bytes):
    minimum_size = HEADER_SIZE + CRC_SIZE

    if len(frame) < minimum_size:
        raise ValueError("FRAME_TOO_SHORT")

    header = frame[:HEADER_SIZE]

    (
        magic,
        version,
        message_type,
        sequence_id,
        payload_length,
    ) = struct.unpack(
        HEADER_FORMAT,
        header,
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

    payload_start = HEADER_SIZE
    payload_end = (
        HEADER_SIZE + payload_length
    )

    payload = frame[
        payload_start:payload_end
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
            message_type
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


# ============================================================
# Action packet codec
# ============================================================

def encode_action_packet(
    packet: ActionPacket,
) -> bytes:

    if set(packet.targets.keys()) != set(
        JOINT_NAMES
    ):
        raise ValueError(
            "INCOMPLETE_TARGET_SET"
        )

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


def decode_action_packet(
    frame: bytes,
) -> ActionPacket:

    (
        message_type,
        sequence_id,
        payload,
    ) = decode_frame(frame)

    if message_type != MessageType.ACTION:
        raise ValueError(
            "EXPECTED_ACTION_FRAME"
        )

    if len(payload) != ACTION_PAYLOAD_SIZE:
        raise ValueError(
            "INVALID_ACTION_PAYLOAD_LENGTH"
        )

    values = struct.unpack(
        ACTION_PAYLOAD_FORMAT,
        payload,
    )

    targets = {
        name: values[index]
        for index, name
        in enumerate(JOINT_NAMES)
    }

    duration = values[6]
    timeout = values[7]

    return ActionPacket(
        sequence_id=sequence_id,
        targets=targets,
        duration=duration,
        timeout=timeout,
    )


# ============================================================
# State packet codec
# ============================================================

def encode_state_packet(
    packet: StatePacket,
) -> bytes:

    joint_positions = [
        float(packet.positions[name])
        for name in JOINT_NAMES
    ]

    payload = struct.pack(
        STATE_PAYLOAD_FORMAT,

        int(packet.state),
        int(packet.fault_code),

        packet.fault_detail,
        0,  # reserved

        *joint_positions,
    )

    return encode_frame(
        MessageType.STATE,
        packet.sequence_id,
        payload,
    )


def decode_state_packet(
    frame: bytes,
) -> StatePacket:

    (
        message_type,
        sequence_id,
        payload,
    ) = decode_frame(frame)

    if message_type != MessageType.STATE:
        raise ValueError(
            "EXPECTED_STATE_FRAME"
        )

    if len(payload) != STATE_PAYLOAD_SIZE:
        raise ValueError(
            "INVALID_STATE_PAYLOAD_LENGTH"
        )

    values = struct.unpack(
        STATE_PAYLOAD_FORMAT,
        payload,
    )

    state = ExecutionState(values[0])
    fault_code = FaultCode(values[1])
    fault_detail = values[2]

    positions = {
        name: values[index + 4]
        for index, name
        in enumerate(JOINT_NAMES)
    }

    return StatePacket(
        sequence_id=sequence_id,
        state=state,
        fault_code=fault_code,
        fault_detail=fault_detail,
        positions=positions,
    )


# ============================================================
# Pretty print
# ============================================================

def print_hex(frame: bytes):
    print(
        " ".join(
            f"{byte:02X}"
            for byte in frame
        )
    )


# ============================================================
# TEST 1
# ActionPacket round trip
# ============================================================

print("=" * 70)
print("TEST 1 - ACTION PACKET BINARY ROUND TRIP")
print("=" * 70)

original_action = ActionPacket(
    sequence_id=100,

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


action_frame = encode_action_packet(
    original_action
)

print(
    f"Encoded frame length: "
    f"{len(action_frame)} bytes"
)

print("\nBinary frame:")
print_hex(action_frame)


decoded_action = decode_action_packet(
    action_frame
)


print("\nDecoded ActionPacket:")
print(decoded_action)


if (
    decoded_action.sequence_id == 100
    and abs(
        decoded_action.targets[
            "shoulder_pan"
        ] - 0.50
    ) < 1e-5
    and abs(
        decoded_action.duration - 3.0
    ) < 1e-5
    and abs(
        decoded_action.timeout - 5.0
    ) < 1e-5
):
    print("\nTEST 1: PASS")
else:
    print("\nTEST 1: FAIL")


# ============================================================
# TEST 2
# CRC corruption
# ============================================================

print("\n" + "=" * 70)
print("TEST 2 - CRC CORRUPTION")
print("=" * 70)


corrupted_frame = bytearray(
    action_frame
)

# Deliberately corrupt one payload byte.
corrupted_frame[15] ^= 0x01


try:
    decode_action_packet(
        bytes(corrupted_frame)
    )

    print(
        "TEST 2: FAIL "
        "(corrupted frame was accepted)"
    )

except ValueError as error:

    print(
        f"Rejected correctly: {error}"
    )

    if str(error) == "CRC_MISMATCH":
        print("TEST 2: PASS")
    else:
        print("TEST 2: FAIL")


# ============================================================
# TEST 3
# StatePacket round trip
# ============================================================

print("\n" + "=" * 70)
print("TEST 3 - STATE PACKET BINARY ROUND TRIP")
print("=" * 70)


original_state = StatePacket(
    sequence_id=100,

    state=ExecutionState.DONE,

    fault_code=FaultCode.NONE,

    fault_detail=0,

    positions={
        "shoulder_pan": 0.50,
        "shoulder_lift": 0.4007,
        "elbow_flex": -0.3995,
        "wrist_flex": 0.2501,
        "wrist_roll": 0.50,
        "gripper": 0.60,
    },
)


state_frame = encode_state_packet(
    original_state
)


print(
    f"Encoded frame length: "
    f"{len(state_frame)} bytes"
)

print("\nBinary frame:")
print_hex(state_frame)


decoded_state = decode_state_packet(
    state_frame
)


print("\nDecoded StatePacket:")
print(decoded_state)


if (
    decoded_state.sequence_id == 100
    and decoded_state.state
    == ExecutionState.DONE
    and decoded_state.fault_code
    == FaultCode.NONE
):
    print("\nTEST 3: PASS")
else:
    print("\nTEST 3: FAIL")


# ============================================================
# TEST 4
# Wrong protocol version
# ============================================================

print("\n" + "=" * 70)
print("TEST 4 - PROTOCOL VERSION CHECK")
print("=" * 70)


bad_version_frame = bytearray(
    action_frame
)

# Header byte layout:
#
# byte 0-1 = MAGIC
# byte 2   = VERSION
#
bad_version_frame[2] = 99


# CRC must be recalculated so that
# this specifically tests VERSION,
# not CRC failure.

body = bad_version_frame[:-CRC_SIZE]

new_crc = calculate_crc(
    bytes(body)
)

bad_version_frame[-CRC_SIZE:] = struct.pack(
    CRC_FORMAT,
    new_crc,
)


try:
    decode_action_packet(
        bytes(bad_version_frame)
    )

    print(
        "TEST 4: FAIL "
        "(unsupported version accepted)"
    )

except ValueError as error:

    print(
        f"Rejected correctly: {error}"
    )

    if str(error) == "UNSUPPORTED_VERSION":
        print("TEST 4: PASS")
    else:
        print("TEST 4: FAIL")


print("\n" + "=" * 70)
print("PROTOCOL SUMMARY")
print("=" * 70)

print(f"Header size          : {HEADER_SIZE} bytes")
print(
    f"Action payload size  : "
    f"{ACTION_PAYLOAD_SIZE} bytes"
)
print(
    f"State payload size   : "
    f"{STATE_PAYLOAD_SIZE} bytes"
)
print(f"CRC size             : {CRC_SIZE} bytes")

print(
    f"Action frame total   : "
    f"{HEADER_SIZE + ACTION_PAYLOAD_SIZE + CRC_SIZE} bytes"
)

print(
    f"State frame total    : "
    f"{HEADER_SIZE + STATE_PAYLOAD_SIZE + CRC_SIZE} bytes"
)