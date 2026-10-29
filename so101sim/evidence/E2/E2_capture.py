#!/usr/bin/env python3
"""E2 evidence collector for SO101 Unified Simulation (LOCAL mode only).

Reads /api/state and sends one small, bounded test motion through /api/action.
Generates local evidence files; DOES NOT modify MuJoCo project files.
This is NOT a test of real VENTUNO Q or STM32H5F5 firmware.

Usage (from project root, with app.py --mode local running separately):
    python evidence/E2/E2_capture.py
"""
from __future__ import annotations
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = 'http://127.0.0.1:8000'
OUTPUT = Path(__file__).resolve().parent
JOINT_TO_MOVE = 'shoulder_pan'
DELTA = 0.12  # radians (~6.9 degrees), inside checked model limits
SAMPLE_INTERVAL = 0.20
MAX_WALL_TIME = 25.0


def exchange(path: str, payload: dict | None = None):
    body = None if payload is None else json.dumps(payload, allow_nan=False).encode('utf-8')
    request = Request(BASE + path, data=body, headers={'Content-Type': 'application/json'} if body else {},
                      method='POST' if body is not None else 'GET')
    try:
        with urlopen(request, timeout=6) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        try:
            parsed = json.loads(exc.read().decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            parsed = {'error': f'HTTP {exc.code} returned no JSON'}
        return exc.code, parsed


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def record():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().isoformat(timespec='seconds')
    print('=== E2 — Unified SO-101 local evidence capture ===', flush=True)
    print('Captured at:', stamp, flush=True)
    print('API:', BASE, flush=True)

    http, initial = exchange('/api/state')
    require(http == 200, 'GET /api/state returned non-200: ' + str(http))
    require(initial.get('mode') == 'local', 'Run python app.py --mode local; never test this in board mode')
    require(len(initial.get('joint_positions', [])) == 6, 'Expected six measured joints')
    require(len(initial.get('joint_limits', [])) == 6, 'Expected six joint limit pairs')
    names = initial['joint_names']
    idx = names.index(JOINT_TO_MOVE)
    before = [float(x) for x in initial['joint_positions']]
    limits = initial['joint_limits']
    lo, hi = [float(v) for v in limits[idx]]
    pos = before[idx]
    if pos + DELTA <= hi - 0.02:
        dest = pos + DELTA
    elif pos - DELTA >= lo + 0.02:
        dest = pos - DELTA
    else:
        raise RuntimeError('Current shoulder_pan position too close to boundaries for safe small test move')
    target = before.copy()
    target[idx] = round(dest, 6)
    seq = max(1, int(initial['accepted_sequence']) + 1)

    print('\n[1] INITIAL JOINT STATE', flush=True)
    for name, value in zip(names, before):
        print(f'  {name:16s}: {value:+.5f} rad', flush=True)
    print('Initial status:', initial['status'], 'sim_time:', initial['sim_time'], flush=True)
    print('Chosen joint:', JOINT_TO_MOVE, 'planned delta:', round(target[idx]-before[idx], 5), 'rad', flush=True)

    print('\n[2] REJECTION TESTS — no motion expected', flush=True)
    unsafe = target.copy()
    unsafe[idx] = hi + 1.0
    bad_bounds = {'type':'ACTION','sequence_id':seq,'joint_targets':unsafe,'duration':2.0,'timeout':4.0}
    h_bounds, r_bounds = exchange('/api/action', bad_bounds)
    ok_bounds = (h_bounds == 400 and r_bounds.get('type') == 'REJECTED'
                 and ('outside' in r_bounds.get('reason','') or 'radians' in r_bounds.get('reason','')))
    print('Out-of-range:', h_bounds, r_bounds, 'PASS' if ok_bounds else 'FAIL', flush=True)

    malformed = {'type':'ACTION','sequence_id':seq,'joint_targets':[0.0]*5,'duration':2.0,'timeout':4.0}
    h_shape, r_shape = exchange('/api/action', malformed)
    ok_shape = (h_shape == 400 and r_shape.get('type') == 'REJECTED'
                and 'exactly six' in r_shape.get('reason',''))
    print('Missing joint:', h_shape, r_shape, 'PASS' if ok_shape else 'FAIL', flush=True)
    _h_rejected_state, rejected_state = exchange('/api/state')
    ok_not_queued = rejected_state.get('accepted_sequence') == initial.get('accepted_sequence')
    print('Accepted sequence unchanged after rejected commands:',
          initial.get('accepted_sequence'), '->', rejected_state.get('accepted_sequence'),
          'PASS' if ok_not_queued else 'FAIL', flush=True)
    require(ok_bounds and ok_shape and ok_not_queued,
            'Validation failed or a rejected action unexpectedly updated accepted_sequence.')

    print('\n[3] VALID ACTION AND TRAJECTORY', flush=True)
    valid = {'type':'ACTION','sequence_id':seq,'joint_targets':target,'duration':2.0,'timeout':4.0}
    h_ack, ack = exchange('/api/action', valid)
    ok_ack = h_ack == 202 and ack.get('type') == 'ACK' and ack.get('sequence_id') == seq
    print('POST /api/action:', h_ack, ack, 'PASS' if ok_ack else 'FAIL', flush=True)
    require(ok_ack, 'Expected 202 ACK from local API. Another test/action might already be running.')

    t0 = time.monotonic()
    samples = []
    final = None
    while time.monotonic() - t0 <= MAX_WALL_TIME:
        status_code, snap = exchange('/api/state')
        require(status_code == 200, 'GET /api/state failed during trajectory')
        elapsed = time.monotonic()-t0
        row = {'wall_elapsed_s':round(elapsed, 3), 'sim_time_s':snap['sim_time'],
               'status':snap['status'], 'fault':snap.get('fault'),
               'applied_sequence':snap['applied_sequence']}
        for name, measured, ctrl in zip(names, snap['joint_positions'], snap['target_positions']):
            row['qpos_'+name] = round(float(measured),6)
            row['ctrl_'+name] = round(float(ctrl),6)
        samples.append(row)
        print(f"  t={elapsed:5.2f}s sim={float(snap['sim_time']):7.3f}s "
              f"status={snap['status']:8s} qpos={row['qpos_'+JOINT_TO_MOVE]:+.4f} "
              f"ctrl={row['ctrl_'+JOINT_TO_MOVE]:+.4f} seq={snap['applied_sequence']}", flush=True)
        if snap['applied_sequence'] == seq and snap['status'] in ('DONE','FAULT'):
            final = snap
            break
        time.sleep(SAMPLE_INTERVAL)
    if final is None:
        _h, final = exchange('/api/state')
        print('WARNING: Timed out waiting for DONE/FAULT. Save evidence without claiming PASS.', flush=True)

    print('\n[4] REPLAYED ACTION', flush=True)
    h_replay, r_replay = exchange('/api/action', valid)
    ok_replay = (h_replay == 400 and r_replay.get('type') == 'REJECTED'
                 and ('Stale' in r_replay.get('reason','') or 'duplicated' in r_replay.get('reason','')))
    print('Duplicate sequence:', h_replay, r_replay, 'PASS' if ok_replay else 'FAIL', flush=True)

    final_q = list(map(float, final['joint_positions']))
    errors = [abs(actual - planned) for actual,planned in zip(final_q,target)]
    moved = abs(final_q[idx]-before[idx])
    max_err = max(errors)
    ok_applied = final['applied_sequence'] == seq
    ok_done = final['status'] == 'DONE' and final.get('fault') is None
    ok_motion = moved > 0.03
    ok_tracking = max_err <= 0.025 + 1e-6
    checks = {'out_of_range_rejected':ok_bounds, 'malformed_action_rejected':ok_shape,
              'rejected_actions_not_queued':ok_not_queued,
              'valid_action_acknowledged':ok_ack, 'sequence_applied':ok_applied,
              'completed_done':ok_done, 'commanded_joint_moved':ok_motion,
              'max_joint_error_at_most_0_025_rad':ok_tracking,
              'replay_rejected':ok_replay}
    result = 'PASS' if all(checks.values()) else 'NEEDS_REVIEW'
    report = {'capture_time':stamp,'scope':'LOCAL simulator HTTP API, not STM32 or VENTUNO hardware',
              'result':result,'checks':checks,'joint_names':names, 'initial_state':initial,
              'valid_action':valid,'ack':ack,'final_state':final,'replay_response':r_replay,
              'limit_rejection':r_bounds,'shape_rejection':r_shape,
              'observed_movement_rad':round(moved,6),'max_final_tracking_error_rad':round(max_err,6),
              'samples':len(samples)}
    (OUTPUT/'E2_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    with (OUTPUT/'E2_trajectory.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(samples[0]))
        writer.writeheader()
        writer.writerows(samples)

    print('\n[5] FINAL MEASUREMENTS', flush=True)
    for name, a,b,error in zip(names,target,final_q,errors):
        print(f'  {name:16s} target={a:+.5f} measured={b:+.5f} abs_error={error:.6f} rad',flush=True)
    print('Observed commanded-joint movement:',round(moved,6),'rad',flush=True)
    print('Maximum joint tracking error:',round(max_err,6),'rad',flush=True)
    print('Final status:',final['status'],'fault:',final.get('fault'),flush=True)
    for name, passed in checks.items():
        print(f'  {"PASS" if passed else "FAIL"}: {name}',flush=True)
    print('OVERALL:',result,flush=True)
    print('Evidence:',OUTPUT/'E2_report.json',flush=True)
    print('Evidence:',OUTPUT/'E2_trajectory.csv',flush=True)
    print('Reminder: This is a LOCAL simulation test; it does not validate physical firmware, MCU execution, or grasping.',flush=True)
    return 0 if result == 'PASS' else 1


if __name__ == '__main__':
    try:
        sys.exit(record())
    except (RuntimeError, URLError, TimeoutError, KeyError, ValueError, IndexError) as exc:
        print('E2 CAPTURE FAILED:',type(exc).__name__+':',exc,file=sys.stderr,flush=True)
        print('Check: python app.py --mode local is running on port 8000; do not run another motion concurrently.',file=sys.stderr)
        sys.exit(2)
