"""Closed-loop SmolVLA rollout in the episode-230 scene with per-step ball/gripper logging and per-chunk images.

Same observation, chunk execution (n_action_steps) and target streaming as so101sim/run_smolvla.py.
"""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, r"C:\RobotArm\so101sim")
import numpy as np
import torch
from PIL import Image
import desk_cleanup
from joint_targets import JointTargets
from run_smolvla import observation

ckpt, out = Path(sys.argv[1]), Path(sys.argv[2])
steps = int(sys.argv[3]) if len(sys.argv) > 3 else 900
seed = int(sys.argv[4]) if len(sys.argv) > 4 else 0
replan = int(sys.argv[5]) if len(sys.argv) > 5 else 0   # 0 = policy default (n_action_steps)
out.mkdir(parents=True, exist_ok=True)
torch.manual_seed(seed)
from lerobot.configs.policies import PreTrainedConfig
from lerobot.policies import make_pre_post_processors
from lerobot.policies.smolvla import SmolVLAPolicy
cfg = PreTrainedConfig.from_pretrained(ckpt, cli_overrides=["--device=cpu", "--load_vlm_weights=false"])
policy = SmolVLAPolicy.from_pretrained(ckpt, config=cfg, strict=True)
pre, post = make_pre_post_processors(cfg, str(ckpt), preprocessor_overrides={"device_processor": {"device": "cpu"}})

sim = desk_cleanup.create_simulation(match_dataset=True)
m, d = sim.model, sim.data
renderer = sim.mj.Renderer(m, height=480, width=640)
ball = d.body("blue_ball")
bgeom = m.geom("blue_ball_geom").id
pads = {m.geom("fixed_finger_pad").id, m.geom("moving_finger_pad").id}
floor = m.geom("bowl_floor").id
start_z = float(ball.xpos[2])
grip_site = d.site("gripperframe")
stream = JointTargets(sim, desk_cleanup.ZERO_RAD, desk_cleanup.RAD_PER_UNIT)
rec = np.load(r"C:\RobotArm\data\raw\desk_cleanup_episode_230.npz")["action"][100:]
log, chunk_i = [], 0
t0 = time.monotonic()
while stream.executed < steps:
    obs = observation(sim, renderer, desk_cleanup.TASK, desk_cleanup.ZERO_RAD, desk_cleanup.RAD_PER_UNIT)
    for key, name in (("observation.images.desk_view", "desk"), ("observation.images.wrist_left", "wrist")):
        Image.fromarray((obs[key].permute(1, 2, 0).numpy() * 255).astype(np.uint8)).save(
            out / f"chunk{chunk_i:02d}_{name}.jpg", quality=80)
    ti = time.monotonic()
    with torch.inference_mode():
        chunk = post(policy.predict_action_chunk(pre(obs))).squeeze(0).numpy()
    infer = time.monotonic() - ti
    targets, limited = stream.prepare(chunk)
    for k in range(min(replan or policy.config.n_action_steps, steps - stream.executed)):
        stream.apply(targets[k])
        touching = set()
        for c in d.contact[:d.ncon]:
            if bgeom in (c.geom1, c.geom2):
                touching.update((int(c.geom1), int(c.geom2)))
        log.append({"step": stream.executed, "chunk": chunk_i, "action": chunk[k].round(2).tolist(),
                    "ball_xyz": ball.xpos.round(4).tolist(), "lift_cm": round(100 * (ball.xpos[2] - start_z), 2),
                    "pads": len(pads & touching), "on_bowl_floor": floor in touching,
                    "grip_to_ball_cm": round(100 * float(np.linalg.norm(grip_site.xpos - ball.xpos)), 2),
                    "limited": bool(limited[k])})
    last = log[-1]
    n = min(replan or 50, 50)   # targets executed from this chunk
    i0 = min(stream.executed - n, len(rec) - n)
    err = float(np.abs(chunk[:n, :5] - rec[i0:i0 + n, :5]).mean())
    print(f"chunk {chunk_i:2d} infer {infer:5.1f}s step {last['step']:3d} grip% {chunk[-1, -1]:5.1f} "
          f"gripper->ball {last['grip_to_ball_cm']:5.1f}cm lift {last['lift_cm']:5.2f}cm pads {last['pads']} "
          f"| err vs recording at same step {err:5.1f}deg", flush=True)
    chunk_i += 1

lifts = [r["lift_cm"] for r in log]
summary = {"seed": seed, "replan_every": replan or policy.config.n_action_steps, "steps": stream.executed, "minutes": round((time.monotonic() - t0) / 60, 1),
           "min_gripper_to_ball_cm": min(r["grip_to_ball_cm"] for r in log),
           "max_pads_touching": max(r["pads"] for r in log),
           "steps_both_pads": sum(r["pads"] == 2 for r in log),
           "peak_lift_cm": max(lifts), "ball_end_xyz": log[-1]["ball_xyz"],
           "ball_on_bowl_floor_at_end": log[-1]["on_bowl_floor"],
           "limited_targets": sum(r["limited"] for r in log)}
(out / "steps.jsonl").write_text("\n".join(json.dumps(r) for r in log))
(out / "summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
