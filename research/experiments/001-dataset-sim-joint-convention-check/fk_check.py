"""Experiment 001: FK of sampled svla_so100_pickplace episode-0 frames in the ManiSkill 3.0.1 SO100 model.
Kinematics only (set_qpos). Base frame on the table plane. Outputs TCP height/reach per frame and mapping."""
import csv, json, sys
from pathlib import Path
import numpy as np, torch, gymnasium as gym
import mani_skill.envs  # noqa: F401  (registers envs)

EXPERIMENT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EXPERIMENT_DIR.parents[1] / "results" / EXPERIMENT_DIR.name
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
rows = list(csv.DictReader(open(EXPERIMENT_DIR / "data/ep0_sampled_frames.csv")))
env = gym.make("PickCubeSO100-v1", obs_mode="state", sim_backend="physx_cpu", render_backend="cpu", num_envs=1)
env.reset(seed=0)
u = env.unwrapped; agent = u.agent; robot = agent.robot
base = robot.pose.p[0].numpy()
GRIP_CLOSED = -1.1  # ManiSkill SO100 gripper lower limit (rad); probe showed jaw-tip gap 6.6 mm here

def fk(q):
    robot.set_qpos(torch.tensor(q, dtype=torch.float32)[None])
    tcp = agent.tcp_pos[0].numpy() - base
    t1 = agent.finger1_tip.pose.p[0].numpy() - base
    t2 = agent.finger2_tip.pose.p[0].numpy() - base
    wrist = robot.links_map["Wrist_Pitch_Roll"].pose.p[0].numpy() - base
    return tcp, t1, t2, wrist

mappings = {
    "M0_identity": np.zeros(5),
    "M1_elbow_minus_6.8deg": np.array([0, 0, -6.8, 0, 0]),
}
out = []
for name, off in mappings.items():
    for r in rows:
        s = np.array([float(r[f"s{i}"]) for i in range(6)])
        arm = np.deg2rad(s[:5] + off)
        grip = GRIP_CLOSED + np.deg2rad(s[5])  # hypothesis Hg: dataset gripper = degrees opened from closed
        tcp, t1, t2, wrist = fk(np.concatenate([arm, [grip]]))
        out.append(dict(mapping=name, frame=int(r["frame_index"]), grip_ds=s[5],
                        tcp_x=tcp[0], tcp_y=tcp[1], tcp_z=tcp[2], reach=float(np.hypot(tcp[0], tcp[1])),
                        tip_fixed_z=t1[2], tip_moving_z=t2[2], jaw_gap=float(np.linalg.norm(t1 - t2)), wrist_z=wrist[2]))
with open(RESULTS_DIR / "fk_results.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader()
    for o in out: w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in o.items()})
for name in mappings:
    print("==", name)
    print(" frame  grip_ds  tcp_x   tcp_y   tcp_z  reach  tipF_z tipM_z  gap")
    for o in out:
        if o["mapping"] != name: continue
        print(f" {o['frame']:5d} {o['grip_ds']:7.2f} {o['tcp_x']:+.3f} {o['tcp_y']:+.3f} {o['tcp_z']:+.3f} {o['reach']:.3f} {o['tip_fixed_z']:+.3f} {o['tip_moving_z']:+.3f} {o['jaw_gap']:.3f}")
# gripper scale check: jaw gap vs gripper opening (Hg)
print("== jaw gap vs gripper (Hg: closed=-1.1 rad + dataset value in degrees)")
for g in [0, 5, 10, 13.88, 14.64, 20, 27.14, 35]:
    _, t1, t2, _ = fk(np.concatenate([np.zeros(5), [GRIP_CLOSED + np.deg2rad(g)]]))
    print(f"  ds_grip={g:6.2f} -> sim_rad={GRIP_CLOSED+np.deg2rad(g):+.3f} jaw_tip_gap={np.linalg.norm(t1-t2)*1000:.1f} mm")
