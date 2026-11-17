"""Fit wrist-camera focal length, radial distortion and a small mount rotation from table markers in the real video.

World marker positions come from desk_cleanup.TABLE_MARKERS (fitted earlier to the desk video). The camera pose per
frame comes from replaying the recorded actions. Real marker centres are dark blobs in the real wrist frames.
"""
import sys
sys.path.insert(0, r"C:\RobotArm\so101sim")
import av
import cv2
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot
import desk_cleanup
from joint_targets import JointTargets

WRIST = r"C:\RobotArm\data\raw\hf\project-ira\videos\observation.images.wrist_left\chunk-000\file-004.mp4"
FRAMES = list(range(560, 949, 12))
W, H = 640, 480
OUT = sys.argv[1]


def real_frames(frames):
    want = set(frames)
    got = {}
    with av.open(WRIST) as box:
        s = box.streams.video[0]
        for fr in box.decode(s):
            idx = int(round(fr.time * 30))
            if idx in want:
                got[idx] = fr.to_ndarray(format="rgb24")
            if idx > max(frames):
                break
    return got


def detect(img):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    dark = (gray < 70).astype(np.uint8)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(dark, 8)
    pts = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if 25 <= a <= 1500 and 0.3 < w / max(h, 1) < 3.5 and a > 0.35 * w * h and y + h < H - 5 and y > 3:
            pts.append(cent[i])
    return np.array(pts).reshape(-1, 2)


ep = np.load(r"C:\RobotArm\data\raw\desk_cleanup_episode_230.npz")
sim = desk_cleanup.create_simulation(match_dataset=True)
cam = sim.model.camera("wrist_camera").id
markers = np.array([[x, y, 0.0003] for x, y in desk_cleanup.TABLE_MARKERS])
stream = JointTargets(sim, desk_cleanup.ZERO_RAD, desk_cleanup.RAD_PER_UNIT)
targets, _ = stream.prepare(ep["action"][100:])
poses = {}
f = 100
for target in targets:
    stream.apply(target)
    f += 1
    if f in FRAMES:
        poses[f] = (sim.data.cam_xpos[cam].copy(), sim.data.cam_xmat[cam].reshape(3, 3).copy())

real = real_frames(FRAMES)
obs = {f: detect(real[f]) for f in FRAMES if f in real}
f_sim = float(sim.model.cam_intrinsic[cam][0]) if hasattr(sim.model, "cam_intrinsic") else 483.107
print("sim wrist camera fovy:", float(sim.model.cam_fovy[cam]), "deg")


def project(p, frame):
    fx, k1, k2, cx, cy, rx, ry, rz = p
    pos, R = poses[frame]
    Rm = R @ Rot.from_rotvec([rx, ry, rz]).as_matrix()
    c = (markers - pos) @ Rm            # camera coords: x right, y up, -z forward
    front = c[:, 2] < -0.02
    x, y = c[:, 0] / -c[:, 2], c[:, 1] / -c[:, 2]
    r2 = x * x + y * y
    d = 1 + k1 * r2 + k2 * r2 * r2
    u, v = cx + fx * x * d, cy - fx * y * d
    ok = front & (u > -50) & (u < W + 50) & (v > -50) & (v < H + 50) & (d > 0.2)
    return np.stack([u, v], 1)[ok]


def residuals(p):
    res = []
    for frame, det in obs.items():
        proj = project(p, frame)
        if len(det) == 0:
            continue
        if len(proj) == 0:
            res.extend([60.0] * len(det))
            continue
        dist = np.linalg.norm(det[:, None] - proj[None], axis=2)
        res.extend(np.minimum(dist.min(1), 60.0))      # each detection to nearest projected marker
    return np.asarray(res)


best = None
for fx0 in (250, 320, 400, 483):
    for k10 in (0.0, -0.2):
        p0 = [fx0, k10, 0.0, W / 2, H / 2, 0, 0, 0]
        sol = least_squares(residuals, p0, loss="soft_l1", f_scale=8.0,
                            bounds=([150, -0.6, -0.3, 250, 170, -0.25, -0.25, -0.25],
                                    [700, 0.3, 0.3, 390, 310, 0.25, 0.25, 0.25]))
        cost = np.median(residuals(sol.x))
        if best is None or cost < best[0]:
            best = (cost, sol.x)
cost, p = best
fx, k1, k2, cx, cy, rx, ry, rz = p
n_det = sum(len(d) for d in obs.values())
print(f"frames used {len(obs)}, marker detections {n_det}")
print(f"fit: fx={fx:.1f}px k1={k1:.3f} k2={k2:.3f} principal=({cx:.1f},{cy:.1f}) "
      f"mount rotation deg={np.degrees([rx, ry, rz]).round(1).tolist()}  median residual {cost:.1f}px")
print(f"equivalent pinhole fovy at image centre: {np.degrees(2 * np.arctan(H / 2 / fx)):.1f} deg; "
      f"horizontal {np.degrees(2 * np.arctan(W / 2 / fx)):.1f} deg")
base = np.median(residuals([f_sim, 0, 0, W / 2 + 46 if False else W / 2, H / 2, 0, 0, 0]))
print(f"(current sim intrinsics, no distortion: median residual {base:.1f}px)")
# Overlay for visual check on three frames
for frame in list(obs)[::max(1, len(obs) // 3)][:3]:
    img = real[frame].copy()
    for u, v in obs[frame]:
        cv2.circle(img, (int(u), int(v)), 6, (0, 255, 0), 2)
    for u, v in project(p, frame):
        cv2.drawMarker(img, (int(u), int(v)), (255, 0, 0), cv2.MARKER_CROSS, 14, 2)
    cv2.imwrite(f"{OUT}\\wrist_fit_f{frame}.jpg", cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
np.save(f"{OUT}\\wrist_fit_params.npy", p)
