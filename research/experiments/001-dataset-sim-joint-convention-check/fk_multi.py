import csv, numpy as np, torch, gymnasium as gym, mani_skill.envs  # noqa
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EXPERIMENT_DIR.parents[1] / "results" / EXPERIMENT_DIR.name
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
rows = list(csv.DictReader(open(EXPERIMENT_DIR / "data/grasp_frames_multi_episode.csv")))
env = gym.make("PickCubeSO100-v1", obs_mode="state", sim_backend="physx_cpu", render_backend="cpu", num_envs=1); env.reset(seed=0)
u = env.unwrapped; agent = u.agent; robot = agent.robot; base = robot.pose.p[0].numpy()
def fk(q):
    robot.set_qpos(torch.tensor(q, dtype=torch.float32)[None])
    return agent.tcp_pos[0].numpy() - base, agent.finger1_tip.pose.p[0].numpy()-base, agent.finger2_tip.pose.p[0].numpy()-base
res = []
for name, off in {"M0_identity": np.zeros(5), "M1_elbow_minus_6.8deg": np.array([0,0,-6.8,0,0])}.items():
    print("==", name); print(" ep frame grip  tcp_x  tcp_y  tcp_z  reach  gap_mm")
    for r in rows:
        s = np.array([float(r[f"s{i}"]) for i in range(6)])
        q = np.concatenate([np.deg2rad(s[:5] + off), [-1.1 + np.deg2rad(s[5])]])
        tcp, t1, t2 = fk(q)
        gap = np.linalg.norm(t1 - t2) * 1000
        res.append([name, r["episode_index"], r["frame_index"], s[5], *tcp.round(4), round(float(np.hypot(*tcp[:2])),4), round(gap,1)])
        print(f" {int(r['episode_index']):2d} {int(r['frame_index']):4d} {s[5]:5.2f} {tcp[0]:+.3f} {tcp[1]:+.3f} {tcp[2]:+.3f} {np.hypot(*tcp[:2]):.3f} {gap:6.1f}")
with open(RESULTS_DIR / "fk_multi_results.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["mapping","episode","frame","grip_ds","tcp_x","tcp_y","tcp_z","reach","jaw_gap_mm"]); w.writerows(res)
