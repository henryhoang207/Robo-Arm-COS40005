"""T3 (experiment 003): closed-loop SmolVLA rollouts on Colab GPU, 16 mm vs 32.6 mm ball look, with the same logging as
logged_rollout.py. Usage via env vars: LOOK=small|big, SEEDS=0,1,2, REPLAN=50."""
import json
import os
import sys
import time
from pathlib import Path
os.environ.setdefault("MUJOCO_GL", "egl")
sys.path.insert(0, "/content/RobotArm/so101sim")
import numpy as np
import torch
from PIL import Image
import desk_cleanup
from joint_targets import JointTargets
from run_smolvla import observation

CKPT = "/content/ckpt/pretrained_model"
LOOK = os.environ.get("LOOK", "small")
SEEDS = [int(s) for s in os.environ.get("SEEDS", "0,1,2").split(",")]
REPLAN = int(os.environ.get("REPLAN", "50"))
NOISE = os.environ.get("NOISE", "device")   # "cpu" = draw flow-matching noise on the CPU generator
TAG = os.environ.get("TAG", "")
STEPS = 900
from lerobot.configs.policies import PreTrainedConfig
from lerobot.policies import make_pre_post_processors
from lerobot.policies.smolvla import SmolVLAPolicy
cfg = PreTrainedConfig.from_pretrained(CKPT, cli_overrides=["--device=cuda", "--load_vlm_weights=false"])
policy = SmolVLAPolicy.from_pretrained(CKPT, config=cfg, strict=True).to("cuda").eval()
pre, post = make_pre_post_processors(cfg, CKPT, preprocessor_overrides={"device_processor": {"device": "cuda"}})
rec = np.load("/content/RobotArm/data/raw/desk_cleanup_episode_230.npz")["action"][100:]

for seed in SEEDS:
    torch.manual_seed(seed)
    out = Path(f"/content/runs/t3{TAG}-{LOOK}-noise{NOISE}-seed{seed}-replan{REPLAN}")
    out.mkdir(parents=True, exist_ok=True)
    sim = desk_cleanup.create_simulation(match_dataset=True)
    m, d = sim.model, sim.data
    if LOOK == "small":
        m.geom_group[m.geom("blue_ball_visual").id] = 3
        m.geom_group[m.geom("blue_ball_geom").id] = 0
    renderer = sim.mj.Renderer(m, height=480, width=640)
    ball, bgeom = d.body("blue_ball"), m.geom("blue_ball_geom").id
    pads = {m.geom("fixed_finger_pad").id, m.geom("moving_finger_pad").id}
    floor = m.geom("bowl_floor").id
    fp, mp = d.geom("fixed_finger_pad"), d.geom("moving_finger_pad")
    start_z = float(ball.xpos[2])
    stream = JointTargets(sim, desk_cleanup.ZERO_RAD, desk_cleanup.RAD_PER_UNIT)
    log, chunk_i, t0 = [], 0, time.time()
    while stream.executed < STEPS:
        obs = observation(sim, renderer, desk_cleanup.TASK, desk_cleanup.ZERO_RAD, desk_cleanup.RAD_PER_UNIT)
        for key in ("observation.images.desk_view", "observation.images.wrist_left"):
            # Guard against the EGL bug seen 2026-11-17: a second Renderer in one process returned pure noise.
            rough = float((obs[key][:, :, 1:] - obs[key][:, :, :-1]).abs().mean()) * 255
            if rough > 15:
                raise RuntimeError(f"{key} looks like noise (mean neighbour diff {rough:.1f}); rendering is broken")
        if chunk_i % 3 == 0:
            for key, name in (("observation.images.desk_view", "desk"), ("observation.images.wrist_left", "wrist")):
                Image.fromarray((obs[key].permute(1, 2, 0).numpy() * 255).astype(np.uint8)).save(
                    out / f"chunk{chunk_i:03d}_{name}.jpg", quality=75)
        with torch.inference_mode():
            if NOISE == "cpu":   # same draw as a CPU run: torch.normal on the CPU generator, then moved to the GPU
                noise = torch.normal(0.0, 1.0, (1, cfg.chunk_size, cfg.max_action_dim), dtype=torch.float32)
                chunk = post(policy.predict_action_chunk(pre(obs), noise=noise.to("cuda"))).squeeze(0).cpu().numpy()
            else:
                chunk = post(policy.predict_action_chunk(pre(obs))).squeeze(0).cpu().numpy()
        targets, limited = stream.prepare(chunk)
        for k in range(min(REPLAN, STEPS - stream.executed)):
            stream.apply(targets[k])
            touching = set()
            for c in d.contact[:d.ncon]:
                if bgeom in (c.geom1, c.geom2):
                    touching.update((int(c.geom1), int(c.geom2)))
            mid = (fp.xpos + mp.xpos) / 2
            log.append({"step": stream.executed, "chunk": chunk_i, "action": chunk[k].round(2).tolist(),
                        "ball_xyz": ball.xpos.round(4).tolist(), "lift_cm": round(100 * (ball.xpos[2] - start_z), 2),
                        "pads": len(pads & touching), "on_bowl_floor": floor in touching,
                        "padmid_minus_ball_cm": (100 * (mid - ball.xpos)).round(2).tolist(),
                        "limited": bool(limited[k])})
        chunk_i += 1
    near = [r for r in log if np.linalg.norm(r["padmid_minus_ball_cm"]) < 5]
    best = min(log, key=lambda r: np.linalg.norm(r["padmid_minus_ball_cm"]))
    summary = {"look": LOOK, "noise": NOISE, "seed": seed, "replan_every": REPLAN, "steps": stream.executed,
               "minutes": round((time.time() - t0) / 60, 2),
               "closest_cm": round(float(np.linalg.norm(best["padmid_minus_ball_cm"])), 2),
               "closest_step": best["step"], "closest_offset_cm_xyz": best["padmid_minus_ball_cm"],
               "min_grip_cmd_within_5cm": round(min(r["action"][5] for r in near), 1) if near else None,
               "max_pads": max(r["pads"] for r in log), "steps_both_pads": sum(r["pads"] == 2 for r in log),
               "peak_lift_cm": max(r["lift_cm"] for r in log), "in_bowl_end": log[-1]["on_bowl_floor"],
               "limited_targets": sum(r["limited"] for r in log)}
    (out / "steps.jsonl").write_text("\n".join(json.dumps(r) for r in log))
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)
