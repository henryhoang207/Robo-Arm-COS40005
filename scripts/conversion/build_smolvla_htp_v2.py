#!/usr/bin/env python
"""Export SmolVLA (checkpoint 100k) to ONNX, functionalize RoPE, quantize all static weight layers to W8A16 QDQ, and verify parity."""

import argparse
import json
import math
import shutil
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

REPO = Path('/mnt/data8tb/henry/robot-arm-conversion/source/SmolVLA_TrainingScript')
sys.path.insert(0, str(REPO))

import splits
from evaluate_smolvla import ActionErrors, select_indices
from train_smolvla import DATASET, DATASET_REVISION

CHECKPOINT = Path("/mnt/data8tb/henry/robot-arm-conversion/staging/results/smolvla_so101/selected_100000/pretrained_model")
PROBE = Path("/mnt/data8tb/henry/robot-arm-conversion/staging/results/smolvla_so101/deployment_probe/results_200")
NUM_STEPS = 10
OPSET = 21

# ----------------------------------------------------------------------------------------------- RoPE functionalization

def functionalize_rope_scatter_fixed(model):
    from onnx import helper, numpy_helper
    init = {t.name: t for t in model.graph.initializer}
    shapes = {v.name: [d.dim_value if d.HasField('dim_value') else None for d in v.type.tensor_type.shape.dim]
              for v in list(model.graph.input) + list(model.graph.value_info) + list(model.graph.output)}
    shapes.update({t.name: list(t.dims) for t in model.graph.initializer})
    
    producers = {name: node for node in model.graph.node for name in node.output}
    replacements = {}
    records = []
    
    def reduction(node):
        return next((a.s for a in node.attribute if a.name == 'reduction'), b'none')
        
    for second in model.graph.node:
        if second.op_type != 'ScatterND':
            continue
        first = producers.get(second.input[0])
        if first is None or first.op_type != 'ScatterND':
            continue
        if reduction(first) != b'none' or reduction(second) != b'none':
            continue
        if first.input[1] not in init or second.input[1] not in init:
            continue
        i1 = numpy_helper.to_array(init[first.input[1]])
        i2 = numpy_helper.to_array(init[second.input[1]])
        data = shapes.get(first.input[0])
        u1, u2 = shapes.get(first.input[2]), shapes.get(second.input[2])
        if not data or any(d is None or d <= 0 for d in data) or u1 is None or u2 is None:
            continue
        if i1.ndim != 2 or i2.ndim != 2 or i1.shape[1] != 1 or i2.shape[1] != 1:
            continue
        if u1 != [i1.shape[0], *data[1:]] or u2 != [i2.shape[0], *data[1:]]:
            continue
        a, b = i1[:, 0], i2[:, 0]
        if np.array_equal(a, np.arange(len(a))) and np.array_equal(b, np.arange(len(a), data[0])):
            updates = [first.input[2], second.input[2]]
        elif np.array_equal(b, np.arange(len(b))) and np.array_equal(a, np.arange(len(b), data[0])):
            updates = [second.input[2], first.input[2]]
        else:
            continue
        if len(a) + len(b) != data[0]:
            continue
            
        concat_axis = 0
        update_producers = [producers.get(name) for name in updates]
        perms = [next((list(a.ints) for a in n.attribute if a.name == 'perm'), None)
                 if n is not None and n.op_type == 'Transpose' else None for n in update_producers]
        sunk = perms[0] is not None and perms[0] == perms[1]
        if sunk:
            concat_axis = perms[0][0]
            joined = second.output[0] + '_functional_concat'
            replacements[second.name] = [
                helper.make_node('Concat', [n.input[0] for n in update_producers], [joined],
                                 name=second.name + '_functional', axis=concat_axis),
                helper.make_node('Transpose', [joined], list(second.output),
                                 name=second.name + '_restore_layout', perm=perms[0])]
        else:
            replacements[second.name] = [helper.make_node('Concat', updates, list(second.output),
                                                         name=second.name + '_functional', axis=0)]
        records.append({'first': first.name, 'second': second.name, 'shape': data,
                        'update_shapes': [u1, u2], 'replacement_inputs': updates,
                        'concat_axis_before_transpose': concat_axis, 'transpose_sunk': sunk})
                        
    if not records:
        print("Warning: No scatter-write pairs found to replace.")
        return model, {'pairs': [], 'pair_count': 0, 'remaining_scatter_nd': 0}
        
    nodes = [replacement for n in model.graph.node for replacement in replacements.get(n.name, [n])]
    needed = {o.name for o in model.graph.output}
    kept = []
    for node in reversed(nodes):
        if any(o in needed for o in node.output):
            kept.append(node)
            needed.update(i for i in node.input if i)
    kept.reverse()
    removed = Counter(n.op_type for n in model.graph.node)
    removed.subtract(Counter(n.op_type for n in kept))
    del model.graph.node[:]
    model.graph.node.extend(kept)
    inits = [t for t in model.graph.initializer if t.name in needed]
    del model.graph.initializer[:]
    model.graph.initializer.extend(inits)
    live = needed | {o for n in kept for o in n.output}
    infos = [v for v in model.graph.value_info if v.name in live]
    del model.graph.value_info[:]
    model.graph.value_info.extend(infos)
    remaining = sum(n.op_type == 'ScatterND' for n in kept)
    if remaining:
        raise RuntimeError(f'{remaining} unmatched ScatterND nodes remain; refusing partial rewrite')
    return model, {'pairs': records, 'pair_count': len(records),
                   'operator_count_delta_removed_minus_added': dict(removed),
                   'remaining_scatter_nd': remaining}

# ----------------------------------------------------------------------------------------------- graphs

def full_image_position_embeddings(embeddings):
    def forward(pixel_values, patch_attention_mask=None):
        patches = embeddings.patch_embedding(pixel_values).flatten(2).transpose(1, 2)
        return patches + embeddings.position_embedding.weight[None, :patches.shape[1]]
    embeddings.forward = forward

def residual(layer, att_out, x):
    dtype = layer.self_attn.o_proj.weight.dtype
    return (layer.self_attn.o_proj(att_out.to(dtype)) + x).to(dtype)

class PrefixGraph(nn.Module):
    def __init__(self, policy):
        super().__init__()
        self.model = policy.model
        self.width, self.height = policy.config.resize_imgs_with_padding
        self.max_state_dim = policy.config.max_state_dim
        self.self_attn_every = policy.config.self_attn_every_n_layers

    def forward(self, image1, image2, lang_tokens, lang_mask, state):
        from lerobot.policies.common.vla_utils import make_att_2d_masks, resize_with_pad
        from lerobot.policies.smolvla.smolvlm_with_expert import apply_rope

        vlm_expert = self.model.vlm_with_expert
        embs, pads = [], []
        for img in (image1, image2):
            img = resize_with_pad(img, self.height, self.width, pad_value=0) * 2.0 - 1.0
            emb = vlm_expert.embed_image(img)
            embs.append(emb * torch.tensor(emb.shape[-1] ** 0.5, dtype=emb.dtype, device=emb.device))
            pads.append(torch.ones(emb.shape[:2], dtype=torch.bool, device=emb.device))
        lang = vlm_expert.embed_language_tokens(lang_tokens)
        embs.append(lang * math.sqrt(lang.shape[-1]))
        pads.append(lang_mask)
        embs.append(self.model.state_proj(F.pad(state, (0, self.max_state_dim - state.shape[-1])))[:, None])
        pads.append(torch.ones(1, 1, dtype=torch.bool, device=state.device))
        x = torch.cat(embs, dim=1)
        pad_mask = torch.cat(pads, dim=1)
        att = torch.zeros_like(pad_mask)
        att[:, -1] = True
        att_2d = make_att_2d_masks(pad_mask, att)
        position_ids = torch.cumsum(pad_mask, dim=1) - 1

        head_dim = vlm_expert.vlm.config.text_config.head_dim
        vlm_layers = vlm_expert.get_vlm_model().text_model.layers
        kv = []
        for i, layer in enumerate(vlm_layers):
            h = layer.input_layernorm(x).to(layer.self_attn.q_proj.weight.dtype)
            shape = (*h.shape[:-1], -1, layer.self_attn.head_dim)
            q = apply_rope(layer.self_attn.q_proj(h).view(shape), position_ids)
            k = apply_rope(layer.self_attn.k_proj(h).view(shape), position_ids)
            v = layer.self_attn.v_proj(h).view(shape)
            if i % self.self_attn_every == 0:
                kv += [k, v]
            else:
                expert = vlm_expert.lm_expert.layers[i].self_attn
                dtype = expert.k_proj.weight.dtype
                kv += [expert.k_proj(k.reshape(*k.shape[:2], -1).to(dtype)).view(*k.shape[:2], -1, expert.head_dim),
                       expert.v_proj(v.reshape(*v.shape[:2], -1).to(dtype)).view(*v.shape[:2], -1, expert.head_dim)]
            if i == len(vlm_layers) - 1:
                break
            att_out = vlm_expert.eager_attention_forward(att_2d, x.shape[0], head_dim, q, k, v)
            out = residual(layer, att_out, x)
            x = layer.mlp(layer.post_attention_layernorm(out)) + out
        return (pad_mask, *kv)

class DenoiseGraph(nn.Module):
    def __init__(self, policy):
        super().__init__()
        self.model = policy.model
        cfg = policy.config
        self.chunk_size = cfg.chunk_size
        self.self_attn_every = cfg.self_attn_every_n_layers
        width = self.model.vlm_with_expert.expert_hidden_size
        fraction = torch.linspace(0.0, 1.0, width // 2, dtype=torch.float64)
        period = cfg.min_period * (cfg.max_period / cfg.min_period) ** fraction
        self.register_buffer("time_freq", (2 * math.pi / period).float(), persistent=False)

    def forward(self, x_t, t, prefix_mask, kv):
        from lerobot.policies.smolvla.smolvlm_with_expert import apply_rope

        m = self.model
        vlm_expert = m.vlm_with_expert
        batch = x_t.shape[0]
        angle = self.time_freq[None, :] * t[:, None]
        time_emb = torch.cat([torch.sin(angle), torch.cos(angle)], dim=1)
        action_emb = m.action_in_proj(x_t)
        x = torch.cat([action_emb, time_emb[:, None, :].expand_as(action_emb)], dim=2)
        x = m.action_time_mlp_out(F.silu(m.action_time_mlp_in(x)))

        steps = torch.arange(self.chunk_size, device=x_t.device)[None, :]
        abs_pos = prefix_mask.sum(dim=-1, keepdim=True) + steps
        prefix_2d = prefix_mask[:, None, :].expand(batch, self.chunk_size, prefix_mask.shape[1])
        causal = (steps[:, None, :] <= steps[:, :, None]).expand(batch, -1, -1)
        self_mask = torch.cat([prefix_2d, causal], dim=2)

        head_dim = vlm_expert.vlm.config.text_config.head_dim
        for i, layer in enumerate(vlm_expert.lm_expert.layers):
            h = layer.input_layernorm(x).to(layer.self_attn.q_proj.weight.dtype)
            shape = (*h.shape[:-1], -1, layer.self_attn.head_dim)
            q = layer.self_attn.q_proj(h).view(shape)
            if i % self.self_attn_every == 0:
                q = apply_rope(q, abs_pos)
                k = apply_rope(layer.self_attn.k_proj(h).view(shape), abs_pos)
                v = layer.self_attn.v_proj(h).view(shape)
                att_out = vlm_expert.eager_attention_forward(
                    self_mask, batch, head_dim, q, torch.cat([kv[2 * i], k], 1), torch.cat([kv[2 * i + 1], v], 1))
            else:
                q = apply_rope(q, steps.expand(batch, -1))
                att_out = vlm_expert.eager_attention_forward(prefix_2d, batch, head_dim, q, kv[2 * i], kv[2 * i + 1])
            out = residual(layer, att_out, x)
            x = layer.mlp(layer.post_attention_layernorm(out)) + out
        return m.action_out_proj(vlm_expert.lm_expert.norm(x).to(m.action_out_proj.weight.dtype))

def kv_names(num_layers):
    return [f"{kind}{i}" for i in range(num_layers) for kind in ("k", "v")]

def euler(denoise, x, num_steps=NUM_STEPS):
    dt = -1.0 / num_steps
    for step in range(num_steps):
        x = x + dt * denoise(x, np.float32(1.0 + step * dt))
    return x

# ----------------------------------------------------------------------------------------------- data

class Setup:
    def __init__(self, device):
        from lerobot.configs.policies import PreTrainedConfig
        from lerobot.configs.train import TrainPipelineConfig
        from lerobot.policies import make_pre_post_processors

        self.device = device
        self.split = splits.load(REPO / "splits.json", DATASET, DATASET_REVISION)
        self.cfg = TrainPipelineConfig.from_pretrained(CHECKPOINT)
        self.policy_cfg = PreTrainedConfig.from_pretrained(CHECKPOINT)
        self.policy_cfg.device = str(device)
        self.cfg.policy = self.policy_cfg
        self.cfg.dataset.image_transforms.enable = False
        overrides = {"device_processor": {"device": str(device)}}
        if self.cfg.rename_map:
            overrides["rename_observations_processor"] = {"rename_map": self.cfg.rename_map}
        self.preprocessor, self.postprocessor = make_pre_post_processors(
            policy_cfg=self.policy_cfg, pretrained_path=str(CHECKPOINT), preprocessor_overrides=overrides)
        self.cameras = [key for key in self.policy_cfg.image_features if "empty_camera" not in key][:2]

    def load_policy(self):
        from lerobot.configs.policies import PreTrainedConfig
        from lerobot.policies.factory import get_policy_class

        config = PreTrainedConfig.from_pretrained(CHECKPOINT)
        config.device = str(self.device)
        policy = get_policy_class("smolvla").from_pretrained(CHECKPOINT, config=config).to(self.device).eval()
        policy.float()
        policy.config.empty_cameras = 0
        policy.config.num_steps = NUM_STEPS
        return policy

    def load_frames(self, partition, budget):
        from torch.utils.data import DataLoader, Subset
        from lerobot.datasets.factory import make_dataset
        from lerobot.utils.collate import lerobot_collate_fn

        self.cfg.dataset.episodes = self.split[partition]["episodes"]
        dataset = make_dataset(self.cfg)
        indices = select_indices(dataset, budget)
        loader = DataLoader(Subset(dataset, indices), batch_size=1, num_workers=0,
                            collate_fn=lerobot_collate_fn if dataset.meta.has_language_columns else None)
        frames = []
        for raw in loader:
            target = raw["action"].cpu().numpy().copy()
            valid = (~raw["action_is_pad"].bool()).cpu().numpy() if "action_is_pad" in raw \
                else np.ones(target.shape[:-1], dtype=bool)
            for key in dataset.meta.camera_keys:
                if key in raw and raw[key].dtype == torch.uint8:
                    raw[key] = raw[key].float() / 255.0
            batch = self.preprocessor(raw)
            frames.append(({k: v for k, v in batch.items() if k != "action"}, target, valid))
        return frames, indices

    def graph_inputs(self, batch):
        from lerobot.utils.constants import OBS_LANGUAGE_ATTENTION_MASK, OBS_LANGUAGE_TOKENS, OBS_STATE

        def last(x):
            return x[:, -1] if x.ndim == 5 else x
        return {
            "image1": last(batch[self.cameras[0]]).float().cpu().numpy(),
            "image2": last(batch[self.cameras[1]]).float().cpu().numpy(),
            "lang_tokens": batch[OBS_LANGUAGE_TOKENS].long().cpu().numpy(),
            "lang_mask": batch[OBS_LANGUAGE_ATTENTION_MASK].bool().cpu().numpy(),
            "state": (batch[OBS_STATE][:, -1] if batch[OBS_STATE].ndim > 2 else batch[OBS_STATE]).float().cpu().numpy(),
        }

    def to_dataset_units(self, actions):
        dim = self.policy_cfg.action_feature.shape[0]
        chunk = torch.as_tensor(np.asarray(actions)[..., :dim], device=self.device)
        return self.postprocessor(chunk).float().cpu().numpy()

def make_noise(policy_cfg, seed, count):
    shape = (1, policy_cfg.chunk_size, policy_cfg.max_action_dim)
    return [torch.randn(shape, generator=torch.Generator().manual_seed(seed + i)).numpy() for i in range(count)]

class OnnxPolicy:
    def __init__(self, prefix_path, denoise_path, threads=0):
        import onnxruntime as ort

        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.log_severity_level = 3
        self.prefix = ort.InferenceSession(str(prefix_path), options, providers=["CPUExecutionProvider"])
        self.denoise = ort.InferenceSession(str(denoise_path), options, providers=["CPUExecutionProvider"])
        self.kv_names = [o.name for o in self.prefix.get_outputs()][1:]

    def run_prefix(self, inputs):
        out = self.prefix.run(None, inputs)
        return out[0], dict(zip(self.kv_names, out[1:], strict=True))

    def __call__(self, inputs, noise):
        prefix_mask, kv = self.run_prefix(inputs)
        return euler(lambda x, t: self.denoise.run(
            None, {"x_t": x, "t": np.array([t], np.float32), "prefix_mask": prefix_mask, **kv})[0], noise)

# ----------------------------------------------------------------------------------------------- stages

def torch_graphs(policy):
    full_image_position_embeddings(policy.model.vlm_with_expert.get_vlm_model().vision_model.embeddings)
    device = next(policy.parameters()).device
    return PrefixGraph(policy).eval(), DenoiseGraph(policy).to(device).eval()

def run_graphs(prefix, denoise, inputs, noise, device):
    with torch.inference_mode():
        args = [torch.as_tensor(inputs[k], device=device) for k in ("image1", "image2", "lang_tokens", "lang_mask", "state")]
        prefix_mask, *kv = prefix(*args)
        return euler(lambda x, t: denoise(x, torch.tensor([t], device=device), prefix_mask, kv),
                     torch.as_tensor(noise, device=device)).cpu().numpy()

def export(args, setup):
    import onnx
    from onnx import shape_inference

    out = args.output
    policy = setup.load_policy()
    frames, _ = setup.load_frames("validation", args.check_frames)
    noise = make_noise(setup.policy_cfg, 10_000, len(frames))

    reference = []
    with torch.inference_mode():
        for (batch, _, _), n in zip(frames, noise, strict=True):
            policy.reset()
            reference.append(policy.predict_action_chunk(dict(batch), noise=torch.as_tensor(n, device=setup.device))
                             .float().cpu().numpy())
    prefix, denoise = torch_graphs(policy)
    dim = setup.policy_cfg.action_feature.shape[0]
    for i, ((batch, _, _), n) in enumerate(zip(frames, noise, strict=True)):
        mine = run_graphs(prefix, denoise, setup.graph_inputs(batch), n, setup.device)[..., :dim]
        print(f"refactor check frame {i}: max |graphs - LeRobot| = {np.abs(mine - reference[i]).max():.2e} "
              f"(normalized units)", flush=True)

    policy.to("cpu")
    prefix, denoise = prefix.cpu(), denoise.cpu()
    inputs = setup.graph_inputs(frames[0][0])
    example = tuple(torch.as_tensor(inputs[k]) for k in ("image1", "image2", "lang_tokens", "lang_mask", "state"))
    num_layers = len(policy.model.vlm_with_expert.lm_expert.layers)
    names = kv_names(num_layers)
    with torch.inference_mode():
        prefix_mask, *kv = prefix(*example)
    started = time.perf_counter()
    
    # 1. Export prefix
    raw_prefix_path = out / "prefix_fp32_raw.onnx"
    torch.onnx.export(prefix, example, raw_prefix_path, dynamo=True, opset_version=OPSET,
                      input_names=list(inputs), output_names=["prefix_mask", *names], external_data=True)
    
    # 2. Export denoise
    raw_denoise_path = out / "denoise_fp32_raw.onnx"
    x_t = torch.as_tensor(noise[0])
    torch.onnx.export(denoise, (x_t, torch.tensor([1.0]), prefix_mask, tuple(kv)), raw_denoise_path,
                      dynamo=True, opset_version=OPSET, input_names=["x_t", "t", "prefix_mask", *names],
                      output_names=["v_t"], external_data=True)
    print(f"Exported raw graphs in {time.perf_counter() - started:.0f} s", flush=True)

    # 3. Functionalize RoPE on both graphs (eliminates all 110 ScatterND nodes)
    for name, p_in in [("prefix", raw_prefix_path), ("denoise", raw_denoise_path)]:
        print(f"Functionalizing RoPE for {name}...", flush=True)
        m = onnx.load(str(p_in), load_external_data=True)
        m = shape_inference.infer_shapes(m)
        m_func, rec = functionalize_rope_scatter_fixed(m)
        p_out = out / f"{name}_fp32.onnx"
        onnx.save(m_func, str(p_out), save_as_external_data=True, all_tensors_to_one_file=True,
                  location=f"{name}_fp32.onnx.data")
        print(f"{name}: replaced {rec['pair_count']} ScatterND pairs, 0 remaining. Saved {p_out}", flush=True)
        # Clean up raw files
        for f in out.glob(f"{name}_fp32_raw.onnx*"):
            f.unlink()

    runner = OnnxPolicy(out / "prefix_fp32.onnx", out / "denoise_fp32.onnx")
    for i, ((batch, _, _), n) in enumerate(zip(frames, noise, strict=True)):
        onnx_out = runner(setup.graph_inputs(batch), n)[..., :dim]
        print(f"Functional RoPE ONNX check frame {i}: max |ORT fp32 - LeRobot| = {np.abs(onnx_out - reference[i]).max():.2e}",
              flush=True)

    stats = {}
    for name in ("preprocessor_step_5_normalizer", "postprocessor_step_0_unnormalizer"):
        from safetensors.torch import load_file
        for key, value in load_file(CHECKPOINT / f"policy_{name}_processor.safetensors").items():
            if key.startswith(("observation.state.", "action.")) and key.rsplit(".", 1)[1] in ("mean", "std"):
                stats[key] = value.tolist()
    io = {
        "checkpoint": str(CHECKPOINT),
        "cameras": {"image1": setup.cameras[0], "image2": setup.cameras[1]},
        "dataset_rename_map": setup.cfg.rename_map,
        "prefix_inputs": {k: {"shape": list(v.shape), "dtype": str(v.dtype)} for k, v in inputs.items()},
        "denoise_inputs": {"x_t": [1, setup.policy_cfg.chunk_size, setup.policy_cfg.max_action_dim], "t": [1],
                           "prefix_mask": list(prefix_mask.shape), "kv": list(kv[0].shape)},
        "normalization": stats,
    }
    (out / "io_spec.json").write_text(json.dumps(io, indent=2), encoding="utf-8")


def select_nodes(model_path):
    """Weight MatMul/Gemm/Conv nodes: ALL static weights are selected for W8A16 QDQ quantization.
    Only activation matmuls (dynamic Q*K^T and Attn*V) are skipped."""
    import onnx

    model = onnx.load(str(model_path), load_external_data=False)
    initializers = {init.name: init for init in model.graph.initializer}
    selected, skipped = [], {"activation_matmul": 0}
    for node in model.graph.node:
        if node.op_type not in ("MatMul", "Gemm", "Conv"):
            continue
        weight = node.input[1]
        if weight not in initializers:
            skipped["activation_matmul"] += 1
            continue
        selected.append(node.name)
    return selected, skipped


class Reader:
    def __init__(self, generator):
        self.generator = generator

    def get_next(self):
        return next(self.generator, None)


def calibration_inputs(setup, out, calibration_frames):
    frames, indices = setup.load_frames("train", calibration_frames)
    calibration = [setup.graph_inputs(batch) for batch, _, _ in frames]
    noise = make_noise(setup.policy_cfg, 30_000, len(frames))
    runner = OnnxPolicy(out / "prefix_fp32.onnx", out / "denoise_fp32.onnx")

    def denoise_inputs():
        for inputs, n in zip(calibration, noise, strict=True):
            prefix_mask, kv = runner.run_prefix(inputs)
            x = n
            for step in range(NUM_STEPS):
                feed = {"x_t": x, "t": np.array([1.0 + step * (-1.0 / NUM_STEPS)], np.float32), "prefix_mask": prefix_mask, **kv}
                yield feed
                x = x + (-1.0 / NUM_STEPS) * runner.denoise.run(None, feed)[0]

    return {"prefix": lambda: iter(calibration), "denoise": denoise_inputs}, indices


def qdq_quantize(setup, out, case, calibration_frames, weight_type):
    from onnxruntime.quantization import CalibrationMethod, QuantFormat, QuantType, quantize_static
    from onnxruntime.quantization.shape_inference import quant_pre_process

    data, indices = calibration_inputs(setup, out, calibration_frames)
    report = {"calibration_frames": len(indices), "calibration_train_indices": indices}
    scratch = Path(tempfile.mkdtemp(prefix="smolvla_onnx_"))
    for name in ("prefix", "denoise"):
        started = time.perf_counter()
        pre = scratch / f"{name}_fp32_pre.onnx"
        quant_pre_process(str(out / f"{name}_fp32.onnx"), str(pre), skip_optimization=False,
                          save_as_external_data=True, external_data_location=f"{pre.name}.data")
        nodes, skipped = select_nodes(pre)
        print(f"{name}: quantizing {len(nodes)} weight MatMul/Gemm/Conv nodes (all static weights); skipped {skipped}", flush=True)
        extra = {
            "ActivationSymmetric": False,
            "WeightSymmetric": True,
            "QDQOpTypePerChannelSupportToAxis": {"MatMul": 1, "Gemm": 1}
        }
        quantize_static(
            str(pre), str(out / f"{name}_{case}.onnx"), Reader(data[name]()),
            quant_format=QuantFormat.QDQ, op_types_to_quantize=["MatMul", "Gemm", "Conv"], nodes_to_quantize=nodes,
            per_channel=True, activation_type=QuantType.QUInt16, weight_type=weight_type,
            calibrate_method=CalibrationMethod.MinMax, use_external_data_format=True, extra_options=extra)
        import onnx
        graph = onnx.load(str(pre), load_external_data=False).graph
        selected = set(nodes)
        distinct = len({node.input[1] for node in graph.node if node.name in selected})
        report[name] = {"quantized_nodes": len(nodes), "distinct_weights": distinct,
                        "skipped": skipped, "seconds": round(time.perf_counter() - started)}
        print(f"{name}: quantized in {report[name]['seconds']} s", flush=True)
    shutil.rmtree(scratch)
    return report


def quantize(args, setup):
    from onnxruntime.quantization import QuantType

    report = qdq_quantize(setup, args.output, "w8a16", args.calibration_frames, QuantType.QInt8)
    (args.output / "quantization.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def compare(args, setup):
    out = args.output
    frames, indices = setup.load_frames("validation", args.eval_frames)
    noise = make_noise(setup.policy_cfg, 10_000, len(frames))
    valid = np.concatenate([v for _, _, v in frames])

    predictions, latency = {}, {}
    policy = setup.load_policy()
    started = time.perf_counter()
    chunks = []
    with torch.inference_mode():
        for (batch, _, _), n in zip(frames, noise, strict=True):
            policy.reset()
            chunk = policy.predict_action_chunk(dict(batch), noise=torch.as_tensor(n, device=setup.device))
            chunks.append(setup.to_dataset_units(chunk.float().cpu().numpy()))
    predictions["pytorch_fp32"] = np.concatenate(chunks)
    print(f"pytorch_fp32: {time.perf_counter() - started:.0f} s", flush=True)
    del policy
    torch.cuda.empty_cache()

    variants = {"onnx_fp32": ("prefix_fp32", "denoise_fp32"),
                "onnx_w8a16": ("prefix_w8a16", "denoise_w8a16")}
    for name, (prefix_file, denoise_file) in variants.items():
        runner = OnnxPolicy(out / f"{prefix_file}.onnx", out / f"{denoise_file}.onnx")
        started, chunks, times = time.perf_counter(), [], []
        for (batch, _, _), n in zip(frames, noise, strict=True):
            inputs = setup.graph_inputs(batch)
            t0 = time.perf_counter()
            actions = runner(inputs, n)
            times.append(time.perf_counter() - t0)
            chunks.append(setup.to_dataset_units(actions))
        predictions[name] = np.concatenate(chunks)
        latency[name] = float(np.median(times) * 1000)
        print(f"{name}: {time.perf_counter() - started:.0f} s, CPU p50 {latency[name]:.0f} ms/chunk", flush=True)

    probe = np.load(PROBE / "predictions.npz")
    probe_indices = json.loads((PROBE / "summary.json").read_text())["validation_indices"]
    if probe_indices == indices:
        for key in ("bf16_as_trained", "fp32", "w8a16"):
            predictions[f"probe_{key}"] = probe[key]

    def deviation(pred, ref):
        diff = np.abs(pred.astype(np.float64) - ref.astype(np.float64))[valid]
        return {"mae": float(diff.mean()), "p99": float(np.percentile(diff, 99)), "max": float(diff.max()),
                "mae_per_joint": diff.mean(axis=0).tolist()}

    def ground_truth(pred):
        errors = ActionErrors()
        for i, (_, target, v) in enumerate(frames):
            errors.update(pred[i:i + 1], target, v)
        result = errors.result()
        return {"mae": result["mae"], "rmse": result["rmse"], "mae_per_joint": result["mae_per_joint"]}

    refs = [r for r in ("pytorch_fp32", "probe_bf16_as_trained", "probe_w8a16") if r in predictions]
    results = {name: {**{f"deviation_vs_{r}": deviation(pred, predictions[r]) for r in refs},
                      "ground_truth": ground_truth(pred),
                      **({"cpu_latency_p50_ms": latency[name]} if name in latency else {})}
               for name, pred in predictions.items()}
    sizes = {p.name: p.stat().st_size for p in sorted(out.glob("*.onnx*"))}
    summary = {"checkpoint": str(CHECKPOINT), "eval_frames": len(frames), "validation_indices": indices,
               "file_bytes": sizes, "variants": results}
    (out / f"comparison{args.tag}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    np.savez_compressed(out / f"predictions{args.tag}.npz", valid=valid, **predictions)

    header = "".join(f"{'vs ' + r.replace('probe_', 'p:'):>22}" for r in refs)
    print(f"\n{'variant':<26}{header}{'GT MAE':>9}{'CPU ms':>8}")
    for name, entry in results.items():
        cols = "".join(f"{entry[f'deviation_vs_{r}']['mae']:>10.4f} /{entry[f'deviation_vs_{r}']['max']:>9.3f}"
                       for r in refs)
        ms = f"{entry['cpu_latency_p50_ms']:.0f}" if "cpu_latency_p50_ms" in entry else ""
        print(f"{name:<26}{cols}{entry['ground_truth']['mae']:>9.3f}{ms:>8}")
    print("(deviation columns: MAE / max)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("stages", nargs="+", choices=["export", "quantize", "compare"])
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--check-frames", type=int, default=4)
    parser.add_argument("--calibration-frames", type=int, default=64)
    parser.add_argument("--eval-frames", type=int, default=200)
    parser.add_argument("--tag", default="", help="suffix for the comparison output files")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
    setup = Setup(torch.device("cuda"))
    for stage in args.stages:
        started = time.perf_counter()
        print(f"=== {stage}", flush=True)
        {"export": export, "quantize": quantize, "compare": compare}[stage](args, setup)
        print(f"=== {stage} done in {time.perf_counter() - started:.0f} s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
