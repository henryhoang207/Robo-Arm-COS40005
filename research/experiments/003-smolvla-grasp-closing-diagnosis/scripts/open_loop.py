"""Open-loop check: SmolVLA's first chunk at the episode-230 start (sim observation) vs the recorded actions."""
import sys
from pathlib import Path
sys.path.insert(0, r"C:\RobotArm\so101sim")
import numpy as np
import torch
import desk_cleanup
from run_smolvla import observation

ckpt = Path(sys.argv[1])
ep = np.load(r"C:\RobotArm\data\raw\desk_cleanup_episode_230.npz")
rec = ep["action"][100:150]
from lerobot.configs.policies import PreTrainedConfig
from lerobot.policies import make_pre_post_processors
from lerobot.policies.smolvla import SmolVLAPolicy
cfg = PreTrainedConfig.from_pretrained(ckpt, cli_overrides=["--device=cpu", "--load_vlm_weights=false"])
policy = SmolVLAPolicy.from_pretrained(ckpt, config=cfg, strict=True)
pre, post = make_pre_post_processors(cfg, str(ckpt), preprocessor_overrides={"device_processor": {"device": "cpu"}})

sim = desk_cleanup.create_simulation(match_dataset=True)
renderer = sim.mj.Renderer(sim.model, height=480, width=640)
obs = observation(sim, renderer, desk_cleanup.TASK, desk_cleanup.ZERO_RAD, desk_cleanup.RAD_PER_UNIT)
names = ["pan", "lift", "elbow", "wflex", "wroll", "grip"]
print("sim state (dataset units):", np.round(obs["observation.state"].numpy(), 2).tolist())
print("recorded state frame 100 :", np.round(ep["state"][100], 2).tolist())
for seed in (0, 1):
    torch.manual_seed(seed)
    with torch.inference_mode():
        chunk = post(policy.predict_action_chunk(pre(dict(obs)))).squeeze(0).numpy()
    err = np.abs(chunk - rec)
    print(f"\nseed {seed}: mean |pred - recorded| per joint over 50 steps:",
          dict(zip(names, np.round(err.mean(0), 2).tolist())))
    for k in (0, 10, 25, 49):
        print(f"  step {k:2d} pred {np.round(chunk[k], 1).tolist()}  rec {np.round(rec[k], 1).tolist()}")
print("\nrecorded change over frames 100->149:", np.round(rec[-1] - rec[0], 1).tolist())
