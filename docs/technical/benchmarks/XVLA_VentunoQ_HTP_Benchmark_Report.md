# X-VLA SO-101 checkpoint + export bundle

Fine-tuned X-VLA (100k steps, SO-101) plus the exported denoising core and everything needed to wire it up. `SHA256SUMS` covers every file.

## Contents

| Path | What |
|---|---|
| `checkpoint/pretrained_model/` | Full PyTorch policy: `model.safetensors` (3.5 GB), `config.json`, `train_config.json`, and pre/post-processor configs with their normalization stats. **Start here for MuJoCo.** |
| `onnx/fp32/xvla_denoise_core_fp32_rank4.onnx` (+ `.data`) | FP32 denoising core (24 transformer layers). Matches PyTorch to 1.4e-5°. Best choice for simulation. |
| `onnx/w8a16_v4/xvla_denoise_core_w8a16_htp_v4.onnx` (+ `.data`) | W8A16 QDQ core, tuned for the Qualcomm Hexagon NPU (VENTUNO Q). Same graph as `xvla_probe_qdq_lnw8u.onnx` (identical weights; only the internal data-file name differs). Host MAE vs PyTorch: 0.034°. |
| `host/xvla_io_projector_weights.npz` | Weights for everything outside the core: action encoder/decoder (per domain), soft prompts, VLM and aux-visual projections, positional embeddings. |
| `host/xvla_htp_audit_runner.py` | Working reference: `XVLAHostProjector` (NumPy `project_in` / `project_out_20`) and the full 10-step rollout around the ONNX core. |
| `host/xvla_ref_bundle_val20.npz`, `host/xvla_ref_stepwise.npz` | 20 validation frames (precomputed prefix contexts, noise, proprio, PyTorch predictions, ground truth, action mean/std) for checking your loop. |
| `scripts/export_xvla_core_clean.py` | How the FP32 core was exported from the checkpoint. |
| `scripts/build_xvla_reference_and_parity.py` | Full host pipeline from the checkpoint: VLM forward, `project_prefix`, the rollout, and the reference bundle. |
| `scripts/07_build_qdq_htp.py`, `xvla_common.py`, `01_make_calib_feeds.py`, `03_eval_host.py` | W8A16/W4A16 quantization recipe, calibration and host evaluation. These use hard-coded server paths; read them as reference. |

## What the ONNX core does (and does not do)

The core is only the transformer: `x` [1,50,1024] and `context` [1,232,1024] go in, and `h_norm` [1,50,1024] comes out. The rest runs outside it:

1. **Prefix, once per observation.** Images and the instruction go through the VLM in PyTorch (`policy.model.forward_vlm(input_ids, image_input, image_mask)`). That gives `vlm_features` and `aux_visual_inputs`. **The VLM is not exported.** It lives in the checkpoint.
   `context = project_prefix(vlm_features, aux_visual_inputs, domain_id)`: the projected features plus `pos_emb[50:250]`, followed by 32 soft-prompt tokens for the domain.
2. **Denoising, 10 steps, t = 1.0, 0.9, …, 0.1:**
   ```
   x_t    = noise * t + action * (1 - t)        # noise ~ N(0,1), shape [1,50,20]; action starts at 0
   x      = project_in(x_t, proprio[20], t, domain_id)
   h      = core(x, context)
   action = project_out_20(h, domain_id)        # [1,50,20]
   ```
3. **Output.** Take `action[..., :6] * action_std + action_mean`. That is 6 joint targets in degrees for a 50-step chunk. Use the stats from the post-processor in `checkpoint/` (they are also in the ref bundle).

## Recommended path for MuJoCo

1. Load the policy in PyTorch (LeRobot, X-VLA policy):
   ```python
   policy = XVLAPolicy.from_pretrained("checkpoint/pretrained_model")
   preprocessor, postprocessor = make_pre_post_processors(policy_cfg=policy.config, pretrained_path="checkpoint/pretrained_model")
   actions = postprocessor(policy.predict_action_chunk(preprocessor(obs)))
   ```
   Feed observations with the same keys and camera names as in `train_config.json`. No ONNX is needed for this.
2. Swap in the ONNX core only once that loop works. Keep the VLM and `project_prefix` in PyTorch, and use `XVLAHostProjector` from `host/xvla_htp_audit_runner.py` for `project_in`/`project_out`. Check against `host/xvla_ref_bundle_val20.npz`: the FP32 core should reproduce `pred_torch` to about 1e-5°.

## Notes
- The W8A16 core's accuracy on the NPU is 0.094° MAE vs PyTorch. On a desktop CPU, prefer the FP32 core.
- `domain_id` comes from the preprocessor (`policy._build_model_inputs(batch)["domain_id"]`). Proprio is 20-dim.
