"""Estimate the real ball radius: pixel area in real desk frames vs sim render (known 16 mm radius) at the same pose."""
import sys
sys.path.insert(0, r"C:\RobotArm\so101sim")
import av
import numpy as np
from PIL import Image
import desk_cleanup
from joint_targets import JointTargets

DESK = r"C:\RobotArm\data\raw\hf\project-ira\videos\observation.images.desk_view\chunk-000\file-002.mp4"
T0 = 601.5333333333333
FRAMES = [100, 150, 200]          # ball still resting on the table, arm not covering it
OUT = sys.argv[1]


def real_frame(f):
    with av.open(DESK) as box:
        s = box.streams.video[0]
        t = T0 + f / 30
        box.seek(int((t - 1) / s.time_base), stream=s, backward=True)
        for fr in box.decode(s):
            if fr.time >= t - 1 / 60:
                return np.asarray(Image.fromarray(fr.to_ndarray(format="rgb24")).resize((640, 480), Image.LANCZOS))


ep = np.load(r"C:\RobotArm\data\raw\desk_cleanup_episode_230.npz")
sim = desk_cleanup.create_simulation(match_dataset=True)
ball_geom = sim.model.geom("blue_ball_visual").id
radius_sim = float(sim.model.geom_size[ball_geom, 0])
seg = sim.mj.Renderer(sim.model, height=480, width=640)
seg.enable_segmentation_rendering()
stream = JointTargets(sim, desk_cleanup.ZERO_RAD, desk_cleanup.RAD_PER_UNIT)
targets, _ = stream.prepare(ep["action"][100:])
results = []
f = 100
for target in [None] + list(targets):
    if target is not None:
        stream.apply(target)
        f += 1
    if f not in FRAMES:
        continue
    seg.update_scene(sim.data, camera="overhead_camera")
    ids = seg.render()[..., 0]
    smask = ids == ball_geom
    ys, xs = np.nonzero(smask)
    cy, cx = ys.mean(), xs.mean()
    img = real_frame(f).astype(int)
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    mx, mn = img.max(-1), img.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1)
    navy = sat > 0.30
    yellow = navy
    win = np.zeros_like(navy)
    y0, x0 = int(cy), int(cx)
    win[max(0, y0 - 45):y0 + 45, max(0, x0 - 60):x0 + 60] = True
    rmask = (navy | yellow) & win
    # Keep the largest blob near the window.
    from scipy import ndimage
    lab, n = ndimage.label(rmask)
    if n:
        sizes = ndimage.sum(rmask, lab, range(1, n + 1))
        rmask = lab == (1 + int(np.argmax(sizes)))
    ry, rx = np.nonzero(rmask)
    d_sim = 2 * np.sqrt(smask.sum() / np.pi)
    d_real = 2 * np.sqrt(rmask.sum() / np.pi)
    w_real, h_real = np.ptp(rx) + 1, np.ptp(ry) + 1
    w_sim, h_sim = np.ptp(xs) + 1, np.ptp(ys) + 1
    ratio = np.mean([d_real / d_sim, w_real / w_sim, h_real / h_sim])
    results.append(ratio * radius_sim)
    print(f"frame {f}: sim ball centre px=({cx:.0f},{cy:.0f}) d_sim={d_sim:.1f}px bbox {w_sim}x{h_sim}; "
          f"real centre px=({rx.mean():.0f},{ry.mean():.0f}) d_real={d_real:.1f}px bbox {w_real}x{h_real}; "
          f"-> radius {1000 * ratio * radius_sim:.1f} mm")
    crop = np.concatenate([img[max(0, y0 - 45):y0 + 45, max(0, x0 - 60):x0 + 60].astype(np.uint8),
                           (np.stack([rmask] * 3, -1)[max(0, y0 - 45):y0 + 45, max(0, x0 - 60):x0 + 60] * 255
                            ).astype(np.uint8)], 1)
    Image.fromarray(crop).resize((crop.shape[1] * 3, crop.shape[0] * 3), Image.NEAREST).save(f"{OUT}\\ball_mask_f{f}.png")
print(f"sim radius {1000 * radius_sim:.1f} mm; estimated real radius {1000 * np.mean(results):.1f} mm "
      f"(range {1000 * min(results):.1f}-{1000 * max(results):.1f})")



