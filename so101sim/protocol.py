"""Network contract and model-independent validation; no MCU trust inferred."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import math

JOINT_NAMES = ('shoulder_pan', 'shoulder_lift', 'elbow_flex', 'wrist_flex', 'wrist_roll', 'gripper')
MAX_LINE = 16_384

class ProtocolError(ValueError):
    pass

@dataclass(frozen=True)
class Action:
    sequence_id: int
    targets: tuple[float, ...]
    duration: float
    timeout: float


def parse_action(obj: Any, limits, last_sequence: int) -> Action:
    if not isinstance(obj, dict) or obj.get('type') != 'ACTION':
        raise ProtocolError('Expected ACTION JSON object')
    seq = obj.get('sequence_id')
    if type(seq) is not int or not (0 <= seq < 2**32):
        raise ProtocolError('sequence_id must be uint32 integer')
    if seq <= last_sequence:
        raise ProtocolError('Stale or duplicated sequence_id')
    targets = obj.get('joint_targets')
    if not isinstance(targets, list) or len(targets) != 6:
        raise ProtocolError('joint_targets must contain exactly six angles (radians)')
    q = []
    for i, item in enumerate(targets):
        if type(item) not in (int, float) or not math.isfinite(item):
            raise ProtocolError(f'Non-finite or nonnumeric target at {JOINT_NAMES[i]}')
        lo, hi = limits[i]
        if not (lo <= float(item) <= hi):
            raise ProtocolError(f'{JOINT_NAMES[i]} outside [{lo:.5f}, {hi:.5f}] radians')
        q.append(float(item))
    duration, timeout = obj.get('duration', 2.0), obj.get('timeout', 4.0)
    if type(duration) not in (int, float) or not math.isfinite(duration) or not 0.1 <= duration <= 30.0:
        raise ProtocolError('duration must be between 0.1 and 30 seconds')
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not duration < timeout <= 60.0:
        raise ProtocolError('timeout must be larger than duration, maximum 60 seconds')
    return Action(seq, tuple(q), float(duration), float(timeout))
