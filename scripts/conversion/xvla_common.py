"""Shared helpers for the X-VLA W4A16 / W8A16_v2 host build + audit (Task C, Profile 4B).

All paths are sol1 paths. Projector + recurrence are copied verbatim from
build_xvla_reference_and_parity.py (XVLAHostProjector) so that the harness is
numerically the same as the one that produced the original G3 (0.238817 deg).
"""
import hashlib
from pathlib import Path

import numpy as np

ROOT = Path("/mnt/data8tb/henry/robot-arm-conversion")
REF_DIR = ROOT / "runs/xvla/w8a16_htp"               # READ-ONLY inputs
W4_DIR = ROOT / "runs/xvla/w4a16_htp"
V2_DIR = ROOT / "runs/xvla/w8a16_htp_v2"
FP32_CORE = REF_DIR / "xvla_denoise_core_fp32_rank4.onnx"
PROJ_NPZ = REF_DIR / "xvla_io_projector_weights.npz"
BUNDLE_NPZ = REF_DIR / "xvla_ref_bundle_val20.npz"
STEPWISE_NPZ = REF_DIR / "xvla_ref_stepwise.npz"
ORIG_W8A16 = REF_DIR / "xvla_denoise_core_w8a16_htp.onnx"
CALIB_NPZ = W4_DIR / "xvla_calib_feeds_train64.npz"
NUM_STEPS = 10


def sha256(path, chunk=1 << 24):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


class XVLAHostProjector:
    def __init__(self, npz_path):
        d = np.load(npz_path)
        self.enc_fc = d["action_encoder_fc"]
        self.enc_b = d["action_encoder_bias"]
        self.dec_fc = d["action_decoder_fc"]
        self.dec_b = d["action_decoder_bias"]
        self.soft_hub = d["soft_prompt_hub"]
        self.vlm_w = d["vlm_proj_w"]
        self.vlm_b = d["vlm_proj_b"]
        self.aux_w = d["aux_visual_proj_w"]
        self.aux_b = d["aux_visual_proj_b"]
        self.pos_emb = d["pos_emb"]

    def timestep_embedding(self, t, dim=32, max_period=100):
        half = dim // 2
        freqs = np.exp(-np.log(float(max_period)) * np.arange(half, dtype=np.float32) / half)
        args = float(t) * freqs
        emb = np.concatenate([np.cos(args), np.sin(args)], axis=-1)
        return emb.astype(np.float32)

    def project_prefix(self, vlm_features, aux_visual_inputs, domain_id):
        vlm_p = vlm_features @ self.vlm_w.T + self.vlm_b
        aux_p = aux_visual_inputs @ self.aux_w.T + self.aux_b
        context = np.concatenate([vlm_p, aux_p], axis=1)
        context_pos = context + self.pos_emb[:, 50:250, :]
        soft_prompts = self.soft_hub[domain_id].reshape(1, 32, 1024)
        prefix_tokens = np.concatenate([context_pos, soft_prompts], axis=1)
        return prefix_tokens.astype(np.float32)

    def project_in(self, x_t, proprio, t, domain_id):
        x_t = np.asarray(x_t, dtype=np.float32).reshape(1, 50, 20)
        proprio = np.asarray(proprio, dtype=np.float32).reshape(1, 20)
        t_emb = self.timestep_embedding(t, dim=32)
        t_tokens = np.broadcast_to(t_emb.reshape(1, 1, 32), (1, 50, 32))
        p_tokens = np.broadcast_to(proprio[:, None, :], (1, 50, 20))
        act_tokens = np.concatenate([x_t, p_tokens, t_tokens], axis=-1)
        w_enc = self.enc_fc[domain_id].reshape(72, 1024)
        b_enc = self.enc_b[domain_id].reshape(1, 1024)
        x_act = act_tokens @ w_enc + b_enc
        x_in = x_act + self.pos_emb[:, :50, :]
        return x_in.astype(np.float32)

    def project_out_20(self, h_norm, domain_id):
        w_dec = self.dec_fc[domain_id].reshape(1024, 20)
        b_dec = self.dec_b[domain_id].reshape(1, 20)
        return (h_norm @ w_dec + b_dec).astype(np.float32)


def make_session(model_path, threads=16):
    import onnxruntime as ort
    so = ort.SessionOptions()
    so.intra_op_num_threads = threads
    so.log_severity_level = 3
    return ort.InferenceSession(str(model_path), so, providers=["CPUExecutionProvider"])
