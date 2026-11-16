"""Versioned simulator commands. Angles are MJCF radians, including the gripper."""
from __future__ import annotations
from dataclasses import dataclass
import math
import time
from typing import Any

SCHEMA_VERSION = 2
JOINT_NAMES = ('shoulder_pan', 'shoulder_lift', 'elbow_flex', 'wrist_flex', 'wrist_roll', 'gripper')
MAX_LINE = 65_536
MAX_POINTS = 64


class ProtocolError(ValueError):
    pass


def number(value, label, lo, hi):
    if type(value) not in (int, float) or not math.isfinite(value) or not lo <= value <= hi:
        raise ProtocolError(f'{label} must be a finite number in [{lo}, {hi}]')
    return float(value)


def angles(values, limits):
    if not isinstance(values, list) or len(values) != 6:
        raise ProtocolError('joint_targets must contain exactly six angles (radians)')
    return tuple(number(v, name, *bound) for v, name, bound in zip(values, JOINT_NAMES, limits))


@dataclass(frozen=True)
class Point:
    time: float
    targets: tuple[float, ...]


@dataclass(frozen=True)
class Action:
    sequence_id: int
    targets: tuple[float, ...]
    duration: float
    timeout: float
    points: tuple[Point, ...] = ()
    allow_gripper_contact: bool = False
    valid_until: float = math.inf
    label: str = ''


def parse_action(obj: Any, limits, last_sequence: int) -> Action:
    if not isinstance(obj, dict) or obj.get('type') not in ('ACTION', 'ACTION_CHUNK'):
        raise ProtocolError('Expected ACTION or ACTION_CHUNK JSON object')
    seq = obj.get('sequence_id')
    if type(seq) is not int or not 0 <= seq < 2**32:
        raise ProtocolError('sequence_id must be uint32 integer')
    if seq <= last_sequence:
        raise ProtocolError('Stale or duplicated sequence_id')
    points = ()
    if obj['type'] == 'ACTION_CHUNK':
        raw = obj.get('points')
        if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_POINTS:
            raise ProtocolError(f'points must contain 1..{MAX_POINTS} timed setpoints')
        parsed = []
        previous = 0.0
        for item in raw:
            if not isinstance(item, dict):
                raise ProtocolError('Each point must be an object')
            when = number(item.get('time_from_start'), 'time_from_start', 0.01, 10.0)
            if when - previous < 0.01 - 1e-9:
                raise ProtocolError('Setpoints must be ordered at least 0.01 seconds apart')
            parsed.append(Point(when, angles(item.get('joint_targets'), limits)))
            previous = when
        points = tuple(parsed)
        duration, targets = points[-1].time, points[-1].targets
    else:
        targets = angles(obj.get('joint_targets'), limits)
        duration = number(obj.get('duration', 2.0), 'duration', 0.1, 30.0)
    timeout = number(obj.get('timeout', max(4.0, duration + 2.0)), 'timeout', 0.1, 60.0)
    if timeout <= duration:
        raise ProtocolError('timeout must be larger than duration')
    contact = obj.get('allow_gripper_contact', False)
    if type(contact) is not bool:
        raise ProtocolError('allow_gripper_contact must be boolean')
    ttl = number(obj.get('valid_for_s', 10.0), 'valid_for_s', 0.05, 60.0)
    label = obj.get('label', '')
    if not isinstance(label, str) or len(label) > 80:
        raise ProtocolError('label must be a string of at most 80 characters')
    return Action(seq, targets, duration, timeout, points, contact, time.monotonic() + ttl, label)


def validate_context(obj, run_id, session_id):
    if not isinstance(obj, dict):
        raise ProtocolError('Expected JSON object')
    if type(obj.get('schema_version')) is not int or obj['schema_version'] != SCHEMA_VERSION:
        raise ProtocolError(f'schema_version must be {SCHEMA_VERSION}; read /api/state or WELCOME')
    if obj.get('run_id') != run_id:
        raise ProtocolError('Wrong or stale run_id; read the current state after RESET')
    if obj.get('session_id') != session_id:
        raise ProtocolError('Wrong or stale session_id; authenticate/read state again')
