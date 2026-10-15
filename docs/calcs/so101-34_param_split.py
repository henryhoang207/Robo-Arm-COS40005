#!/usr/bin/env python3
"""SO101-34 supporting calculations (decision record 0002). Pure Python, no dependencies.

What it computes  [Reasoning — Claude's derivation; inputs are cited in the decision record]
  1. Diffusion Policy (LeRobot 0.6.2 module structure): parameters in convolutions vs Linear layers.
  2. ACT (LeRobot 0.6.2): parameters in the inference graph (training-only VAE encoder removed).
  3. OpenVLA weight-memory arithmetic against the 16 GB VENTUNO Q.

Cross-checks against Hugging Face safetensors counts (read 14 Oct 2026):
  lerobot/diffusion_pusht                 262,709,062
  lerobot/act_aloha_sim_transfer_cube_human 51,685,096
  openvla/openvla-7b                    7,541,237,184

Formulas: Conv1d/Conv2d = in*out*k (+out bias); ConvTranspose1d = in*out*k (+out);
Linear = in*out + out; GroupNorm/LayerNorm affine = 2*C; FrozenBatchNorm2d has no parameters.
ResNet-18 convolution weights (no fc) = 11,166,912; its BN/GN affine parameters = 9,600.
Run:  python3 so101-34_param_split.py
"""

RES18_CONV = 11_166_912
RES18_NORM = 9_600


def lin(i, o):
    return i * o + o


def conv1d(i, o, k):
    return i * o * k + o


def add(total, part):
    for key, val in part.items():
        total[key] = total.get(key, 0) + val


# ---------------- Diffusion Policy (LeRobot policies/diffusion, v0.6.2) ----------------
def dp_res_block(i, o, cond, k=5, film=True):
    d = {"conv": conv1d(i, o, k) + conv1d(o, o, k), "norm": 2 * (2 * o), "linear": lin(cond, 2 * o if film else o)}
    if i != o:
        d["conv"] += conv1d(i, o, 1)  # residual 1x1 conv
    return d


def dp_unet(action_dim, global_cond_dim, down=(512, 1024, 2048), k=5, emb=128):
    t = {"conv": 0, "norm": 0, "linear": lin(emb, 4 * emb) + lin(4 * emb, emb)}  # timestep encoder
    cond = emb + global_cond_dim
    in_out = [(action_dim, down[0])] + list(zip(down[:-1], down[1:]))
    for idx, (di, do) in enumerate(in_out):  # down path
        add(t, dp_res_block(di, do, cond, k))
        add(t, dp_res_block(do, do, cond, k))
        if idx < len(in_out) - 1:
            t["conv"] += conv1d(do, do, 3)  # downsample
    for _ in range(2):  # mid
        add(t, dp_res_block(down[-1], down[-1], cond, k))
    for idx, (do, di) in enumerate(reversed(in_out[1:])):  # up path
        add(t, dp_res_block(2 * di, do, cond, k))
        add(t, dp_res_block(do, do, cond, k))
        if idx < len(in_out) - 1:
            t["conv"] += do * do * 4 + do  # ConvTranspose1d(do, do, 4, 2, 1)
    t["conv"] += conv1d(down[0], down[0], k) + conv1d(down[0], action_dim, 1)  # final conv block + 1x1
    t["norm"] += 2 * down[0]
    return t


def dp_policy(action_dim, state_dim, n_cams, n_obs=2, kp=32, separate_encoders=True):
    t = {"conv": 0, "norm": 0, "linear": 0}
    for _ in range(n_cams if separate_encoders else 1):
        add(t, {"conv": RES18_CONV + (512 * kp + kp), "norm": RES18_NORM, "linear": lin(2 * kp, 2 * kp)})
    global_cond = (state_dim + 2 * kp * n_cams) * n_obs
    add(t, dp_unet(action_dim, global_cond))
    return t


# ---------------- ACT (LeRobot policies/act, v0.6.2; pre_norm=False) ----------------
def act_policy(state_dim, action_dim, d=512, ff=3200, latent=32, chunk=100, n_enc=4, n_dec=1, n_vae=4):
    mha = 4 * d * d + 4 * d
    ffn = lin(d, ff) + lin(ff, d)
    conv = RES18_CONV + (512 * d + d)  # backbone + 1x1 input projection
    linear = n_enc * (mha + ffn) + n_dec * (2 * mha + ffn) + lin(state_dim, d) + lin(latent, d) + lin(d, action_dim)
    other = n_enc * 4 * d + n_dec * 6 * d + 2 * d + 2 * d + chunk * d  # layer norms, pos embeddings
    vae = n_vae * (mha + ffn + 4 * d) + d + lin(state_dim, d) + lin(action_dim, d) + lin(d, 2 * latent)
    return {"conv": conv, "linear": linear, "other": other, "inference": conv + linear + other, "vae_training_only": vae}


def pct(a, b):
    return 100.0 * a / b


if __name__ == "__main__":
    print("== Diffusion Policy ==")
    chk = dp_policy(action_dim=2, state_dim=2, n_cams=1)
    print(f"PushT architecture check: {sum(chk.values()):,} (Hugging Face: 262,709,062)")
    so = dp_policy(action_dim=6, state_dim=6, n_cams=2)
    tot = sum(so.values())
    print(f"Project shape (6-D, 2 cameras): total {tot:,}")
    print(f"  conv   {so['conv']:,} ({pct(so['conv'], tot):.1f}%)")
    print(f"  linear {so['linear']:,} ({pct(so['linear'], tot):.1f}%)")
    print(f"  norm   {so['norm']:,}")

    print("\n== ACT ==")
    a = act_policy(14, 14)
    print(f"ALOHA check (incl. VAE): {a['inference'] + a['vae_training_only']:,} (Hugging Face: 51,685,096)")
    a = act_policy(6, 6)
    print(f"Project shape inference graph: {a['inference']:,} (VAE encoder dropped: {a['vae_training_only']:,})")
    print(f"  linear {pct(a['linear'], a['inference']):.1f}%  conv {pct(a['conv'], a['inference']):.1f}%")

    print("\n== OpenVLA weight memory ==")
    n = 7_541_237_184
    fp16 = n * 2
    print(f"FP16: {n:,} x 2 B = {fp16:,} B = {fp16/1e9:.2f} GB = {fp16/2**30:.2f} GiB")
    print(f"INT8 lower bound (1 B/weight, no scales): {n/1e9:.2f} GB")
    print(f"INT4 lower bound (0.5 B/weight, no scales): {n*0.5/1e9:.2f} GB")
    print("VENTUNO Q RAM: 16 GB LPDDR5 (2 x 8 GB) before OS, firmware and runtime use.")
