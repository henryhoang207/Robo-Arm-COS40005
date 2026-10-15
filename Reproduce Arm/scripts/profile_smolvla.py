"""Time SmolVLA inference on CPU, broken down by stage (ML dry-run, Stage C).

The policy is built the way `lerobot-train` builds it for fine-tuning: input features come from the dataset
(its cameras and state), weights come from the pretrained checkpoint. Timings therefore reflect a fine-tuned
model with the dataset's camera count, not the base checkpoint's three-camera layout.

    python profile_smolvla.py --runs 5 --warmup 2 --out profile.json
    python profile_smolvla.py --threads 10          # compare CPU thread counts

Stages, in execution order for one action chunk:
    preprocess      rename, batch, tokenize task, normalise state (LeRobot processor pipeline)
    image_prep      resize + pad every camera image to 512x512
    vision          SigLIP vision encoder + connector, summed over cameras
    prefix_other    language/state embedding and prefix assembly (embed_prefix minus vision)
    vlm_prefix      one SmolVLM backbone pass over image+language+state tokens, fills the KV cache
    expert          action expert, `num_steps` flow-matching denoising steps over the chunk
    postprocess     unnormalise actions, move to CPU
"""
import argparse
import json
import platform
import resource
import subprocess
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

STAGES = ["preprocess", "image_prep", "vision", "prefix_other", "vlm_prefix", "expert", "postprocess"]


class StageTimer:
    """Accumulates wall time of wrapped instance methods into the current run's buckets."""

    def __init__(self):
        self.run = defaultdict(float)
        self.calls = defaultdict(int)

    def wrap(self, obj, method, label_fn):
        original = getattr(obj, method)

        def wrapped(*args, **kwargs):
            label = label_fn(args, kwargs)
            start = time.perf_counter()
            try:
                return original(*args, **kwargs)
            finally:
                if label:
                    self.run[label] += time.perf_counter() - start
                    self.calls[label] += 1

        setattr(obj, method, wrapped)


def cpu_name():
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor()


def git_commit(path):
    try:
        return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


def pct(values, q):
    return float(np.percentile(values, q)) if values else float("nan")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-id", default="lerobot/svla_so101_pickplace")
    parser.add_argument("--policy", default="lerobot/smolvla_base")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--threads", type=int, default=None)
    parser.add_argument("--out", type=Path, default=Path("profile.json"))
    parser.add_argument(
        "--rename-map",
        default='{"observation.images.up": "observation.images.camera1", '
                '"observation.images.side": "observation.images.camera2"}',
        help="JSON map from dataset camera keys to the pretrained policy's keys (same as lerobot-train --rename_map)",
    )
    parser.add_argument(
        "--dtype", default="native", choices=["native", "float32", "bfloat16", "float16"],
        help="cast the whole policy after loading; 'native' keeps the checkpoint's dtype. CPUs without "
             "bfloat16 instructions (no AVX512_BF16/AMX) run bfloat16 far slower than float32",
    )
    args = parser.parse_args()
    rename_map = json.loads(args.rename_map) if args.rename_map else {}

    if args.threads:
        torch.set_num_threads(args.threads)
    torch.manual_seed(0)

    from lerobot.configs.policies import PreTrainedConfig
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    from lerobot.policies.factory import make_policy, make_pre_post_processors

    t0 = time.perf_counter()
    ds = LeRobotDataset(args.repo_id)
    cfg = PreTrainedConfig.from_pretrained(args.policy)
    cfg.pretrained_path = args.policy
    cfg.device = "cpu"
    policy = make_policy(cfg, ds_meta=ds.meta, rename_map=rename_map or None)
    if args.dtype != "native":
        # SmolVLA casts activations to each layer's weight dtype, so a whole-model cast is safe.
        policy.to(getattr(torch, args.dtype))
    policy.eval()
    stats = {rename_map.get(k, k): v for k, v in ds.meta.stats.items()}
    raw_preprocessor, postprocessor = make_pre_post_processors(policy.config, dataset_stats=stats)

    def preprocessor(obs):
        # Robot/dataset camera names -> policy camera names, as lerobot-train and lerobot-record do.
        return raw_preprocessor({rename_map.get(k, k): v for k, v in obs.items()})

    load_s = time.perf_counter() - t0

    n_params = sum(p.numel() for p in policy.parameters())
    cams = [k for k in policy.config.input_features if "image" in k]
    print(f"loaded in {load_s:.1f}s | params={n_params / 1e6:.0f}M | dtype={next(policy.parameters()).dtype} | "
          f"threads={torch.get_num_threads()} | cameras={cams}")
    print(f"chunk_size={policy.config.chunk_size} num_steps={policy.config.num_steps} "
          f"image_size={policy.config.resize_imgs_with_padding} vlm_layers={policy.config.num_vlm_layers}")

    timer = StageTimer()
    model = policy.model
    timer.wrap(policy, "prepare_images", lambda a, k: "image_prep")
    timer.wrap(model.vlm_with_expert, "embed_image", lambda a, k: "vision")
    timer.wrap(model, "embed_prefix", lambda a, k: "_embed_prefix_total")
    timer.wrap(model.vlm_with_expert, "forward",
               lambda a, k: "vlm_prefix" if k.get("inputs_embeds", [None])[0] is not None else None)
    timer.wrap(model, "denoise_step", lambda a, k: "expert")

    # Spread samples across the dataset so different scenes are measured.
    indices = np.linspace(0, ds.num_frames - 1, args.warmup + args.runs).astype(int)
    runs, outputs = [], []
    for i, idx in enumerate(indices):
        sample = ds[int(idx)]
        obs = {k: v for k, v in sample.items() if k.startswith("observation.")}
        obs["task"] = sample["task"]
        timer.run, timer.calls = defaultdict(float), defaultdict(int)
        policy.reset()

        with torch.inference_mode():
            start = time.perf_counter()
            batch = preprocessor(obs)
            timer.run["preprocess"] = time.perf_counter() - start

            start = time.perf_counter()
            chunk = policy.predict_action_chunk(batch)
            model_s = time.perf_counter() - start

            start = time.perf_counter()
            actions = postprocessor(chunk)
            timer.run["postprocess"] = time.perf_counter() - start

        record = dict(timer.run)
        record["prefix_other"] = record.pop("_embed_prefix_total", 0.0) - record.get("vision", 0.0)
        record["model_total"] = model_s
        record["end_to_end"] = record["preprocess"] + model_s + record["postprocess"]
        record["calls"] = dict(timer.calls)
        phase = "warmup" if i < args.warmup else "run"
        print(f"  {phase:<6} sample {idx:>5}: end_to_end={record['end_to_end']:.2f}s "
              f"(vision {record.get('vision', 0):.2f}, vlm {record.get('vlm_prefix', 0):.2f}, "
              f"expert {record.get('expert', 0):.2f})")
        if i >= args.warmup:
            runs.append(record)
            outputs.append(actions)

    calls = runs[0]["calls"]
    summary = {}
    total_p50 = pct([r["end_to_end"] for r in runs], 50)
    print(f"\n{'stage':<14}{'p50 ms':>9}{'p95 ms':>9}{'min ms':>9}{'share':>8}  calls/chunk")
    for stage in STAGES + ["model_total", "end_to_end"]:
        vals = [r.get(stage, 0.0) * 1000 for r in runs]
        summary[stage] = {"p50_ms": pct(vals, 50), "p95_ms": pct(vals, 95), "min_ms": min(vals),
                          "max_ms": max(vals), "calls": calls.get(stage)}
        share = f"{100 * summary[stage]['p50_ms'] / (total_p50 * 1000):.0f}%" if stage in STAGES else ""
        print(f"{stage:<14}{summary[stage]['p50_ms']:>9.0f}{summary[stage]['p95_ms']:>9.0f}"
              f"{summary[stage]['min_ms']:>9.0f}{share:>8}  {calls.get(stage, '')}")

    fps = ds.fps
    chunk_motion_s = policy.config.n_action_steps / fps
    per_camera = summary["vision"]["p50_ms"] / max(calls.get("vision", 1), 1)
    per_step = summary["expert"]["p50_ms"] / max(calls.get("expert", 1), 1)
    print(f"\nper camera (vision): {per_camera:.0f} ms | per denoising step: {per_step:.0f} ms")
    print(f"inference rate: {1 / total_p50:.2f} chunks/s | one chunk = {policy.config.n_action_steps} actions "
          f"= {chunk_motion_s:.2f}s of motion at {fps} Hz")
    print(f"actions consumed while the next chunk computes (p50): {total_p50 * fps:.0f} of "
          f"{policy.config.n_action_steps} | headroom ratio chunk_motion/latency = {chunk_motion_s / total_p50:.2f}")

    stacked = torch.cat([o.reshape(-1, o.shape[-1]) for o in outputs])
    ds_actions = np.stack([np.asarray(x) for x in ds.hf_dataset["action"]])
    sanity = {
        "chunk_shape": list(outputs[0].shape),
        "finite": bool(torch.isfinite(stacked).all()),
        "pred_min": stacked.min(0).values.tolist(),
        "pred_max": stacked.max(0).values.tolist(),
        "dataset_action_min": ds_actions.min(0).tolist(),
        "dataset_action_max": ds_actions.max(0).tolist(),
    }
    print(f"output: shape={sanity['chunk_shape']} finite={sanity['finite']}")
    print("  predicted min:", np.round(sanity["pred_min"], 1).tolist())
    print("  predicted max:", np.round(sanity["pred_max"], 1).tolist())
    print("  dataset   min:", np.round(sanity["dataset_action_min"], 1).tolist())
    print("  dataset   max:", np.round(sanity["dataset_action_max"], 1).tolist())

    peak_rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print(f"peak RSS: {peak_rss_mb:.0f} MB")

    import lerobot

    result = {
        "environment": {
            "cpu": cpu_name(), "platform": platform.platform(), "python": platform.python_version(),
            "torch": torch.__version__, "threads": torch.get_num_threads(),
            "lerobot_commit": git_commit(Path(lerobot.__file__).resolve().parents[2]),
        },
        "setup": {
            "policy": args.policy, "dataset": args.repo_id, "cameras": cams, "params_m": n_params / 1e6,
            "dtype": str(next(policy.parameters()).dtype), "chunk_size": policy.config.chunk_size,
            "n_action_steps": policy.config.n_action_steps, "num_steps": policy.config.num_steps,
            "image_size": list(policy.config.resize_imgs_with_padding), "fps": fps,
            "runs": args.runs, "warmup": args.warmup, "load_s": load_s,
        },
        "summary_ms": summary,
        "derived": {"vision_per_camera_ms": per_camera, "expert_per_step_ms": per_step,
                    "chunks_per_s": 1 / total_p50, "actions_consumed_during_inference": total_p50 * fps,
                    "chunk_motion_over_latency": chunk_motion_s / total_p50, "peak_rss_mb": peak_rss_mb},
        "sanity": sanity,
        "runs": runs,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
