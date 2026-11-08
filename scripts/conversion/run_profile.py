"""Integrate the staged SmolVLA split wrappers with the native profile builder.

Runs one graph/profile per process. Requires the archived training repository,
checkpoint assets, processor assets and frozen dataset cache to be available.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

from native_profiles import check_environment, convert_graph


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exporter", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--golden-fixture", type=Path, help="Reuse the passed FP32 gate's golden_validation.npz")
    parser.add_argument("--dataset-root", type=Path, help="Frozen local training dataset root for Conv calibration")
    parser.add_argument("--pad-linears-to-group32", action="store_true", help="Apply identical explicit zero-padding in both profiles")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", choices=("fp16", "int8_mixed", "int4_mixed"), required=True)
    parser.add_argument("--graph", choices=("prefix", "denoise"), required=True)
    parser.add_argument("--exceptions", type=Path, help="Frozen JSON list of extra excluded module FQNs")
    parser.add_argument("--calibration-frames", type=int, default=64)
    parser.add_argument("--check-frames", type=int, default=4)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--max-refactor-error", type=float, default=1e-4)
    args = parser.parse_args()
    if args.calibration_frames < 1 or args.check_frames < 1:
        raise ValueError("Calibration and validation smoke budgets must be positive")
    check_environment(args.threads)
    import numpy as np
    import torch

    sys.path.insert(0, str(args.repo.resolve()))
    spec = importlib.util.spec_from_file_location("staged_smol_exporter", args.exporter)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot import staged tensor wrappers")
    exporter = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = exporter
    spec.loader.exec_module(exporter)
    exporter.REPO = args.repo.resolve()
    exporter.CHECKPOINT = args.checkpoint.resolve()
    from lerobot.configs.policies import PreTrainedConfig
    from lerobot.policies.factory import get_policy_class
    from safetensors.torch import load_model

    config = PreTrainedConfig.from_pretrained(args.checkpoint)
    config.device = "cpu"
    config.load_vlm_weights = False
    policy = get_policy_class("smolvla")(config).cpu().eval()
    missing, unexpected = load_model(policy, str(args.checkpoint / "model.safetensors"), strict=True, device="cpu")
    if missing or unexpected:
        raise RuntimeError(f"Strict checkpoint loading failed: {missing=}, {unexpected=}")
    policy.float().requires_grad_(False)
    # Avoid CPU flash-SDPA decomposition producing unsupported allocation ops.
    # The existing frozen-fixture refactor gate checks this equivalent math.
    for layer in policy.modules():
        layer_config = getattr(layer, "config", None)
        if layer_config is not None and hasattr(layer_config, "_attn_implementation"):
            layer_config._attn_implementation = "eager"
    policy.config.empty_cameras = 0
    policy.config.num_steps = exporter.NUM_STEPS

    setup = None

    def get_setup():
        nonlocal setup
        if setup is None:
            setup = exporter.Setup(torch.device("cpu"))
            setup.policy_cfg.empty_cameras = 0
            setup.policy_cfg.num_steps = exporter.NUM_STEPS
            setup.cfg.dataset.image_transforms.enable = False
            setup.cfg.dataset.video_backend = "pyav"
            if args.dataset_root:
                setup.cfg.dataset.root = args.dataset_root.resolve()
        return setup

    fixture_sha256 = None
    if args.golden_fixture:
        gate_path = args.golden_fixture.parent / "parity_report.json"
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        if gate.get("status") != "passed":
            raise RuntimeError("The FP32 baseline gate must pass before native full-model conversion")
        if gate.get("dataset") != exporter.DATASET or gate.get("dataset_revision") != exporter.DATASET_REVISION:
            raise RuntimeError("Golden fixture dataset lineage differs from the staged exporter")
        validation_indices = gate["validation_indices"][:args.check_frames]
        fixture_sha256 = hashlib.sha256(args.golden_fixture.read_bytes()).hexdigest()
        with np.load(args.golden_fixture, allow_pickle=False) as fixture:
            available = sorted(int(key.split("_")[1]) for key in fixture.files
                               if key.startswith("frame_") and key.endswith("_reference"))
            if len(available) < args.check_frames:
                raise RuntimeError("Golden fixture has fewer frames than the declared smoke budget")
            inputs = [{name: fixture[f"frame_{i}_{name}"].copy() for name in
                       ("image1", "image2", "lang_tokens", "lang_mask", "state")}
                      for i in available[:args.check_frames]]
            noise = [fixture[f"frame_{i}_noise"].copy() for i in available[:args.check_frames]]
            reference = [fixture[f"frame_{i}_reference"].copy() for i in available[:args.check_frames]]
    else:
        frames, validation_indices = get_setup().load_frames("validation", args.check_frames)
        noise = exporter.make_noise(get_setup().policy_cfg, 10_000, len(frames))
        inputs = [get_setup().graph_inputs(batch) for batch, _, _ in frames]
        # Record untouched LeRobot references BEFORE the vision-forward refactor.
        with torch.inference_mode():
            reference = []
            for (batch, _, _), value in zip(frames, noise, strict=True):
                policy.reset()
                reference.append(policy.predict_action_chunk(dict(batch), noise=torch.as_tensor(value)).float().numpy())
    prefix, denoise = exporter.torch_graphs(policy)
    refactor_max = 0.0
    with torch.inference_mode():
        for record, value, expected in zip(inputs, noise, reference, strict=True):
            actual = exporter.run_graphs(prefix, denoise, record, value, torch.device("cpu"))
            actual = actual[..., :expected.shape[-1]]
            if not np.isfinite(actual).all():
                raise RuntimeError("Non-finite FP32 refactor output")
            refactor_max = max(refactor_max, float(np.abs(actual - expected).max()))
    if refactor_max > args.max_refactor_error:
        raise RuntimeError(f"FP32 host-loop refactor parity failed: {refactor_max}")

    def prefix_inputs(prepared):
        return tuple(torch.as_tensor(prepared[name]) for name in
                     ("image1", "image2", "lang_tokens", "lang_mask", "state"))

    first_inputs = prefix_inputs(inputs[0])
    calibration_indices = []
    if args.graph == "prefix":
        if args.profile == "fp16":
            calibration = []
        else:
            calibration_frames, calibration_indices = get_setup().load_frames("train", args.calibration_frames)
            calibration = [prefix_inputs(get_setup().graph_inputs(batch)) for batch, _, _ in calibration_frames]
        selected_module, example = prefix, first_inputs
    else:
        # The SmolVLA denoise boundary has Linear layers and no executed Conv2d.
        # Dynamic A8 requires no static activation calibration. The inventory
        # guard rejects an accidental future Conv2d addition without samples.
        with torch.inference_mode():
            mask, *cache = prefix(*first_inputs)
        example = (torch.as_tensor(noise[0]), torch.tensor([1.0]), mask, tuple(cache))
        selected_module, calibration = denoise, []

    exclusions = json.loads(args.exceptions.read_text(encoding="utf-8")) if args.exceptions else []
    if not isinstance(exclusions, list) or any(not isinstance(item, str) for item in exclusions):
        raise ValueError("--exceptions must contain a JSON list of module path strings")
    args.output.mkdir(parents=True, exist_ok=True)
    provenance = {
        "model": "smolvla", "checkpoint": str(args.checkpoint.resolve()),
        "dataset": exporter.DATASET, "dataset_revision": exporter.DATASET_REVISION,
        "profile": args.profile, "graph": args.graph, "num_steps": exporter.NUM_STEPS,
        "validation_smoke_indices": validation_indices, "calibration_train_indices": calibration_indices,
        "validation_noise": "CPU torch.Generator seeds 10000+i", "fp32_refactor_max_abs": refactor_max,
        "golden_fixture": str(args.golden_fixture) if args.golden_fixture else None,
        "golden_fixture_sha256": fixture_sha256,
        "shared_group32_padding_requested": args.pad_linears_to_group32,
        "extra_exclusions": exclusions, "formal_campaign_complete": False,
    }
    (args.output / f"{args.graph}_{args.profile}.provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    if args.profile == "fp16":
        from fp16_profile import convert_fp16_graph
        report = convert_fp16_graph(
            selected_module, example, output_dir=args.output, graph_name=args.graph,
            extra_exclusions=exclusions, threads=args.threads,
            pad_linears_to_group32=args.pad_linears_to_group32,
        )
    else:
        report = convert_graph(
            selected_module, example, calibration, profile=args.profile, output_dir=args.output,
            graph_name=args.graph, coverage_lock=args.output.parent / "coverage-locks" / f"{args.graph}.json",
            extra_exclusions=exclusions, threads=args.threads,
            pad_linears_to_group32=args.pad_linears_to_group32,
            require_static_conv=args.graph == "prefix",
            expected_calibration_samples=args.calibration_frames if args.graph == "prefix" else None,
        )
    print(json.dumps({"status": report["status"], "artifact": report["artifact"]}), flush=True)


if __name__ == "__main__":
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise SystemExit("Set CUDA_VISIBLE_DEVICES='' before the CPU-only conversion")
    main()
