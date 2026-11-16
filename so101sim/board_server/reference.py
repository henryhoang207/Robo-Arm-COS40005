"""Local contact-based reference controller. Uses ground truth, not AI or MCU code."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import time

import numpy as np

from protocol import ProtocolError, SCHEMA_VERSION


def build_plan(sim):
    if sim.task.target != 'red_ball':
        raise ProtocolError('The validated local reference task uses red_ball; RESET with that target')
    mj, model = sim.mj, sim.model
    scratch = mj.MjData(model)
    site = mj.mj_name2id(model, mj.mjtObj.mjOBJ_SITE, 'grasp_center')
    dofs = sim.vids[:4]
    limits = np.array(sim.limits)
    down = np.array([0., 0., -1.])
    jp, jr = np.zeros((3, model.nv)), np.zeros((3, model.nv))

    def solve(position, initial):
        weight = .12 if position[2] < .09 else 0.0
        best = None
        for elbow in (None, .8, 1.4, -.8):
            q = np.array(initial, dtype=float)
            if elbow is not None:
                q[2], q[1] = elbow, -.7 if elbow > 0 else .5
                q[3] = 1.57 - q[1] - q[2]
            for _ in range(200):
                scratch.qpos[:] = sim.data.qpos
                scratch.qpos[sim.qids] = q
                mj.mj_forward(model, scratch)
                direction = scratch.site_xmat[site].reshape(3, 3)[:, 0]
                ep = np.array(position) - scratch.site_xpos[site]
                er = np.cross(direction, down)
                if np.linalg.norm(ep) < 1e-5 and (weight == 0 or np.linalg.norm(er) < 1e-4):
                    break
                mj.mj_jacSite(model, scratch, jp, jr, site)
                jac = np.vstack((jp[:, dofs], weight * (np.eye(3) - np.outer(direction, direction)) @ jr[:, dofs]))
                delta = jac.T @ np.linalg.solve(jac @ jac.T + np.eye(6) * 1e-5, np.r_[ep, weight * er])
                q[:4] += np.clip(delta, -.12, .12)
                q = np.clip(q, limits[:, 0] + .001, limits[:, 1] - .001)
            residual = np.linalg.norm(ep) + weight * np.linalg.norm(er)
            score = residual + .0001 * np.linalg.norm(q - initial)
            if best is None or score < best[0]:
                best = score, residual, q.copy()
        if best[1] > .003:
            raise ProtocolError(f'Reference target is outside the validated reach (IK residual {best[1]:.4f} m)')
        return best[2]

    xy = sim.data.xpos[sim.task.bodies[sim.task.target], :2].copy()
    box = sim.data.xpos[sim.task.box, :2].copy()
    q = np.array(sim._joints())
    previous = q.copy()
    plan = []

    def add(label, duration, contact=False):
        nonlocal previous
        duration = max(duration, float(np.max(1.875 * np.abs(q - previous) / sim.max_speeds)) * 1.02)
        plan.append({'type': 'ACTION', 'sequence_id': len(plan), 'joint_targets': q.tolist(),
                     'duration': duration, 'timeout': duration + 3, 'valid_for_s': 60,
                     'allow_gripper_contact': contact, 'label': label})
        previous = q.copy()

    q = solve([*xy, .08], q); q[5] = .8
    add('APPROACH', 1)
    q = solve([*xy, .016], q); q[5] = 1.2
    add('LOWER', 1.2)
    q[5] = .1
    add('GRASP', 2, True)
    q = solve([*xy, .14], q)
    add('LIFT', 2, True)
    # Rotate the lifted arm before approaching the box; avoid dragging over the table.
    q[0] = float(np.arctan2(box[1], box[0]) - np.pi / 2)
    add('TRANSFER', 4, True)
    q = solve([*box, .12], q)
    add('ABOVE_BOX', 1.5, True)
    q[5] = 1.2
    add('RELEASE', 1)
    add('SETTLE', 1)
    return plan


def benchmark(episodes=3, seed=0, randomize=False, output=None):
    from engine import Simulation
    from runtime_support import RUNTIME
    results = []
    for index in range(episodes):
        sim = Simulation('local', log_dir=RUNTIME / 'runs')
        try:
            sim.command({'type': 'RESET', 'schema_version': SCHEMA_VERSION, 'run_id': sim.run_id,
                         'session_id': sim.session_id, 'seed': seed + index, 'randomize': randomize})
            started = time.monotonic()
            sim.start_reference({'schema_version': SCHEMA_VERSION, 'run_id': sim.run_id, 'session_id': sim.session_id})
            min_z = 1.0
            for _ in range(int(65 / sim.model.opt.timestep)):
                sim.step()
                min_z = min(min_z, float(sim.data.xpos[sim.task.bodies[sim.task.target], 2]))
                if sim.hold_latched or (not sim.reference_active and sim.task.status in ('SUCCESS', 'FAILURE')):
                    break
            result = {'run_id': sim.run_id, **sim.task.summary(), 'fault': sim.fault,
                      'min_object_center_z_m': min_z, 'completed_sequence': sim.last_completed_sequence,
                      'wall_time_s': round(time.monotonic() - started, 3),
                      'final_position': sim.data.xpos[sim.task.bodies[sim.task.target]].tolist(),
                      'model_sha256': sim.identity['model_sha256']}
            results.append(result)
            print(json.dumps(result), flush=True)
        finally:
            sim.close()
    report = {'controller': 'ground-truth reference, not AI/MCU', 'randomize': randomize,
              'episodes': results, 'successes': sum(r['status'] == 'SUCCESS' for r in results)}
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--episodes', type=int, default=3)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--randomize', action='store_true')
    parser.add_argument('--output', default='runtime/validation/reference.json')
    args = parser.parse_args()
    if not 1 <= args.episodes <= 100 or not 0 <= args.seed <= 2**32 - args.episodes:
        parser.error('episodes must be 1..100 and seed must fit uint32')
    result = benchmark(args.episodes, args.seed, args.randomize, args.output)
    raise SystemExit(0 if result['successes'] == args.episodes else 1)
