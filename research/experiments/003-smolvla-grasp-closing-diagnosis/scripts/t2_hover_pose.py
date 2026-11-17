"""T2: gripper pose at closest approach (failed rollouts) vs recorded grasp pose (replay), relative to the ball."""
import json
import sys
from pathlib import Path
sys.path.insert(0, r"C:\RobotArm\so101sim")
import numpy as np
import desk_cleanup
from joint_targets import JointTargets

RUNS = Path(r"C:\RobotArm\so101sim\runs")


def trajectory(actions, frames_wanted):
    """Stream actions from the episode start; return gripper-frame/pad-midpoint/ball/joints at wanted steps."""
    sim = desk_cleanup.create_simulation(match_dataset=True)
    d = sim.data
    stream = JointTargets(sim, desk_cleanup.ZERO_RAD, desk_cleanup.RAD_PER_UNIT)
    targets, _ = stream.prepare(np.asarray(actions))
    out = {}
    for step, target in enumerate(targets, start=1):
        stream.apply(target)
        if step in frames_wanted:
            pads = (d.geom("fixed_finger_pad").xpos + d.geom("moving_finger_pad").xpos) / 2
            q = (d.qpos[sim.qids] - desk_cleanup.ZERO_RAD) / desk_cleanup.RAD_PER_UNIT
            out[step] = {"pad_mid": pads.copy(), "ball": d.body("blue_ball").xpos.copy(), "joints": q.copy()}
    return out


ep = np.load(r"C:\RobotArm\data\raw\desk_cleanup_episode_230.npz")["action"][100:]
# Recorded grasp: the gripper closes between steps 340 and 380 (frames 440-480); use step 370.
rec = trajectory(ep, {340, 370})
print("RECORDED grasp pose (pad midpoint minus ball centre, cm) and joints (dataset units):")
for s, v in rec.items():
    off = 100 * (v["pad_mid"] - v["ball"])
    print(f"  step {s}: dx {off[0]:5.1f} dy {off[1]:5.1f} dz {off[2]:5.1f} | joints {np.round(v['joints'], 1).tolist()}")

rows = []
for run in sorted(RUNS.glob("20261117-rollout-seed[0-9]")):
    log = [json.loads(line) for line in (run / "steps.jsonl").read_text().splitlines()]
    best = min(log, key=lambda r: r["grip_to_ball_cm"])
    pose = trajectory([r["action"] for r in log], {best["step"]})[best["step"]]
    off = 100 * (pose["pad_mid"] - pose["ball"])
    dj = pose["joints"] - rec[370]["joints"]
    rows.append(off)
    print(f"{run.name[-5:]}: closest step {best['step']:3d} (grip cmd {best['action'][5]:4.1f}%): pad-mid minus ball "
          f"dx {off[0]:5.1f} dy {off[1]:5.1f} dz {off[2]:5.1f} cm | joints minus recorded grasp "
          f"{np.round(dj[:5], 1).tolist()}")
rows = np.array(rows)
r = 100 * (rec[370]["pad_mid"] - rec[370]["ball"])
print(f"MEAN over seeds: dx {rows[:, 0].mean():5.1f} dy {rows[:, 1].mean():5.1f} dz {rows[:, 2].mean():5.1f} cm "
      f"(recorded grasp: dx {r[0]:5.1f} dy {r[1]:5.1f} dz {r[2]:5.1f})")
