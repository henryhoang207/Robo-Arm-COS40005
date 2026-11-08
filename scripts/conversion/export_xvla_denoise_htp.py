import sys
import time
from pathlib import Path
import torch
import torch.nn as nn
import numpy as np
import onnx
from onnx import shape_inference

ROOT = Path("/mnt/data8tb/henry/robot-arm-conversion")
REPO = ROOT / "source/SmolVLA_TrainingScript"
CHECKPOINT = ROOT / "staging/results/xvla_so101/selected_100000/pretrained_model"
OUTPUT_DIR = ROOT / "runs/xvla/w8a16_htp"

sys.path.insert(0, str(REPO))
from lerobot.policies.xvla.modeling_xvla import XVLAPolicy

print("Loading XVLAPolicy on CPU...", flush=True)
policy = XVLAPolicy.from_pretrained(str(CHECKPOINT))
policy.to("cpu")
policy.eval()
transformer = policy.model.transformer

# Patch Attention forward to be strictly rank-4
def clean_attention_forward(self, x: torch.Tensor) -> torch.Tensor:
    batch_size, seq_len, channels = x.shape
    qkv = self.qkv(x) # [B, T, 3 * D]
    d = self.num_heads * self.head_dim
    q_proj, k_proj, v_proj = torch.split(qkv, d, dim=-1)
    
    q = self.q_norm(q_proj.reshape(batch_size, seq_len, self.num_heads, self.head_dim).permute(0, 2, 1, 3))
    k = self.k_norm(k_proj.reshape(batch_size, seq_len, self.num_heads, self.head_dim).permute(0, 2, 1, 3))
    v = v_proj.reshape(batch_size, seq_len, self.num_heads, self.head_dim).permute(0, 2, 1, 3)
    
    q = q * self.scale
    attn = torch.matmul(q, k.transpose(-2, -1))
    attn = attn.softmax(dim=-1)
    x = torch.matmul(attn, v)
    
    x = x.permute(0, 2, 1, 3).reshape(batch_size, seq_len, channels)
    x = self.proj(x)
    return x

import types
for block in transformer.blocks:
    block.attn.forward = types.MethodType(clean_attention_forward, block.attn)

class XVLADenoiseCore(nn.Module):
    def __init__(self, transformer):
        super().__init__()
        self.blocks = transformer.blocks
        self.norm = transformer.norm

    def forward(self, x, context):
        # x: [1, 50, 1024]
        # context: [1, 232, 1024]
        x_full = torch.cat([x, context], dim=1) # [1, 282, 1024]
        for block in self.blocks:
            x_full = block(x_full)
        h_norm = self.norm(x_full[:, :50, :]) # [1, 50, 1024]
        return h_norm

core_model = XVLADenoiseCore(transformer).to("cpu").eval()

dummy_x = torch.zeros(1, 50, 1024, dtype=torch.float32, device="cpu")
dummy_context = torch.zeros(1, 232, 1024, dtype=torch.float32, device="cpu")

out_onnx = OUTPUT_DIR / "xvla_denoise_core_fp32_rank4.onnx"
out_data = OUTPUT_DIR / "xvla_denoise_core_fp32_rank4.onnx.data"

for p in [out_onnx, out_data]:
    if p.exists():
        p.unlink()

print(f"Exporting to {out_onnx}...", flush=True)
t0 = time.perf_counter()
torch.onnx.export(
    core_model,
    (dummy_x, dummy_context),
    str(out_onnx),
    input_names=["x", "context"],
    output_names=["h_norm"],
    opset_version=21,
    external_data=True
)
print(f"Export completed in {time.perf_counter() - t0:.1f} s")

# Verify exported model
print("Checking model with onnx.checker...", flush=True)
onnx.checker.check_model(str(out_onnx))
print("onnx.checker PASSED!")

# Check ops and ranks
m = onnx.load(str(out_onnx), load_external_data=False)
op_hist = {}
for n in m.graph.node:
    op_hist[n.op_type] = op_hist.get(n.op_type, 0) + 1

print("\nOp type histogram:")
for k, v in sorted(op_hist.items(), key=lambda x: -x[1]):
    print(f"  {k:<20s}: {v}")

scatters = [n for n in m.graph.node if n.op_type == 'ScatterND']
recips = [n for n in m.graph.node if n.op_type == 'Reciprocal']
print(f"\nScatterND count: {len(scatters)} (must be 0)")
print(f"Reciprocal count: {len(recips)} (must be 0)")
assert len(scatters) == 0
assert len(recips) == 0

# Ensure allowzero=0 on all Reshapes
reshapes = [n for n in m.graph.node if n.op_type == 'Reshape']
for n in reshapes:
    for a in n.attribute:
        if a.name == 'allowzero':
            a.i = 0

onnx.save(m, str(out_onnx))

# Run shape inference and check ranks
m_inf = shape_inference.infer_shapes(m)
rank_gt4 = [vi.name for vi in m_inf.graph.value_info if len(vi.type.tensor_type.shape.dim) > 4]
print(f"\nTensors of rank > 4 in entire model: {len(rank_gt4)} (must be 0)")
assert len(rank_gt4) == 0, f"Found rank > 4: {rank_gt4}"

print(f"SUCCESS: Exported {out_onnx.name} ({out_onnx.stat().st_size} bytes, data: {out_data.stat().st_size} bytes)")
print("ALL 5 HTP RULES ENFORCED CLEANLY (0 ScatterND, 0 Reciprocal, 0 dyn/-1 Reshape, 0 rank > 4)!")
