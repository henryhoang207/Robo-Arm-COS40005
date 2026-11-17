"""T1 (experiment 003): at frame 440 (just before the recorded close), does SmolVLA command the close with real vs sim images?"""
import os
import sys
import time
os.environ.setdefault("MUJOCO_GL", "egl")
sys.path.insert(0, "/content/RobotArm/so101sim")
import av
import numpy as np
import torch
from huggingface_hub import hf_hub_download
import desk_cleanup
from joint_targets import JointTargets

FRAME, SEEDS = 440, (0, 1, 2, 3)
CKPT = "/content/ckpt/pretrained_model"
REPO, REV = "Project-IRA/TPSoSe2026_Dataset_Full_Merged_Final_LeRobot_SO101_V1", "bf6f568e9ec218fff838fb266e161724ec4f7e2c"
VIDS = {"desk": ("videos/observation.images.desk_view/chunk-000/file-002.mp4", 601.5333333333333),
        "wrist": ("videos/observation.images.wrist_left/chunk-000/file-004.mp4", 0.0)}


def real_frame(cam):
    path = hf_hub_download(REPO, VIDS[cam][0], repo_type="dataset", revision=REV, local_dir="/content/hf")
    t = VIDS[cam][1] + FRAME / 30
    with av.open(path) as box:
        s = box.streams.video[0]
        box.seek(int((t - 1) / s.time_base), stream=s, backward=True)
        for fr in box.decode(s):
            if fr.time >= t - 1 / 60:
                return fr.to_ndarray(format="rgb24")


def sim_frames(small_look):
    sim = desk_cleanup.create_simulation(match_dataset=True)
    m = sim.model
    if small_look:   # show the 16 mm contact sphere instead of the 32.6 mm visual sphere
        m.geom_group[m.geom("blue_ball_visual").id] = 3
        m.geom_group[m.geom("blue_ball_geom").id] = 0
    stream = JointTargets(sim, desk_cleanup.ZERO_RAD, desk_cleanup.RAD_PER_UNIT)
    targets, _ = stream.prepare(ep["action"][100:FRAME])
    for t in targets:
        stream.apply(t)
    r = sim.mj.Renderer(m, height=480, width=640)
    out = {}
    for cam, name in (("desk", "overhead_camera"), ("wrist", "wrist_camera")):
        r.update_scene(sim.data, camera=name)
        out[cam] = r.render().copy()
    state = ((sim.data.qpos[sim.qids] - desk_cleanup.ZERO_RAD) / desk_cleanup.RAD_PER_UNIT).astype(np.float32)
    return out, state


def to_t(img):
    return torch.from_numpy(img).permute(2, 0, 1).float() / 255


ep = np.load("/content/RobotArm/data/raw/desk_cleanup_episode_230.npz")
rec = ep["action"][FRAME:FRAME + 50]
from lerobot.configs.policies import PreTrainedConfig
from lerobot.policies import make_pre_post_processors
from lerobot.policies.smolvla import SmolVLAPolicy
dev = "cuda"
cfg = PreTrainedConfig.from_pretrained(CKPT, cli_overrides=[f"--device={dev}", "--load_vlm_weights=false"])
policy = SmolVLAPolicy.from_pretrained(CKPT, config=cfg, strict=True).to(dev).eval()
pre, post = make_pre_post_processors(cfg, CKPT, preprocessor_overrides={"device_processor": {"device": dev}})

real = {c: real_frame(c) for c in VIDS}
big, sim_state = sim_frames(False)
small, _ = sim_frames(True)
rec_state = ep["state"][FRAME]
print(f"state at frame {FRAME}: recorded {np.round(rec_state, 1).tolist()} | sim replay {np.round(sim_state, 1).tolist()}")
print(f"recorded gripper over next 50 steps: start {rec[0, 5]:.1f}% -> min {rec[:, 5].min():.1f}% "
      f"(step of min {int(rec[:, 5].argmin())}); at k=0/20/40: {rec[[0, 20, 40], 5].round(1).tolist()}")
sets = {"A real desk + real wrist": (real["desk"], real["wrist"]),
        "B sim desk + sim wrist (32.6 mm look)": (big["desk"], big["wrist"]),
        "C sim desk + sim wrist (16 mm look)": (small["desk"], small["wrist"]),
        "D real desk + sim wrist (32.6 mm look)": (real["desk"], big["wrist"]),
        "E sim desk (32.6 mm look) + real wrist": (big["desk"], real["wrist"])}
os.makedirs("/content/out_t1", exist_ok=True)
from PIL import Image
for key, (dk, wr) in sets.items():
    Image.fromarray(np.concatenate([np.asarray(Image.fromarray(dk).resize((640, 480))), wr], 1)).save(
        f"/content/out_t1/{key[0]}_inputs.jpg", quality=85)
    mins, ks, errs = [], [], []
    for seed in SEEDS:
        torch.manual_seed(seed)
        obs = {"observation.state": torch.from_numpy(rec_state.astype(np.float32)),
               "observation.images.desk_view": to_t(dk), "observation.images.wrist_left": to_t(wr),
               "task": desk_cleanup.TASK}
        t0 = time.time()
        with torch.inference_mode():
            chunk = post(policy.predict_action_chunk(pre(obs))).squeeze(0).cpu().numpy()
        mins.append(chunk[:, 5].min())
        ks.append(chunk[[0, 20, 40], 5])
        errs.append(np.abs(chunk[:, :5] - rec[:, :5]).mean())
    print(f"{key:40s} gripper min {np.mean(mins):5.1f}% (seeds {np.round(mins, 1).tolist()}) "
          f"k=0/20/40 {np.round(np.mean(ks, 0), 1).tolist()} | joint err {np.mean(errs):4.1f} deg | "
          f"{time.time() - t0:.2f}s/pred")
