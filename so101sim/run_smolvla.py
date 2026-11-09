"""Run the Project-IRA SmolVLA checkpoint on the local SO-101 MuJoCo scene."""

import argparse
from contextlib import nullcontext
from pathlib import Path
import time

import numpy as np
import torch

import desk_cleanup
from engine import Simulation
from joint_targets import FPS, JointTargets


CAMERAS = {
    "observation.images.desk_view": "overhead_camera",
    "observation.images.wrist_left": "wrist_camera",
}


def observation(sim, renderer, task, zero_rad, rad_per_unit):
    state = ((sim.data.qpos[sim.qids] - zero_rad) / rad_per_unit).astype(np.float32)
    state[-1] = np.clip(state[-1], 0, 100)
    obs = {"observation.state": torch.from_numpy(state), "task": task}
    for key, camera in CAMERAS.items():
        renderer.update_scene(sim.data, camera=camera)
        image = torch.from_numpy(renderer.render().copy())
        obs[key] = image.permute(2, 0, 1).float() / 255
    return obs


def rollout(sim, renderer, viewer, policy, preprocess, postprocess, task, steps, zero_rad, rad_per_unit):
    stream = JointTargets(sim, zero_rad, rad_per_unit)
    initial_joints = sim.data.qpos[sim.qids].copy()
    clipped = 0
    while stream.executed < steps and (viewer is None or viewer.is_running()):
        obs = observation(sim, renderer, task, zero_rad, rad_per_unit)
        start_inference = time.monotonic()
        with torch.inference_mode():
            batch = preprocess(obs)
            chunk = postprocess(policy.predict_action_chunk(batch)).squeeze(0).numpy()
        if chunk.shape != (policy.config.chunk_size, len(sim.aids)) or not np.isfinite(chunk).all():
            raise RuntimeError(f"Expected a finite action chunk with six joint targets, got {chunk.shape}")

        targets, limited = stream.prepare(chunk)
        print(f"Predicted {len(chunk)} targets in {time.monotonic() - start_inference:.2f}s", flush=True)

        remaining = min(policy.config.n_action_steps, steps - stream.executed)
        for target, was_limited in zip(targets[:remaining], limited[:remaining]):
            if viewer is not None and not viewer.is_running():
                break
            start_frame = time.monotonic()
            clipped += int(was_limited)
            stream.apply(target)
            if viewer is not None:
                viewer.sync()
                time.sleep(max(0, 1 / FPS - (time.monotonic() - start_frame)))

    if not np.isfinite(sim.data.qpos).all():
        raise RuntimeError("MuJoCo returned a non-finite position")
    motion = np.max(np.abs(sim.data.qpos[sim.qids] - initial_joints))
    print(f"Applied {stream.executed} targets ({clipped} limited) over {sim.data.time - stream.start_time:.3f}s "
          f"of simulation. Largest final joint change: {motion:.3f} rad.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path, help="Checkpoint folder containing model.safetensors")
    parser.add_argument("--task", required=True, help="Natural-language task for the policy")
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    parser.add_argument("--steps", type=int, default=300, help="Number of policy targets to apply at 30 Hz")
    parser.add_argument("--viewer", action="store_true", help="Show the MuJoCo window during the rollout")
    parser.add_argument("--desk-cleanup", action=argparse.BooleanOptionalAction, default=None,
                        help="Use the episode-230 calibration (auto-detected for the matching checkpoint and task)")
    parser.add_argument("--match-dataset", action="store_true",
                        help="Use the Desk Cleanup scene with camera and visual details fitted to the recording")
    args = parser.parse_args()
    if args.steps < 1 or not args.task.strip():
        parser.error("--steps must be positive and --task must contain text")
    if args.match_dataset and args.desk_cleanup is False:
        parser.error("--match-dataset requires the Desk Cleanup scene")
    checkpoint = args.checkpoint.resolve()
    if (checkpoint / "pretrained_model").is_dir():
        checkpoint /= "pretrained_model"
    for name in ("config.json", "model.safetensors", "policy_preprocessor.json", "policy_postprocessor.json"):
        if not (checkpoint / name).is_file():
            parser.error(f"Missing {name} in {checkpoint}")

    from lerobot.configs.policies import PreTrainedConfig
    from lerobot.policies import make_pre_post_processors
    from lerobot.policies.smolvla import SmolVLAPolicy

    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA is unavailable in the current PyTorch installation")

    print(f"Loading SmolVLA on {device} from {checkpoint}", flush=True)
    config = PreTrainedConfig.from_pretrained(
        checkpoint, cli_overrides=[f"--device={device}", "--load_vlm_weights=false"]
    )
    policy = SmolVLAPolicy.from_pretrained(checkpoint, config=config, strict=True)
    preprocess, postprocess = make_pre_post_processors(
        config, str(checkpoint), preprocessor_overrides={"device_processor": {"device": device}}
    )

    use_desk_cleanup = True if args.match_dataset else args.desk_cleanup
    if use_desk_cleanup is None:
        use_desk_cleanup = desk_cleanup.matches_checkpoint_task(checkpoint, args.task)
    if use_desk_cleanup:
        appearance = "dataset-matched" if args.match_dataset else "calibrated"
        print(f"Using the {appearance} Desk Cleanup scene (episode 230).", flush=True)
        sim = desk_cleanup.create_simulation(match_dataset=args.match_dataset)
        zero_rad, rad_per_unit = desk_cleanup.ZERO_RAD, desk_cleanup.RAD_PER_UNIT
    else:
        sim = Simulation("local")
        closed, opened = sim.limits[-1]
        zero_rad = np.r_[np.zeros(5), closed]
        rad_per_unit = np.r_[np.full(5, np.pi / 180), (opened - closed) / 100]
    viewer_context = nullcontext()
    if args.viewer:
        from mujoco.viewer import launch_passive

        viewer_context = launch_passive(sim.model, sim.data)
    with viewer_context as viewer, sim.mj.Renderer(sim.model, height=480, width=640) as renderer:
        rollout(sim, renderer, viewer, policy, preprocess, postprocess, args.task, args.steps,
                zero_rad, rad_per_unit)


if __name__ == "__main__":
    main()
