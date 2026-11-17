"""Parity: same frame-100 sim observation + same fixed noise -> SmolVLA chunk on each device. Args: ckpt so101sim_dir devices"""
import inspect
import os
import sys
os.environ.setdefault("MUJOCO_GL", "egl")
ckpt, simdir, devices = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
sys.path.insert(0, simdir)
import numpy as np
import torch
import desk_cleanup
from run_smolvla import observation
from lerobot.configs.policies import PreTrainedConfig
from lerobot.policies import make_pre_post_processors
from lerobot.policies.smolvla import SmolVLAPolicy

print("torch", torch.__version__, "| predict_action_chunk signature:", inspect.signature(SmolVLAPolicy.predict_action_chunk))
sim = desk_cleanup.create_simulation(match_dataset=True)
r = sim.mj.Renderer(sim.model, height=480, width=640)
obs = observation(sim, r, desk_cleanup.TASK, desk_cleanup.ZERO_RAD, desk_cleanup.RAD_PER_UNIT)
img_sum = float(obs["observation.images.desk_view"].sum()), float(obs["observation.images.wrist_left"].sum())
print("image checksums (desk, wrist):", [round(x, 2) for x in img_sum])
noise = torch.from_numpy(np.random.default_rng(123).standard_normal((1, 50, 32)).astype(np.float32))
for dev in devices:
    cfg = PreTrainedConfig.from_pretrained(ckpt, cli_overrides=[f"--device={dev}", "--load_vlm_weights=false"])
    policy = SmolVLAPolicy.from_pretrained(ckpt, config=cfg, strict=True).to(dev).eval()
    pre, post = make_pre_post_processors(cfg, ckpt, preprocessor_overrides={"device_processor": {"device": dev}})
    with torch.inference_mode():
        batch = pre(dict(obs))
        try:
            out = policy.predict_action_chunk(batch, noise=noise.to(dev))
            tag = "fixed noise"
        except TypeError:
            torch.manual_seed(123)
            out = policy.predict_action_chunk(batch)
            tag = "seed 123 (noise arg unsupported)"
        chunk = post(out).squeeze(0).cpu().numpy()
    print(f"{dev} [{tag}] step0 {np.round(chunk[0], 2).tolist()}")
    print(f"{dev} step25 {np.round(chunk[25], 2).tolist()}")
    print(f"{dev} step49 {np.round(chunk[49], 2).tolist()}")
    np.save(f"parity_{dev}.npy", chunk)
