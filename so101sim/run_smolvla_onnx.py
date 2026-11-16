#!/usr/bin/env python3
"""Local-mode test: the VENTUNO Q SmolVLA runner drives the MuJoCo scene on this laptop.

Uses so101arm/python/smolvla_runner.py, the same code that board mode v1 will run (steps 4a-4d), but both ONNX
stages run on the laptop CPU and each chunk goes straight into the simulator instead of over USB. Physics is
paused while the model infers, so slow CPU inference does not change the physics.

    python run_smolvla_onnx.py                              # 4 balls + box, level 1 (integration)
    python run_smolvla_onnx.py --scene desk-cleanup --match-dataset --steps 900   # level 2, ~30 s like episode 230
    python run_smolvla_onnx.py --viewer --steps 600 --replan 25

Every run writes runs/<run_id>/: run.jsonl (one line per chunk), summary.json, the first frames as PNG and
io_chunkNNN.npz files that `smolvla_runner.py replay` can re-run on the board's NPU for a CPU-vs-NPU check.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path

import numpy as np

from engine import ROOT, Simulation
from joint_targets import FPS, JointTargets

sys.path.insert(0, str(ROOT.parent / "so101arm" / "python"))
from smolvla_runner import DEFAULT_CORE_DIR, DEFAULT_PREFIX_DIR, SmolVLARunner, save_io  # noqa: E402

DEFAULT_TASKS = {
    "local": "pick up the red ball and place it in the box",
    "desk-cleanup": "Place the ball into the bowl to clear the desk",
}
BALLS = ("red", "green", "blue", "yellow")
# Horizontal radius (m) around the drop_box body that counts as "inside": box interior / bowl rim.
CONTAINER_RADIUS = {"local": 0.05, "desk-cleanup": 0.07}


def build_scene(name, match_dataset=False):
    if name == "local":
        return Simulation()
    import desk_cleanup
    return desk_cleanup.create_simulation(match_dataset=match_dataset)


def render(sim, renderer, camera):
    renderer.update_scene(sim.data, camera=camera)
    return renderer.render().copy()


def balls_in_container(sim, scene):
    mj = sim.mj
    box = sim.data.xpos[mj.mj_name2id(sim.model, mj.mjtObj.mjOBJ_BODY, "drop_box")]
    result = {}
    for colour in BALLS:
        bid = mj.mj_name2id(sim.model, mj.mjtObj.mjOBJ_BODY, f"{colour}_ball")
        if bid < 0:
            continue
        p = sim.data.xpos[bid]
        result[colour] = bool(np.hypot(p[0] - box[0], p[1] - box[1]) < CONTAINER_RADIUS[scene] and p[2] < 0.09)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scene", choices=tuple(DEFAULT_TASKS), default="local")
    parser.add_argument("--task", help="Natural-language command (default depends on --scene)")
    parser.add_argument("--steps", type=int, default=300, help="Joint targets to execute at 30 Hz (300 = 10 s)")
    parser.add_argument("--replan", type=int, default=25, help="Targets executed from each 50-step chunk (K)")
    parser.add_argument("--core-provider", choices=("cpu", "qnn"), default="cpu",
                        help="Stage 2 provider; qnn only exists on VENTUNO Q")
    parser.add_argument("--prefix-dir", type=Path, default=DEFAULT_PREFIX_DIR)
    parser.add_argument("--core-dir", type=Path, default=DEFAULT_CORE_DIR)
    parser.add_argument("--seed", type=int, default=0, help="Seed for the flow-matching noise")
    parser.add_argument("--threads", type=int, default=0, help="ONNX Runtime CPU threads (0 = all cores)")
    parser.add_argument("--save-io", type=int, default=1, help="Save the first N chunks as npz for the board replay")
    parser.add_argument("--settle", type=float, default=0.4, help="Seconds of physics before the first observation")
    parser.add_argument("--viewer", action="store_true", help="Show the MuJoCo window")
    parser.add_argument("--match-dataset", action="store_true",
                        help="desk-cleanup only: cameras and look fitted to the Project-IRA recording")
    args = parser.parse_args()
    task = (args.task or DEFAULT_TASKS[args.scene]).strip()
    if args.steps < 1 or not 1 <= args.replan <= 50 or not task:
        parser.error("--steps must be positive, --replan must be 1..50 and the task must contain text")
    if args.match_dataset and args.scene != "desk-cleanup":
        parser.error("--match-dataset needs --scene desk-cleanup")

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + f"-{args.scene}"
    run_dir = ROOT / "runs" / run_id
    run_dir.mkdir(parents=True)
    print(f"Run {run_id}\nTask: {task!r}\nLoading SmolVLA ONNX (prefix CPU, core {args.core_provider})...", flush=True)
    t = time.perf_counter()
    runner = SmolVLARunner(args.prefix_dir, args.core_dir, core_provider=args.core_provider, seed=args.seed,
                           threads=args.threads)
    print(f"Loaded in {time.perf_counter() - t:.1f} s: {runner.describe()}", flush=True)

    sim = build_scene(args.scene, args.match_dataset)
    for _ in range(round(args.settle / sim.model.opt.timestep)):
        sim.step()
    stream = JointTargets(sim, runner.cfg.zero_rad, runner.cfg.rad_per_unit)
    limits = np.asarray(sim.limits)
    initial_joints = sim.data.qpos[sim.qids].copy()
    meta = {"run_id": run_id, "scene": args.scene, "match_dataset": args.match_dataset, "task": task, "replan": args.replan, "seed": args.seed,
            "core_provider": runner.core_provider, "host": platform.node(), **runner.describe()}
    (run_dir / "summary.json").write_text(json.dumps({**meta, "status": "RUNNING"}, indent=2), encoding="utf-8")

    viewer_context = nullcontext()
    if args.viewer:
        from mujoco.viewer import launch_passive
        viewer_context = launch_passive(sim.model, sim.data)

    totals = {"chunks": 0, "clipped": 0}
    timings = []
    status = "TIMEOUT"
    with viewer_context as viewer, sim.mj.Renderer(sim.model, height=480, width=640) as renderer, \
            open(run_dir / "run.jsonl", "w", encoding="utf-8") as log:
        while stream.executed < args.steps and (viewer is None or viewer.is_running()):
            chunk_id = totals["chunks"]
            # Observation: both cameras and the joints at the same sim instant (overhead -> image1, wrist -> image2;
            # mapping set by image_inputs in so101arm/python/smolvla_config.json).
            wrist = render(sim, renderer, "wrist_camera")
            overhead = render(sim, renderer, "overhead_camera")
            joints = sim.data.qpos[sim.qids].copy()
            obs_time = float(sim.data.time)
            if chunk_id == 0:
                from PIL import Image
                Image.fromarray(wrist).save(run_dir / "chunk000_wrist.png")
                Image.fromarray(overhead).save(run_dir / "chunk000_overhead.png")

            keep = chunk_id < args.save_io
            result = runner.infer(wrist, overhead, joints, task, keep_io=keep)
            if keep:
                save_io(run_dir / f"io_chunk{chunk_id:03d}.npz", result, {**meta, "chunk_id": chunk_id})

            k = min(args.replan, args.steps - stream.executed)
            raw = result.actions_rad[:k]
            targets = np.clip(raw, limits[:, 0], limits[:, 1])
            clipped = int(np.any(raw != targets, axis=1).sum())
            # How far the first target is from where the arm is now: large values usually mean a wrong
            # state normalization or calibration, not a bad policy.
            jump = float(np.max(np.abs(targets[0] - joints)))
            for target in targets:
                if viewer is not None and not viewer.is_running():
                    break
                start = time.monotonic()
                stream.apply(target)
                if viewer is not None:
                    viewer.sync()
                    time.sleep(max(0.0, 1 / FPS - (time.monotonic() - start)))

            done = balls_in_container(sim, args.scene)
            totals["chunks"] += 1
            totals["clipped"] += clipped
            timings.append(result.timings_ms)
            record = {"chunk_id": chunk_id, "obs_sim_time": round(obs_time, 4), "joints_rad": joints.round(5).tolist(),
                      "first_target_rad": targets[0].round(5).tolist(), "first_jump_rad": round(jump, 4),
                      "applied": k, "clipped": clipped, "timings_ms": result.timings_ms, "in_container": done}
            log.write(json.dumps(record) + "\n")
            log.flush()
            print(f"chunk {chunk_id:3d} | t={obs_time:6.2f}s | prefix {result.timings_ms['prefix']:7.0f} ms "
                  f"core {result.timings_ms['core']:6.0f} ms | applied {k:2d} clipped {clipped:2d} | "
                  f"jump {jump:.3f} rad | in box: {[c for c, v in done.items() if v] or '-'}", flush=True)
            if any(done.values()):
                status = "SUCCESS"
                break

    if not np.isfinite(sim.data.qpos).all():
        raise RuntimeError("MuJoCo returned a non-finite position")
    summary = {**meta, "status": status, **totals, "targets_executed": stream.executed,
               "sim_seconds": round(float(sim.data.time - stream.start_time), 3),
               "largest_joint_change_rad": round(float(np.max(np.abs(sim.data.qpos[sim.qids] - initial_joints))), 4),
               "in_container": balls_in_container(sim, args.scene),
               "mean_ms": {key: round(float(np.mean([t[key] for t in timings])), 1) for key in timings[0]}
               if timings else {}}
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n{status}: {stream.executed} targets, {totals['chunks']} chunks, {totals['clipped']} clipped. "
          f"Mean latency {summary['mean_ms']}.\nLogs: {run_dir}", flush=True)


if __name__ == "__main__":
    main()
