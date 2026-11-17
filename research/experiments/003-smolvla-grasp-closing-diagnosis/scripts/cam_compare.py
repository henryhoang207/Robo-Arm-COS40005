"""Real episode-230 camera frames vs simulator frames at the same moments (sim follows the recorded actions)."""
import sys
from pathlib import Path
sys.path.insert(0, r"C:\RobotArm\so101sim")
import av
import numpy as np
from PIL import Image, ImageDraw
import desk_cleanup
from joint_targets import JointTargets

ROOT = Path(r"C:\RobotArm\data\raw")
OUT = Path(sys.argv[1])
FRAMES = [100, 250, 400, 500, 600, 700, 850]
VIDEOS = {  # camera -> (file, episode start timestamp in that file)
    "desk": (ROOT / "hf/project-ira/videos/observation.images.desk_view/chunk-000/file-002.mp4", 601.5333333333333),
    "wrist": (ROOT / "hf/project-ira/videos/observation.images.wrist_left/chunk-000/file-004.mp4", 0.0),
}


def read_frames(path, t0, frames):
    want = {f: t0 + f / 30 for f in frames}
    got = {}
    with av.open(str(path)) as box:
        stream = box.streams.video[0]
        for f, t in want.items():
            box.seek(int((t - 1.0) / stream.time_base), stream=stream, backward=True)
            for frame in box.decode(stream):
                if frame.time is not None and frame.time >= t - 1 / 60:
                    got[f] = frame.to_ndarray(format="rgb24")
                    break
    return got


real = {cam: read_frames(p, t0, FRAMES) for cam, (p, t0) in VIDEOS.items()}
print("real sizes:", {cam: next(iter(v.values())).shape for cam, v in real.items()})

ep = np.load(ROOT / "desk_cleanup_episode_230.npz")
sim = desk_cleanup.create_simulation(match_dataset=True)
renderer = sim.mj.Renderer(sim.model, height=480, width=640)
stream = JointTargets(sim, desk_cleanup.ZERO_RAD, desk_cleanup.RAD_PER_UNIT)
targets, _ = stream.prepare(ep["action"][100:])
simimg = {"desk": {}, "wrist": {}}


def grab(f):
    for cam, name in (("desk", "overhead_camera"), ("wrist", "wrist_camera")):
        renderer.update_scene(sim.data, camera=name)
        simimg[cam][f] = renderer.render().copy()


grab(100)
for f, target in enumerate(targets, start=101):
    stream.apply(target)
    if f in FRAMES:
        grab(f)

W, H = 320, 240
sheet = Image.new("RGB", (4 * W, len(FRAMES) * (H + 18) + 18), "white")
draw = ImageDraw.Draw(sheet)
for c, title in enumerate(("REAL desk_view", "SIM overhead", "REAL wrist_left", "SIM wrist")):
    draw.text((c * W + 6, 3), title, fill="black")
for r, f in enumerate(FRAMES):
    y = 18 + r * (H + 18)
    draw.text((6, y), f"frame {f}", fill="black")
    for c, img in enumerate((real["desk"][f], simimg["desk"][f], real["wrist"][f], simimg["wrist"][f])):
        sheet.paste(Image.fromarray(img).resize((W, H)), (c * W, y + 16))
sheet.save(OUT / "camera_compare_ep230.jpg", quality=88)
# Full-size frame-100 pair for a close look and for the model test.
for cam in ("desk", "wrist"):
    pair = Image.new("RGB", (1280, 480))
    pair.paste(Image.fromarray(real[cam][100]).resize((640, 480)), (0, 0))
    pair.paste(Image.fromarray(simimg[cam][100]), (640, 0))
    pair.save(OUT / f"frame100_{cam}_real_vs_sim.jpg", quality=90)
np.savez(OUT / "frame100_real.npz", desk=real["desk"][100], wrist=real["wrist"][100])
print("saved to", OUT)
