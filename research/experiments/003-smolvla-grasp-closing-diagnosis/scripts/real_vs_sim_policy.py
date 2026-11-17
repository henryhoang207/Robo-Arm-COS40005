"""Same state (frame 100), real camera frames vs sim camera frames -> SmolVLA chunk error vs recorded actions."""
import sys
from pathlib import Path
sys.path.insert(0, r"C:\RobotArm\so101sim")
import numpy as np
import torch
import desk_cleanup
from run_smolvla import observation

ckpt = Path(sys.argv[1])
ep = np.load(r"C:\RobotArm\data\raw\desk_cleanup_episode_230.npz")
real = np.load(r"C:\RobotArm\data\raw\camera_check\frame100_real.npz")
rec = ep["action"][100:150]
from lerobot.configs.policies import PreTrainedConfig
from lerobot.policies import make_pre_post_processors
from lerobot.policies.smolvla import SmolVLAPolicy
cfg = PreTrainedConfig.from_pretrained(ckpt, cli_overrides=["--device=cpu", "--load_vlm_weights=false"])
policy = SmolVLAPolicy.from_pretrained(ckpt, config=cfg, strict=True)
pre, post = make_pre_post_processors(cfg, str(ckpt), preprocessor_overrides={"device_processor": {"device": "cpu"}})

sim = desk_cleanup.create_simulation(match_dataset=True)
renderer = sim.mj.Renderer(sim.model, height=480, width=640)
sim_obs = observation(sim, renderer, desk_cleanup.TASK, desk_cleanup.ZERO_RAD, desk_cleanup.RAD_PER_UNIT)
real_obs = dict(sim_obs)
real_obs["observation.state"] = torch.from_numpy(ep["state"][100].astype(np.float32))
real_obs["observation.images.desk_view"] = torch.from_numpy(real["desk"]).permute(2, 0, 1).float() / 255
real_obs["observation.images.wrist_left"] = torch.from_numpy(real["wrist"]).permute(2, 0, 1).float() / 255
mixed = dict(real_obs)  # real desk + sim wrist, to see which camera matters
mixed["observation.images.wrist_left"] = sim_obs["observation.images.wrist_left"]
mixed2 = dict(real_obs)  # sim desk + real wrist
mixed2["observation.images.desk_view"] = sim_obs["observation.images.desk_view"]

names = ["pan", "lift", "elbow", "wflex", "wroll", "grip"]
rows = []
for label, obs in (("REAL both", real_obs), ("SIM both", sim_obs), ("real desk + sim wrist", mixed),
                   ("sim desk + real wrist", mixed2)):
    errs, ends = [], []
    for seed in range(4):
        torch.manual_seed(seed)
        with torch.inference_mode():
            chunk = post(policy.predict_action_chunk(pre(dict(obs)))).squeeze(0).numpy()
        errs.append(np.abs(chunk - rec).mean(0))
        ends.append(chunk[-1] - chunk[0])
    e = np.mean(errs, 0)
    print(f"{label:24s} mean|pred-rec| deg: {dict(zip(names, np.round(e, 1).tolist()))}  overall {e[:5].mean():.2f}")
    print(f"{'':24s} change over chunk (mean of 4 seeds): {np.round(np.mean(ends, 0), 1).tolist()}")
print(f"{'RECORDED':24s} change over chunk:                    {np.round(rec[-1] - rec[0], 1).tolist()}")
