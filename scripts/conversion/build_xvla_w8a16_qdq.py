"""Official X-VLA QDQ HTP build (Task G): the board-verified "spill fix" recipe as a standalone, assert-guarded script.

usage: 07_build_qdq_htp.py --weights {int8,int4} --out-dir DIR --name NAME [--skip-finite]
  W8A16_v4: --weights int8 --out-dir runs/xvla/w8a16_htp_v4 --name xvla_denoise_core_w8a16_htp_v4
  W4A16_v3: --weights int4 --out-dir runs/xvla/w4a16_htp_v3 --name xvla_denoise_core_w4a16_htp_v3
Outputs: DIR/NAME.onnx + DIR/NAME.onnx.data + DIR/NAME.build_report.json

Recipe (reproduces runs/xvla/spill_probe/qdq_lnw8u, 1 QNN partition / 0 CPU nodes on the board), applied to the FP32 rank-4 core
(FP32_CORE in xvla_common.py):
  1. quant_pre_process(skip_optimization=False)             -> "Gemm route" (96 Gemm + 48 MatMul)
  2. quantize_static, QuantFormat.QDQ, MinMax over the cached 640 true-recurrence feeds (CALIB_NPZ), per_channel=True
       activations QUInt16, weights QInt8 (int8) / QInt4 (int4), per-channel symmetric
       extra_options ActivationSymmetric=False, WeightSymmetric=True, QDQOpTypePerChannelSupportToAxis={"MatMul": 1}
       op_types_to_quantize = EVERY op type present after pre-processing (explicit list QDQ_OP_TYPES, asserted == pre-processed op set)
       nodes_to_exclude = graph-input Concat (node_cat), final Slice (node_slice_1), final LayerNorm (node_layer_norm_48)
           -> no Q consumes a graph input, no DQ produces the graph output
       TensorQuantOverrides: every quantized LayerNorm's gamma (scale input) = QUInt8 asymmetric (signed INT8 gamma -> QNN error 3110);
           beta becomes INT32 through ORT's bias path
  3. every Reshape allowzero=0, onnx.checker, then the structural asserts in verify_structure().
The only difference between the two builds is WEIGHT_TYPE. Opset stays 21 (the FP32 core is opset 21, which QInt4 needs); like
02_quantize.py w4a16 nothing special is done for int4 apart from weight_type=QInt4.
"""
import argparse
import collections
import importlib.util
import json
import resource
import shutil
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper
from onnxruntime.quantization import CalibrationDataReader, CalibrationMethod, QuantFormat, QuantType, quantize_static
from onnxruntime.quantization.shape_inference import quant_pre_process

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from xvla_common import CALIB_NPZ, FP32_CORE, ROOT, make_session, sha256  # noqa: E402

_spec = importlib.util.spec_from_file_location("evalmod", HERE / "03_eval_host.py")
evalmod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(evalmod)          # only used for g1_scan()

# ----------------------------------------------------------------------------- recipe constants (explicit, no variant table)
ACT_TYPE = QuantType.QUInt16
WEIGHT_TYPES = {"int8": QuantType.QInt8, "int4": QuantType.QInt4}
LN_GAMMA_OVERRIDE = {"quant_type": QuantType.QUInt8, "symmetric": False}
QDQ_OP_TYPES = ["Add", "Concat", "Gelu", "Gemm", "LayerNormalization", "MatMul", "Mul", "Reshape", "Slice", "Softmax", "Split", "Transpose"]
EXPECTED_EXCLUDE = ["node_cat", "node_slice_1", "node_layer_norm_48"]
N_LN, N_LN_QUANT = 49, 48
FINITE_FEEDS = [0, 9, 320]                  # frame0 t=1.0, frame0 t=0.1, mid-set feed (same as the probe)
DT = TensorProto.DataType.Name


class NpzReader(CalibrationDataReader):
    def __init__(self):
        cal = np.load(CALIB_NPZ)
        self.X, self.C, self.IDX = cal["x"], cal["context"].reshape(64, 1, 232, 1024), cal["context_frame_idx"]
        assert self.X.shape == (640, 1, 50, 1024) and self.IDX.shape == (640,)
        self.i = 0

    def get_next(self):
        if self.i >= len(self.X):
            return None
        j = self.i
        self.i += 1
        return {"x": self.X[j], "context": self.C[self.IDX[j]]}

    def rewind(self):
        self.i = 0


def boundary_nodes(pm):
    """Names to exclude, derived structurally from the pre-processed graph (then asserted == the known trio)."""
    gin = {i.name for i in pm.graph.input}
    gout = {o.name for o in pm.graph.output}
    cat = [n for n in pm.graph.node if any(i in gin for i in n.input)]
    sl = [n for n in pm.graph.node if n.op_type == "Slice"]
    fin = [n for n in pm.graph.node if any(o in gout for o in n.output)]
    assert len(cat) == 1 and cat[0].op_type == "Concat", [n.name for n in cat]
    assert len(sl) == 1, [n.name for n in sl]
    assert len(fin) == 1 and fin[0].op_type == "LayerNormalization", [n.name for n in fin]
    excl = [cat[0].name, sl[0].name, fin[0].name]
    assert excl == EXPECTED_EXCLUDE, excl
    return excl


def verify_structure(path):
    """All hard asserts of the deliverable + the diagnostic tables. Returns a dict."""
    m = onnx.load(str(path), load_external_data=False)
    g = m.graph
    I = {t.name: t for t in g.initializer}
    prod = {o: n for n in g.node for o in n.output}
    cons = collections.defaultdict(list)
    for n in g.node:
        for i in n.input:
            cons[i].append(n)
    gin = {i.name for i in g.input}
    gout = {o.name for o in g.output}
    ops = collections.Counter(n.op_type for n in g.node)

    # (1) boundaries
    q_on_input = [n.name for n in g.node if n.op_type == "QuantizeLinear" and n.input[0] in gin]
    dq_to_output = [n.name for n in g.node if n.op_type == "DequantizeLinear" and n.output[0] in gout]
    assert not q_on_input, f"Q node(s) consume a graph input: {q_on_input}"
    assert not dq_to_output, f"DQ node(s) produce the graph output: {dq_to_output}"
    assert all(o in prod and prod[o].op_type == "LayerNormalization" for o in gout)

    # (2) LayerNorm gamma UINT8 (asymmetric: zero point present and UINT8)
    ln_rows = collections.Counter()
    n_ln = n_ln_q = 0
    for n in g.node:
        if n.op_type != "LayerNormalization":
            continue
        n_ln += 1
        src = prod.get(n.input[0])
        if src is None or src.op_type != "DequantizeLinear":
            ln_rows[("unquantized", "gamma=" + (DT(I[n.input[1]].data_type) if n.input[1] in I else "?"))] += 1
            continue
        n_ln_q += 1
        gdq = prod.get(n.input[1])
        assert gdq is not None and gdq.op_type == "DequantizeLinear", f"LN {n.name}: gamma not DQ-produced"
        gx = I[gdq.input[0]]
        gzp = I[gdq.input[2]]
        assert gx.data_type == TensorProto.UINT8, f"LN {n.name}: gamma data dtype {DT(gx.data_type)} != UINT8"
        assert gzp.data_type == TensorProto.UINT8, f"LN {n.name}: gamma zero-point dtype {DT(gzp.data_type)} != UINT8"
        bdq = prod.get(n.input[2]) if len(n.input) > 2 else None
        bdt = (DT(I[bdq.input[0]].data_type) if bdq is not None and bdq.op_type == "DequantizeLinear" else "raw")
        xzp = I[src.input[2]]
        ln_rows[("quantized", f"x=DQ:{DT(xzp.data_type)}", f"gamma={DT(gx.data_type)}(zp {DT(gzp.data_type)})", f"beta={bdt}")] += 1
    assert (n_ln, n_ln_q) == (N_LN, N_LN_QUANT), (n_ln, n_ln_q)

    # (3) QDQ scales FLOAT32 (scale dtype of every Q/DQ), zero points present
    scale_dt = collections.Counter()
    for n in g.node:
        if n.op_type in ("QuantizeLinear", "DequantizeLinear"):
            s = I.get(n.input[1])
            scale_dt[DT(s.data_type) if s is not None else "NON_INITIALIZER"] += 1
    assert set(scale_dt) == {"FLOAT"}, dict(scale_dt)

    # (4) rank <= 4 for every initializer and every inferable tensor
    max_rank = max(len(t.dims) for t in g.initializer)
    inferred = onnx.shape_inference.infer_shapes(onnx.load(str(path), load_external_data=False), strict_mode=False)
    for v in list(inferred.graph.value_info) + list(inferred.graph.input) + list(inferred.graph.output):
        if v.type.HasField("tensor_type") and v.type.tensor_type.HasField("shape"):
            max_rank = max(max_rank, len(v.type.tensor_type.shape.dim))
    assert max_rank <= 4, f"max rank {max_rank}"

    # (5) every Reshape has an explicit allowzero == 0
    for n in g.node:
        if n.op_type == "Reshape":
            az = [a.i for a in n.attribute if a.name == "allowzero"]
            assert az == [0], f"Reshape {n.name} allowzero={az}"

    zp_dt = collections.Counter((n.op_type, DT(I[n.input[2]].data_type)) for n in g.node
                                if n.op_type in ("QuantizeLinear", "DequantizeLinear") and len(n.input) > 2 and n.input[2] in I)
    wdq = collections.Counter(DT(I[n.input[2]].data_type) for n in g.node if n.op_type == "DequantizeLinear"
                              and any(a.name == "axis" for a in n.attribute) and len(n.input) > 2 and n.input[2] in I)
    return {"asserts_passed": ["no_Q_on_graph_input", "no_DQ_on_graph_output", "quantized_LN_gamma_UINT8(data+zp)",
                               "qdq_scales_FLOAT32", "max_rank<=4", "all_Reshape_allowzero==0"],
            "op_counts": dict(ops), "Q": ops["QuantizeLinear"], "DQ": ops["DequantizeLinear"],
            "Gemm": ops["Gemm"], "MatMul": ops["MatMul"], "LayerNormalization": ops["LayerNormalization"],
            "layernorm_quantized": n_ln_q, "layernorm_total": n_ln,
            "layernorm_input_dtypes": {" | ".join(k): v for k, v in ln_rows.items()},
            "qdq_scale_dtypes": dict(scale_dt), "qdq_zero_point_dtypes": {f"{a}:{b}": c for (a, b), c in zp_dt.items()},
            "per_channel_DQ_zero_point_dtypes": dict(wdq), "max_rank": max_rank,
            "graph_input_consumers": {i: [c.op_type for c in cons.get(i, [])] for i in gin},
            "graph_output_producers": {o: prod[o].op_type for o in gout}}


def finite_check(path):
    cal = np.load(CALIB_NPZ)
    sess, ref = make_session(path, 16), make_session(FP32_CORE, 16)
    out = []
    for j in FINITE_FEEDS:
        x = cal["x"][j]
        c = cal["context"][cal["context_frame_idx"][j]].reshape(1, 232, 1024)
        r = ref.run(None, {"x": x, "context": c})[0]
        h = sess.run(None, {"x": x, "context": c})[0]
        fin = bool(np.isfinite(h).all())
        assert fin, f"non-finite output on calib feed {j}"
        out.append({"feed": j, "out_shape": list(h.shape), "finite": fin, "max_abs_diff_vs_fp32": float(np.abs(h - r).max()),
                    "mean_abs_diff_vs_fp32": float(np.abs(h - r).mean()), "ref_max_abs": float(np.abs(r).max())})
    return out


def build(weights, out_dir, name, skip_finite=False):
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{name}.onnx"
    dest_data = Path(str(dest) + ".data")
    scratch = Path(tempfile.mkdtemp(prefix="scr_", dir=str(out_dir)))
    rep = {"script": "07_build_qdq_htp.py", "weights": weights, "name": name, "path": str(dest), "fp32_core": str(FP32_CORE),
           "calib": str(CALIB_NPZ)}
    t0 = time.perf_counter()
    try:
        # 1. pre-process, Gemm route (skip_optimization=False)
        pre = scratch / "pre.onnx"
        quant_pre_process(str(FP32_CORE), str(pre), skip_optimization=False, save_as_external_data=True,
                          external_data_location=f"{pre.name}.data")
        pm = onnx.load(str(pre), load_external_data=False)
        pre_ops = dict(collections.Counter(n.op_type for n in pm.graph.node))
        rep["pre_ops"] = pre_ops
        assert pre_ops["Gemm"] == 96 and pre_ops["MatMul"] == 48, f"not the Gemm route: {pre_ops}"
        assert sorted(pre_ops) == sorted(QDQ_OP_TYPES), f"op set changed: {sorted(pre_ops)}"

        # 2. quantize
        excl = boundary_nodes(pm)
        overrides = {n.input[1]: [dict(LN_GAMMA_OVERRIDE)] for n in pm.graph.node
                     if n.op_type == "LayerNormalization" and n.name not in excl}
        assert len(overrides) == N_LN_QUANT
        extra = {"ActivationSymmetric": False, "WeightSymmetric": True, "QDQOpTypePerChannelSupportToAxis": {"MatMul": 1},
                 "TensorQuantOverrides": overrides}
        rep["quant"] = {"activation": str(ACT_TYPE), "weight": str(WEIGHT_TYPES[weights]), "op_types_to_quantize": QDQ_OP_TYPES,
                        "nodes_to_exclude": excl, "calibrate": "MinMax", "per_channel": True, "calib_samples": 640,
                        "extra_options": {k: (v if k != "TensorQuantOverrides" else f"<{len(v)} LN gamma -> QUInt8 asymmetric>")
                                          for k, v in extra.items()}}
        for p in (dest, dest_data):
            if p.exists():
                p.unlink()
        quantize_static(str(pre), str(dest), NpzReader(), quant_format=QuantFormat.QDQ, op_types_to_quantize=QDQ_OP_TYPES,
                        nodes_to_exclude=excl, per_channel=True, activation_type=ACT_TYPE, weight_type=WEIGHT_TYPES[weights],
                        calibrate_method=CalibrationMethod.MinMax, use_external_data_format=True, extra_options=extra)

        # 3. allowzero=0 on all Reshapes, checker, structural asserts
        mq = onnx.load(str(dest), load_external_data=False)
        for n in mq.graph.node:
            if n.op_type == "Reshape":
                found = False
                for a in n.attribute:
                    if a.name == "allowzero":
                        a.i = 0
                        found = True
                if not found:
                    n.attribute.append(helper.make_attribute("allowzero", 0))
        onnx.save(mq, str(dest))
        onnx.checker.check_model(str(dest))
        rep["build_seconds"] = time.perf_counter() - t0
        rep["structure"] = verify_structure(dest)
        rep["g1"] = evalmod.g1_scan(dest)
        assert rep["g1"]["onnx_checker"] == "PASS" and rep["g1"]["g1_pass"], rep["g1"]
        rep["bytes"] = {dest.name: dest.stat().st_size, dest_data.name: dest_data.stat().st_size}
        rep["sha256"] = {dest.name: sha256(dest), dest_data.name: sha256(dest_data)}
        if not skip_finite:
            rep["cpu_ep_finite_check"] = finite_check(dest)
        rep["peak_rss_mb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        rep["status"] = "ok"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        if rep.get("status") != "ok":
            rep["status"] = "FAILED"
        (out_dir / f"{name}.build_report.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps({k: rep.get(k) for k in ("status", "build_seconds", "bytes", "sha256")}, indent=1), flush=True)
    print("structure:", json.dumps({k: v for k, v in rep["structure"].items() if k != "op_counts"}, indent=1), flush=True)
    print("ops:", rep["structure"]["op_counts"], flush=True)
    print("g1_pass:", rep["g1"]["g1_pass"], "checker:", rep["g1"]["onnx_checker"], flush=True)
    for c in rep.get("cpu_ep_finite_check", []):
        print("finite:", c, flush=True)
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", choices=["int8", "int4"], required=True)
    ap.add_argument("--out-dir", required=True, help="absolute, or relative to the workspace root")
    ap.add_argument("--name", required=True, help="output basename without .onnx")
    ap.add_argument("--skip-finite", action="store_true")
    a = ap.parse_args()
    od = Path(a.out_dir)
    if not od.is_absolute():
        od = ROOT / od
    build(a.weights, od, a.name, a.skip_finite)
