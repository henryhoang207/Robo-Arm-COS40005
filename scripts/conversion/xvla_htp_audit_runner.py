#!/usr/bin/env python3
"""X-VLA HTP audit runner (board: ORT QNN EP / host dry-run: ORT CPU EP).

Derived from the proven SmolVLA runner (htp_audit_runner.py). Same session setup,
profiling, partition / CPU-node / VTCM spill-fill parsing, latency statistics and
G7a / G7b definitions; the model I/O and rollout are X-VLA specific:

  core graph : inputs  x [1,50,1024], context [1,232,1024]  ->  h_norm [1,50,1024]
  recurrence : for step in 10..1, t = step/10
                 x_t         = x1*t + action_loop*(1-t)
                 x_in        = project_in(x_t, proprio, t, domain_id)       (host CPU, NumPy)
                 h_norm      = core(x=x_in, context=prefix_context)         (QNN HTP or CPU EP)
                 action_loop = project_out_20(h_norm, domain_id)            (host CPU, NumPy)
               pred = action_loop[..., :6] * action_std + action_mean

Compatible with Python 3.10 / 3.12 and NumPy 1.x / 2.x (see timestep_embedding).
Linux only for the QNN path (reads /proc, uses fd redirection to capture QNN logs).

Exit code: 0 = run completed and every applicable gate passed, 1 = run completed but a gate /
reproduction check failed, 2 = run could not be completed (e.g. QNN EP unavailable).
"""
import argparse
import json
import os
import platform
import re
import sys
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort

try:
    import resource  # POSIX only
except ImportError:  # pragma: no cover
    resource = None

RUNNER_VERSION = "xvla-htp-audit-runner-1.0"
NUM_STEPS = 10
NUM_STEPWISE_FRAMES = 5
GATE_MAE_DEG = 0.35  # handoff section 6: on-board rollout MAE <= 0.35 deg


# --------------------------------------------------------------------------------------
# Host-side projector (X-VLA: action encoder / decoder + timestep embedding, domain tables)
# --------------------------------------------------------------------------------------
class XVLAHostProjector:
    """Numerically identical to XVLAHostProjector in build_xvla_reference_and_parity.py
    (only the tensors the rollout needs are loaded; project_prefix is not needed because
    the bundle stores the precomputed prefix contexts)."""

    def __init__(self, npz_path):
        d = np.load(npz_path)
        self.enc_fc = d["action_encoder_fc"]
        self.enc_b = d["action_encoder_bias"]
        self.dec_fc = d["action_decoder_fc"]
        self.dec_b = d["action_decoder_bias"]
        self.pos_emb = d["pos_emb"]
        # Timestep-embedding frequencies. Computed in float64 and cast to float32 at the end.
        # The reference build script wrote `-np.log(max_period) * np.arange(half, dtype=np.float32) / half`,
        # which is float64 under NumPy 2 (NEP 50, np.float64 scalar is not "weak") and float32 under
        # NumPy 1. G3 was produced with NumPy 2.2.6, so the float64 path is reproduced explicitly here
        # to make the result independent of the NumPy major version.
        half = 16
        self._freqs = np.exp(-np.log(100.0) * np.arange(half, dtype=np.float64) / half)

    def timestep_embedding(self, t, dim=32):
        assert dim == 32
        args = float(t) * self._freqs
        emb = np.concatenate([np.cos(args), np.sin(args)], axis=-1)
        return emb.astype(np.float32)

    def project_in(self, x_t, proprio, t, domain_id):
        x_t = np.asarray(x_t, dtype=np.float32).reshape(1, 50, 20)
        proprio = np.asarray(proprio, dtype=np.float32).reshape(1, 20)
        t_emb = self.timestep_embedding(t)
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


# --------------------------------------------------------------------------------------
# Helpers copied from / mirroring the SmolVLA runner
# --------------------------------------------------------------------------------------
class CaptureFD:
    """Redirect process-level stdout/stderr (fd 1/2) to a file, so native (QNN) logging is captured."""

    def __init__(self, filepath):
        self.filepath = filepath

    def __enter__(self):
        sys.stdout.flush()
        sys.stderr.flush()
        self.log_fd = os.open(str(self.filepath), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        self.saved_stdout = os.dup(1)
        self.saved_stderr = os.dup(2)
        os.dup2(self.log_fd, 1)
        os.dup2(self.log_fd, 2)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(self.saved_stdout, 1)
        os.dup2(self.saved_stderr, 2)
        os.close(self.saved_stdout)
        os.close(self.saved_stderr)
        os.close(self.log_fd)


def parse_profile_json(profile_path):
    """Same logic as the SmolVLA runner: per-provider node-event counts, CPU compute / copy events."""
    if not profile_path or not os.path.exists(profile_path):
        return {}, [], []
    with open(profile_path, "r") as f:
        data = json.load(f)
    events = data if isinstance(data, list) else data.get("traceEvents", [])
    provider_counts = {}
    cpu_compute_nodes = []
    cpu_copy_nodes = []
    for ev in events:
        args = ev.get("args", {})
        provider = args.get("provider")
        if provider:
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
            if provider == "CPUExecutionProvider":
                op_name = args.get("op_name", "")
                node_entry = {"name": ev.get("name"), "op_name": op_name, "dur_us": ev.get("dur", 0)}
                if "Memcpy" in op_name or "Copy" in op_name:
                    cpu_copy_nodes.append(node_entry)
                else:
                    cpu_compute_nodes.append(node_entry)
    return provider_counts, cpu_compute_nodes, cpu_copy_nodes


_DDR_BLOCK_RE = re.compile(r"====== DDR bandwidth summary ======(.*?read_total_bytes=\d+)", re.DOTALL | re.IGNORECASE)


def parse_qnn_log(log_path):
    """Parse the verbose ORT/QNN log captured during session creation.

    Marker formats were taken from real VENTUNO Q logs of the SmolVLA runs:
      '[...qnn_execution_provider.cc:... GetCapability] Number of partitions supported by QNN EP: 1,
       number of nodes in the graph: 884, number of nodes supported by QNN: 884'
      '... CompileFromOrtGraph] fused node name: QNNExecutionProvider_QNN_<hash>_<n>_0'
      '... FinalizeGraphs completed.'
      '====== DDR bandwidth summary ======\\nspill_bytes=0\\nfill_bytes=0\\nwrite_total_bytes=..\\nread_total_bytes=..'
    """
    out = {
        "log_exists": False,
        "partition_count": None,           # SmolVLA definition: fused-node names, else FinalizeGraphs count
        "fused_node_names": [],
        "finalize_graphs_completed": 0,
        "getcapability": None,             # {partitions, nodes_in_graph, nodes_supported} (last occurrence)
        "ddr_blocks": [],                  # list of dicts with spill/fill/read/write bytes
        "ddr_raw_blocks": [],
        "all_nodes_on_qnn_line": None,
    }
    if not log_path or not os.path.exists(log_path):
        return out
    out["log_exists"] = True
    with open(log_path, "r", errors="replace") as f:
        content = f.read()

    fused = re.findall(r"fused node name:\s*(QNNExecutionProvider_QNN_[^\s]+)", content, re.IGNORECASE)
    finalized = re.findall(r"FinalizeGraphs completed", content, re.IGNORECASE)
    out["fused_node_names"] = fused
    out["finalize_graphs_completed"] = len(finalized)
    out["partition_count"] = len(fused) if fused else len(finalized)

    caps = re.findall(
        r"Number of partitions supported by QNN EP:\s*(\d+),\s*number of nodes in the graph:\s*(\d+),\s*"
        r"number of nodes supported by QNN:\s*(\d+)", content)
    if caps:
        p, n, s = caps[-1]
        out["getcapability"] = {"partitions": int(p), "nodes_in_graph": int(n), "nodes_supported_by_qnn": int(s)}

    m = re.findall(r"All nodes placed on \[([^\]]+)\]\.\s*Number of nodes:\s*(\d+)", content)
    if m:
        out["all_nodes_on_qnn_line"] = {"ep": m[-1][0], "number_of_nodes": int(m[-1][1])}

    for blk in _DDR_BLOCK_RE.findall(content):
        out["ddr_raw_blocks"].append(blk.strip())
        entry = {}
        for key in ("spill_bytes", "fill_bytes", "write_total_bytes", "read_total_bytes"):
            mm = re.search(key + r"=(\d+)", blk)
            entry[key] = int(mm.group(1)) if mm else None
        out["ddr_blocks"].append(entry)
    return out


def read_proc_status():
    """VmHWM / VmRSS (kB) of this process from /proc/self/status (Linux). None elsewhere."""
    res = {"VmHWM_kb": None, "VmRSS_kb": None}
    try:
        with open("/proc/self/status") as f:
            for line in f:
                for key in ("VmHWM", "VmRSS"):
                    if line.startswith(key + ":"):
                        res[key + "_kb"] = int(line.split()[1])
    except OSError:
        pass
    return res


def ru_maxrss_kb():
    if resource is None:
        return None
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)  # kB on Linux


def lat_stats(arr):
    a = np.asarray(arr, dtype=np.float64)
    p50 = float(np.percentile(a, 50))
    p95 = float(np.percentile(a, 95))
    return {
        "n": int(a.size), "mean_ms": float(a.mean()), "p50_ms": p50, "p95_ms": p95,
        "jitter_p95_minus_p50_ms": p95 - p50, "min_ms": float(a.min()), "max_ms": float(a.max()),
    }


def to_jsonable(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not JSON serializable: {type(o)}")


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------
def build_arg_parser():
    p = argparse.ArgumentParser(description="X-VLA HTP audit runner (QNN EP on board / CPU EP on host)")
    p.add_argument("--model", required=True, help="Path to X-VLA core ONNX (x, context -> h_norm)")
    p.add_argument("--bundle", required=True, help="Path to xvla_ref_bundle_val20.npz")
    p.add_argument("--weights", default=None, help="Projector npz (default: <model dir>/xvla_io_projector_weights.npz)")
    p.add_argument("--stepwise", default=None, help="Optional xvla_ref_stepwise.npz for teacher-forced h_norm parity (frames 0-4)")
    p.add_argument("--label", required=True, help="Label for this audit run")
    p.add_argument("--provider", choices=["qnn", "cpu"], default="qnn")
    p.add_argument("--out", default=None, help="JSON report path (default: <log-dir>/xvla_audit_<label>.json)")
    p.add_argument("--log-dir", default="/tmp", help="Where verbose QNN logs / ORT profile files go (default /tmp)")
    # QNN options (same three the SmolVLA runner hard-codes)
    p.add_argument("--backend-path", default="/usr/lib/libQnnHtp.so")
    p.add_argument("--htp-performance-mode", default="burst")
    p.add_argument("--enable-htp-fp16-precision", default="1")
    p.add_argument("--qnn-opt", action="append", default=[], metavar="KEY=VALUE",
                   help="Extra QNN provider option (repeatable), e.g. --qnn-opt vtcm_mb=8")
    p.add_argument("--no-profiling", action="store_true", help="Disable ORT profiling (QNN: CPU-node audit then unavailable)")
    p.add_argument("--no-fallback-diagnostic", action="store_true",
                   help="If the no-CPU-fallback QNN session fails, abort instead of re-creating a diagnostic session with fallback allowed")
    p.add_argument("--intra-op-threads", type=int, default=0, help="ORT intra-op threads (0 = ORT default). Useful on shared hosts.")
    p.add_argument("--warmup", type=int, default=3, help="Warm-up runs excluded from latency stats (default 3)")
    p.add_argument("--max-frames", type=int, default=0, help="Smoke-test only: limit the rollout to N frames (report is flagged partial)")
    # Optional reproduction check (e.g. G3 on host)
    p.add_argument("--expect-mae-unnorm", type=float, default=None)
    p.add_argument("--expect-mae-unnorm-tol", type=float, default=1e-3)
    p.add_argument("--expect-mae-norm", type=float, default=None)
    p.add_argument("--expect-mae-norm-tol", type=float, default=1e-4)
    return p


def make_cast_feed(sess_input_types):
    def cast_feed(name, arr):
        expected = sess_input_types.get(name, "")
        if "float16" in expected:
            return arr.astype(np.float16)
        elif "float" in expected:
            return arr.astype(np.float32)
        elif "bool" in expected:
            return arr.astype(bool)
        elif "int64" in expected:
            return arr.astype(np.int64)
        return arr
    return cast_feed


def create_session(args, model_path, report, log_dir):
    """Returns (sess, init_time_ms, verbose_log_path or None, state dict)."""
    label = args.label
    state = {"fallback_disabled_requested": args.provider == "qnn", "fallback_disabled_success": None,
             "fallback_diagnostic_session": False, "fallback_error": ""}

    if args.provider == "cpu":
        so = ort.SessionOptions()
        if args.intra_op_threads > 0:
            so.intra_op_num_threads = args.intra_op_threads
        t0 = time.perf_counter()
        sess = ort.InferenceSession(str(model_path), so, providers=["CPUExecutionProvider"])
        return sess, (time.perf_counter() - t0) * 1000.0, None, state

    # ---- QNN ----
    if "QNNExecutionProvider" not in ort.get_available_providers():
        raise RuntimeError("QNNExecutionProvider is not available in this onnxruntime build "
                           f"(available: {ort.get_available_providers()}). Use --provider cpu on hosts without the QNN EP.")
    qnn_opts = {
        "backend_path": args.backend_path,
        "htp_performance_mode": args.htp_performance_mode,
        "enable_htp_fp16_precision": args.enable_htp_fp16_precision,
    }
    for kv in args.qnn_opt:
        k, _, v = kv.partition("=")
        qnn_opts[k] = v
    report["qnn_provider_options"] = dict(qnn_opts)

    def make_so(prefix, nofallback):
        so = ort.SessionOptions()
        if nofallback:
            so.add_session_config_entry("session.disable_cpu_ep_fallback", "1")
        if not args.no_profiling:
            so.enable_profiling = True
            so.profile_file_prefix = prefix
        so.log_severity_level = 0
        so.log_verbosity_level = 0
        if args.intra_op_threads > 0:
            so.intra_op_num_threads = args.intra_op_threads
        return so

    verbose_log = os.path.join(log_dir, f"qnn_verbose_{label}.log")
    if os.path.exists(verbose_log):
        os.remove(verbose_log)
    so = make_so(os.path.join(log_dir, f"ort_profile_{label}"), True)
    print("\nAttempting session creation with fallback DISABLED (session.disable_cpu_ep_fallback = 1)...", flush=True)
    t0 = time.perf_counter()
    sess = None
    with CaptureFD(verbose_log):
        try:
            sess = ort.InferenceSession(str(model_path), so, providers=[("QNNExecutionProvider", qnn_opts)])
            state["fallback_disabled_success"] = True
        except Exception as e:  # noqa: BLE001
            state["fallback_disabled_success"] = False
            state["fallback_error"] = str(e)
    init_ms = (time.perf_counter() - t0) * 1000.0

    if state["fallback_disabled_success"]:
        print(f"Session initialized successfully with fallback DISABLED in {init_ms:.1f} ms!", flush=True)
        return sess, init_ms, verbose_log, state

    print("GATE G4 FAILURE: session creation FAILED with fallback disabled:", flush=True)
    print(f"  Error: {state['fallback_error']}", flush=True)
    if args.no_fallback_diagnostic:
        raise RuntimeError("QNN session creation failed with fallback disabled: " + state["fallback_error"])
    print("\nRe-creating session with fallback ALLOWED for diagnostics...", flush=True)
    state["fallback_diagnostic_session"] = True
    fb_log = os.path.join(log_dir, f"qnn_verbose_{label}_fallback.log")
    so2 = make_so(os.path.join(log_dir, f"ort_profile_{label}_fallback"), False)
    t1 = time.perf_counter()
    with CaptureFD(fb_log):
        sess = ort.InferenceSession(str(model_path), so2, providers=[("QNNExecutionProvider", qnn_opts), "CPUExecutionProvider"])
    init_ms = (time.perf_counter() - t1) * 1000.0
    print(f"Fallback session initialized in {init_ms:.1f} ms.", flush=True)
    return sess, init_ms, fb_log, state


def main():
    args = build_arg_parser().parse_args()
    model_path = Path(args.model)
    bundle_path = Path(args.bundle)
    weights_path = Path(args.weights) if args.weights else model_path.parent / "xvla_io_projector_weights.npz"
    stepwise_path = Path(args.stepwise) if args.stepwise else None
    label = args.label
    log_dir = args.log_dir
    os.makedirs(log_dir, exist_ok=True)
    out_path = Path(args.out) if args.out else Path(log_dir) / f"xvla_audit_{label}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print(f"       X-VLA HTP AUDIT RUNNER ({RUNNER_VERSION}): {label}")
    print("=" * 80)
    print(f"Provider    : {args.provider}")
    print(f"Model       : {model_path}")
    print(f"Bundle      : {bundle_path}")
    print(f"Weights     : {weights_path}")
    print(f"Stepwise    : {stepwise_path}")
    print(f"Output JSON : {out_path}")
    print(f"python {platform.python_version()}  numpy {np.__version__}  onnxruntime {ort.__version__}")
    print(f"ORT available providers: {ort.get_available_providers()}")
    print(f"OMP_NUM_THREADS       : {os.environ.get('OMP_NUM_THREADS', 'Not set')}")
    print(f"OPENBLAS_NUM_THREADS  : {os.environ.get('OPENBLAS_NUM_THREADS', 'Not set')}")

    report = {
        "runner": RUNNER_VERSION, "label": label, "provider": args.provider,
        "model_path": str(model_path), "bundle_path": str(bundle_path),
        "weights_path": str(weights_path), "stepwise_path": str(stepwise_path) if stepwise_path else None,
        "args": vars(args),
        "environment": {
            "python": platform.python_version(), "numpy": np.__version__, "onnxruntime": ort.__version__,
            "available_providers": ort.get_available_providers(), "platform": platform.platform(),
            "machine": platform.machine(), "node": platform.node(), "cpu_count": os.cpu_count(),
            "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"),
            "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS"),
        },
        "error": None,
    }

    def finish_error(msg, code=2):
        report["error"] = msg
        print(f"\nFATAL: {msg}", flush=True)
        with open(out_path, "w") as f:
            json.dump(report, f, indent=2, default=to_jsonable)
        print(f"Saved (error) audit JSON to: {out_path}")
        sys.exit(code)

    # ---- Session first (before loading data) so VmHWM right after creation brackets FinalizeGraphs ----
    mem = {"baseline_before_session": read_proc_status()}
    try:
        sess, init_time_ms, verbose_log, sstate = create_session(args, model_path, report, log_dir)
    except Exception as e:  # noqa: BLE001
        finish_error(f"session creation failed: {e}")
    mem["after_session_create"] = read_proc_status()
    session_providers = sess.get_providers()
    report["environment"]["session_providers"] = session_providers
    if args.provider == "qnn" and "QNNExecutionProvider" not in session_providers:
        finish_error(f"QNN requested but session providers are {session_providers}")

    sess_input_types = {i.name: i.type for i in sess.get_inputs()}
    sess_output_types = {o.name: o.type for o in sess.get_outputs()}
    print(f"\nModel input types : {sess_input_types}")
    print(f"Model output types: {sess_output_types}")
    print(f"Session providers : {session_providers}")
    if set(sess_input_types) != {"x", "context"}:
        finish_error(f"unexpected model inputs {sorted(sess_input_types)} (expected x, context)")
    cast_feed = make_cast_feed(sess_input_types)

    # ---- Load data (all arrays materialised once; npz access is lazy and re-decompresses per access) ----
    print("\nLoading reference bundle...", flush=True)
    bz = np.load(bundle_path)
    b = {k: bz[k] for k in bz.files}
    prefix_contexts = b["prefix_contexts"]            # (20, 232, 1024)
    noises = b["noises"]                              # (20, 1, 50, 20)
    proprios = b["proprios"]                          # (20, 20)
    domain_ids = b["domain_ids"]                      # (20,)
    pred_torch_all = b["pred_torch"].reshape(-1, 6)   # (1000, 6)
    ground_truth_all = b["ground_truth"].reshape(-1, 6)
    valid_all = b["valid_mask"].flatten().astype(bool)
    action_mean = b["action_mean"].flatten()
    action_std = b["action_std"].flatten()
    action_min = b["action_min"].flatten()
    action_max = b["action_max"].flatten()
    dataset_max_delta = float(b["dataset_max_delta"])
    n_total = prefix_contexts.shape[0]
    num_frames = n_total if args.max_frames <= 0 else min(args.max_frames, n_total)
    partial = num_frames != n_total
    pred_torch = pred_torch_all[: num_frames * 50]
    ground_truth = ground_truth_all[: num_frames * 50]
    valid_mask = valid_all[: num_frames * 50]
    if partial:
        print(f"WARNING: --max-frames set: rollout limited to {num_frames}/{n_total} frames (partial run).")

    print("Loading XVLAHostProjector...", flush=True)
    projector = XVLAHostProjector(weights_path)

    # ---- Warm-up ----
    f0_ctx = cast_feed("context", prefix_contexts[0].reshape(1, 232, 1024))
    f0_x1 = noises[0].reshape(1, 50, 20)
    f0_prop = proprios[0].reshape(1, 20)
    f0_dom = int(domain_ids[0])
    print(f"\nRunning {args.warmup} warmup passes...", flush=True)
    for w in range(args.warmup):
        t0 = time.perf_counter()
        x_in = projector.project_in(f0_x1, f0_prop, 1.0, f0_dom)   # t=1 -> x_t = x1
        h = sess.run(None, {"x": cast_feed("x", x_in), "context": f0_ctx})[0]
        _ = projector.project_out_20(h.astype(np.float32), f0_dom)
        print(f"  Warmup {w + 1}/{args.warmup} complete in {(time.perf_counter() - t0) * 1000.0:.1f} ms", flush=True)
    mem["after_warmup"] = read_proc_status()

    # ---- Rollout: num_frames x 10 steps ----
    print(f"\nStarting {num_frames}-frame X-VLA rollout ({num_frames * NUM_STEPS} steps total)...", flush=True)
    lat_in, lat_core, lat_out, lat_total = [], [], [], []
    chunks_pred = []
    frame0_xt = []          # free-running x_t per step for frame 0 (task 3b)
    for fi in range(num_frames):
        d_id = int(domain_ids[fi])
        ctx = cast_feed("context", prefix_contexts[fi].reshape(1, 232, 1024))
        prop = proprios[fi].reshape(1, 20)
        x1 = noises[fi].reshape(1, 50, 20)
        action_loop = np.zeros_like(x1)
        for step in range(NUM_STEPS, 0, -1):
            t_val = step / NUM_STEPS
            t0 = time.perf_counter()
            x_t = x1 * t_val + action_loop * (1.0 - t_val)
            if fi == 0:
                frame0_xt.append(x_t.copy())
            x_in = projector.project_in(x_t, prop, t_val, d_id)
            feed = {"x": cast_feed("x", x_in), "context": ctx}
            t1 = time.perf_counter()
            h_norm = sess.run(None, feed)[0]
            t2 = time.perf_counter()
            action_loop = projector.project_out_20(h_norm.astype(np.float32), d_id)
            t3 = time.perf_counter()
            lat_in.append((t1 - t0) * 1000.0)
            lat_core.append((t2 - t1) * 1000.0)
            lat_out.append((t3 - t2) * 1000.0)
            lat_total.append((t3 - t0) * 1000.0)
        pred_chunk = action_loop[..., :6] * action_std + action_mean
        chunks_pred.append(pred_chunk.reshape(50, 6))
        if (fi + 1) % 5 == 0 or fi + 1 == num_frames:
            print(f"  Frame {fi + 1}/{num_frames} complete (mean step: {np.mean(lat_total[-NUM_STEPS:]):.1f} ms)...", flush=True)
    mem["after_rollout"] = read_proc_status()
    all_preds = np.concatenate(chunks_pred, axis=0)  # (num_frames*50, 6)

    # ---- Teacher-forced stepwise h_norm parity (task 3a) ----
    stepwise = {"available": False}
    if stepwise_path is not None and stepwise_path.exists():
        print("\nTask 3a: teacher-forced single-step h_norm parity vs FP32 core (frames 0-4)...", flush=True)
        szf = np.load(stepwise_path)
        sw = {k: szf[k] for k in szf.files}
        sw_xt, sw_hn = sw["stepwise_x_t"], sw["stepwise_h_norm"]  # (5,10,1,50,20), (5,10,1,50,1024)
        nsf = min(NUM_STEPWISE_FRAMES, sw_xt.shape[0])
        consistency = {
            "prefix_contexts_max_abs_diff_vs_bundle": float(np.max(np.abs(sw["prefix_contexts"][:nsf] - prefix_contexts[:nsf]))),
            "proprios_max_abs_diff_vs_bundle": float(np.max(np.abs(sw["proprios"][:nsf] - proprios[:nsf]))),
            "domain_ids_equal_bundle": bool(np.array_equal(sw["domain_ids"][:nsf], domain_ids[:nsf])),
        }
        per_step = [[] for _ in range(NUM_STEPS)]
        for fi in range(nsf):
            ctx = cast_feed("context", sw["prefix_contexts"][fi].reshape(1, 232, 1024))
            prop = sw["proprios"][fi].reshape(1, 20)
            d_id = int(sw["domain_ids"][fi])
            for s in range(NUM_STEPS):
                t_val = (NUM_STEPS - s) / NUM_STEPS
                x_in = projector.project_in(sw_xt[fi, s], prop, t_val, d_id)
                hn = sess.run(None, {"x": cast_feed("x", x_in), "context": ctx})[0].astype(np.float32)
                per_step[s].append(np.abs(hn - sw_hn[fi, s]))
        max_errs, mean_errs = [], []
        print(f"{'Step':<6s} {'t':<6s} {'Max Abs Err':<14s} {'Mean Abs Err':<14s}")
        print("-" * 44)
        for s in range(NUM_STEPS):
            d = np.stack(per_step[s])
            max_errs.append(float(d.max()))
            mean_errs.append(float(d.mean()))
            print(f"{s:<6d} {(NUM_STEPS - s) / NUM_STEPS:<6.1f} {max_errs[-1]:<14.6f} {mean_errs[-1]:<14.6f}")
        # Task 3b: frame-0 free-running x_t divergence vs the FP32 reference trajectory
        div = []
        n3b = min(len(frame0_xt), sw_xt.shape[1])
        if num_frames >= 1:
            for s in range(n3b):
                dx = np.abs(frame0_xt[s] - sw_xt[0, s])
                div.append({"step": s, "t": (NUM_STEPS - s) / NUM_STEPS, "max_abs": float(dx.max()), "mean_abs": float(dx.mean())})
        stepwise = {
            "available": True, "frames": nsf, "steps": NUM_STEPS,
            "definition": "teacher-forced: x_t, prefix_context, proprio, domain_id taken from the reference; "
                          "h_norm = core(project_in(x_t_ref, ...)) compared with stepwise_h_norm (FP32 core); "
                          "step index s=0..9 corresponds to t=(10-s)/10",
            "per_step_max_abs": max_errs, "per_step_mean_abs": mean_errs,
            "overall_max_abs": float(max(max_errs)), "overall_mean_abs": float(np.mean(mean_errs)),
            "reference_consistency": consistency,
            "frame0_free_running_xt_divergence": div,
        }
    else:
        print("\nTask 3a skipped: no --stepwise file." if stepwise_path is None else f"\nTask 3a skipped: {stepwise_path} not found.")

    # ---- Profiling end (QNN only) ----
    profile_path = None
    if args.provider == "qnn" and not args.no_profiling:
        profile_path = sess.end_profiling()
        print(f"\nProfiling output saved to: {profile_path}", flush=True)
    mem["final"] = read_proc_status()
    mem["ru_maxrss_kb"] = ru_maxrss_kb()

    # ======================================================================================
    # GATES
    # ======================================================================================
    print("\n" + "=" * 80)
    print("                ROLLOUT PARITY (X-VLA)")
    print("=" * 80)
    diff_torch = np.abs(all_preds - pred_torch)[valid_mask]
    diff_gt = np.abs(all_preds - ground_truth)[valid_mask]
    diff_torch_gt = np.abs(pred_torch - ground_truth)[valid_mask]
    mae_vs_torch = float(diff_torch.mean())
    mae_vs_gt = float(diff_gt.mean())
    mae_torch_vs_gt = float(diff_torch_gt.mean())
    torch_norm = (pred_torch - action_mean) / action_std
    pred_norm = (all_preds - action_mean) / action_std
    mae_norm = float(np.abs(pred_norm - torch_norm)[valid_mask].mean())
    gate_mae_pass = bool(mae_vs_torch <= GATE_MAE_DEG)
    print(f"valid elements                          : {int(valid_mask.sum())} / {valid_mask.size}")
    print(f"Unnormalized MAE vs PyTorch FP32 (deg)  : {mae_vs_torch:.6f}   (gate <= {GATE_MAE_DEG})")
    print(f"Normalized   MAE vs PyTorch FP32        : {mae_norm:.6f}")
    print(f"Unnormalized MAE vs Ground Truth (deg)  : {mae_vs_gt:.4f}")
    print(f"PyTorch FP32 vs Ground Truth (deg)      : {mae_torch_vs_gt:.4f}")
    print(f"MAE GATE (<= {GATE_MAE_DEG} deg): {'PASSED' if gate_mae_pass else 'FAILED'}" + ("  [PARTIAL RUN]" if partial else ""))

    mae_per_joint = [float(np.abs(all_preds[:, j] - pred_torch[:, j])[valid_mask].mean()) for j in range(6)]
    mae_per_frame = []
    for fi in range(num_frames):
        sl = slice(fi * 50, (fi + 1) * 50)
        d = np.abs(all_preds[sl] - pred_torch[sl])[valid_mask[sl]]
        mae_per_frame.append(float(d.mean()) if d.size else 0.0)
    print("\nMasked MAE per joint (deg): " + ", ".join(f"{v:.4f}" for v in mae_per_joint))

    # G7a / G7b (mirroring SmolVLA runner definitions)
    is_finite = bool(np.all(np.isfinite(all_preds)))
    margin = 0.05 * (action_max - action_min)
    lower_bound, upper_bound = action_min - margin, action_max + margin
    pred_min, pred_max = np.min(all_preds, axis=0), np.max(all_preds, axis=0)
    g7a_joint_ok = [bool(pred_min[j] >= lower_bound[j] and pred_max[j] <= upper_bound[j]) for j in range(6)]
    g7a_bounds_ok = all(g7a_joint_ok)
    gate_g7a = bool(is_finite and g7a_bounds_ok)
    print("\nG7a: finite + per-joint bounds (action_min/max +/- 5% of range):")
    for j in range(6):
        print(f"  Joint {j}: pred=[{pred_min[j]:.4f}, {pred_max[j]:.4f}] bound=[{lower_bound[j]:.4f}, {upper_bound[j]:.4f}] -> {'OK' if g7a_joint_ok[j] else 'FAIL'}")
    print(f"G7a STATUS: {'PASSED' if gate_g7a else 'FAILED'} (finite={is_finite}, bounds={g7a_bounds_ok})")

    pred_chunks = all_preds.reshape(num_frames, 50, 6)
    torch_chunks = pred_torch.reshape(num_frames, 50, 6)
    max_delta_board = np.max(np.abs(np.diff(pred_chunks, axis=1)), axis=(0, 1))
    max_delta_torch = np.max(np.abs(np.diff(torch_chunks, axis=1)), axis=(0, 1))
    allowed_jerk = 1.05 * max_delta_torch + 0.05
    g7b_joint_ok = [bool(max_delta_board[j] <= allowed_jerk[j]) for j in range(6)]
    gate_g7b = all(g7b_joint_ok)
    print("\nG7b: deployment-induced jerk  max|d_board| <= 1.05*max|d_torch| + 0.05")
    print(f"{'Joint':<6s} {'max|d_board|':<14s} {'max|d_torch|':<14s} {'allowed':<12s} status")
    for j in range(6):
        print(f"{j:<6d} {max_delta_board[j]:<14.4f} {max_delta_torch[j]:<14.4f} {allowed_jerk[j]:<12.4f} {'PASSED' if g7b_joint_ok[j] else 'FAILED'}")
    print(f"G7b STATUS: {'PASSED' if gate_g7b else 'FAILED'}")
    linf_per_joint = [float(np.max(np.abs(all_preds[:, j] - pred_torch[:, j]))) for j in range(6)]
    max_delta_gt = np.max(np.abs(np.diff(ground_truth.reshape(num_frames, 50, 6), axis=1)), axis=(0, 1))
    gate_g7 = bool(gate_g7a and gate_g7b)
    print(f"G7 REFINED STATUS: {'PASSED' if gate_g7 else 'FAILED'}")
    print(f"(informational) dataset_max_delta from bundle = {dataset_max_delta:.4f}; board max |delta| over joints = {float(max_delta_board.max()):.4f}")

    # ---- G4 / G5 (QNN only) ----
    if args.provider == "qnn":
        provider_counts, cpu_compute_nodes, cpu_copy_nodes = parse_profile_json(profile_path)
        qlog = parse_qnn_log(verbose_log)
        profiling_on = not args.no_profiling
        part_count = qlog["partition_count"]
        ddr = qlog["ddr_blocks"]
        spill_total = sum(x["spill_bytes"] for x in ddr if x["spill_bytes"] is not None) if ddr else None
        fill_total = sum(x["fill_bytes"] for x in ddr if x["fill_bytes"] is not None) if ddr else None
        cap = qlog["getcapability"]
        single_partition = bool(part_count == 1 and (cap is None or cap["partitions"] == 1))
        g4_cpu_ok = (len(cpu_compute_nodes) == 0) if profiling_on else None
        gate_g4_pass = (bool(sstate["fallback_disabled_success"] and single_partition and g4_cpu_ok)
                        if g4_cpu_ok is not None else None)
        gate_g5_spillfill = (bool(spill_total == 0 and fill_total == 0) if ddr else None)
        print("\n" + "=" * 80)
        print("                G4 / G5: EXECUTION PROVIDER, PARTITION AND VTCM AUDIT")
        print("=" * 80)
        print(f"Fallback-disabled session creation : {'SUCCESS' if sstate['fallback_disabled_success'] else 'FAILED'}")
        print(f"Fallback diagnostic session used   : {sstate['fallback_diagnostic_session']}")
        print(f"QNN partitions (fused nodes / FinalizeGraphs): {part_count}; GetCapability: {cap}")
        print(f"Node execution counts by provider  : {provider_counts if profiling_on else 'n/a (profiling disabled)'}")
        print(f"CPU compute-node events            : {len(cpu_compute_nodes) if profiling_on else 'n/a'}")
        print(f"CPU copy/memcpy events             : {len(cpu_copy_nodes) if profiling_on else 'n/a'}")
        for cnode in cpu_compute_nodes[:20]:
            print(f"    CPU node: {cnode['name']} (op {cnode['op_name']}, {cnode['dur_us']} us)")
        print(f"DDR bandwidth summary blocks found : {len(ddr)}")
        for blk in ddr:
            print(f"    {blk}")
        print(f"spill_bytes total={spill_total} fill_bytes total={fill_total}"
              + ("" if ddr else "  (NO DDR summary block found in log: spill/fill UNKNOWN, not assumed 0)"))
        print(f"G4 STATUS: {gate_g4_pass}   G5 (1 partition): {single_partition}   spill/fill==0: {gate_g5_spillfill}")
        g4 = {"applicable": True, "passed": gate_g4_pass, "fallback_disabled_success": sstate["fallback_disabled_success"],
              "fallback_diagnostic_session": sstate["fallback_diagnostic_session"], "fallback_error": sstate["fallback_error"],
              "profiling_enabled": profiling_on,
              "provider_counts": provider_counts if profiling_on else None,
              "cpu_compute_node_count": len(cpu_compute_nodes) if profiling_on else None,
              "cpu_copy_node_count": len(cpu_copy_nodes) if profiling_on else None,
              "cpu_compute_nodes": cpu_compute_nodes if profiling_on else None,
              "partitions": part_count}
        g5 = {"applicable": True, "passed": single_partition, "partitions": part_count,
              "getcapability": cap, "fused_node_names": qlog["fused_node_names"],
              "finalize_graphs_completed": qlog["finalize_graphs_completed"],
              "all_nodes_on_qnn_line": qlog["all_nodes_on_qnn_line"],
              "ddr_blocks_count": len(ddr), "ddr_blocks": ddr,
              "spill_bytes_total": spill_total, "fill_bytes_total": fill_total,
              "spill_fill_zero": gate_g5_spillfill,
              "ddr_read_total_bytes": [x["read_total_bytes"] for x in ddr] if ddr else None,
              "ddr_write_total_bytes": [x["write_total_bytes"] for x in ddr] if ddr else None,
              "log_exists": qlog["log_exists"], "log_path": verbose_log}
    else:
        na = "n/a on CPU EP"
        g4 = {"applicable": False, "passed": None, "note": na, "fallback_disabled_success": None, "provider_counts": None,
              "cpu_compute_node_count": None, "cpu_copy_node_count": None, "cpu_compute_nodes": None, "partitions": None}
        g5 = {"applicable": False, "passed": None, "note": na, "partitions": None, "spill_bytes_total": None,
              "fill_bytes_total": None, "spill_fill_zero": None, "ddr_blocks_count": None}
        print("\nG4/G5 (partition, CPU-node, VTCM spill/fill): n/a on CPU EP (reported as null).")

    # ---- Performance & resources ----
    print("\n" + "=" * 80)
    print("                PERFORMANCE & RESOURCE AUDIT")
    print("=" * 80)
    st = {"core": lat_stats(lat_core), "cpu_in": lat_stats(lat_in), "cpu_out": lat_stats(lat_out), "total_step": lat_stats(lat_total)}
    hwm_after_session = mem["after_session_create"]["VmHWM_kb"]
    hwm_final = mem["final"]["VmHWM_kb"]
    print(f"Session init time          : {init_time_ms:.1f} ms")
    print(f"VmHWM baseline / after session create / final (kB): {mem['baseline_before_session']['VmHWM_kb']} / {hwm_after_session} / {hwm_final}")
    print(f"ru_maxrss (kB)             : {mem['ru_maxrss_kb']}")
    print(f"Steps measured             : {st['core']['n']} ({num_frames} frames x {NUM_STEPS}, {args.warmup} warmups excluded; total includes projector time)")
    print(f"{'Component':<12s} {'Mean':<9s} {'p50':<9s} {'p95':<9s} {'Jitter':<9s} {'Min':<9s} {'Max':<9s}  (ms)")
    for name, key in (("Core", "core"), ("CPU-in", "cpu_in"), ("CPU-out", "cpu_out"), ("Total step", "total_step")):
        s = st[key]
        print(f"{name:<12s} {s['mean_ms']:<9.2f} {s['p50_ms']:<9.2f} {s['p95_ms']:<9.2f} {s['jitter_p95_minus_p50_ms']:<9.2f} {s['min_ms']:<9.2f} {s['max_ms']:<9.2f}")

    peak_rss_kb = hwm_final if hwm_final is not None else mem["ru_maxrss_kb"]
    g8 = {
        "init_time_ms": init_time_ms, "latency": st,
        "peak_rss_mb": (peak_rss_kb / 1024.0) if peak_rss_kb is not None else None,
        "peak_rss_source": "VmHWM(/proc/self/status)" if hwm_final is not None else "ru_maxrss",
        "vmhwm_kb_baseline_before_session": mem["baseline_before_session"]["VmHWM_kb"],
        "vmhwm_kb_after_session_create": hwm_after_session,
        "vmhwm_kb_final": hwm_final,
        "vmrss_kb_after_session_create": mem["after_session_create"]["VmRSS_kb"],
        "ru_maxrss_kb": mem["ru_maxrss_kb"],
        "vmhwm_note": "Session is created BEFORE bundle/projector are loaded, so vmhwm_kb_after_session_create "
                      "(minus baseline) brackets the host-process peak during session creation incl. FinalizeGraphs. "
                      "DSP-side / driver memory is not in VmHWM.",
        "core_p50_in_target_25_35ms_informational": (25.0 <= st["core"]["p50_ms"] <= 35.0),
        # SmolVLA-style flat keys
        "npu_mean_ms": st["core"]["mean_ms"], "npu_p50_ms": st["core"]["p50_ms"], "npu_p95_ms": st["core"]["p95_ms"],
        "npu_jitter_ms": st["core"]["jitter_p95_minus_p50_ms"],
        "step_mean_ms": st["total_step"]["mean_ms"], "step_p50_ms": st["total_step"]["p50_ms"],
        "step_p95_ms": st["total_step"]["p95_ms"], "step_jitter_ms": st["total_step"]["jitter_p95_minus_p50_ms"],
    }

    # ---- Reproduction check (optional) ----
    repro = None
    if args.expect_mae_unnorm is not None or args.expect_mae_norm is not None:
        repro = {"partial_run": partial}
        ok = True
        if args.expect_mae_unnorm is not None:
            d = abs(mae_vs_torch - args.expect_mae_unnorm)
            repro["unnorm"] = {"expected": args.expect_mae_unnorm, "tol": args.expect_mae_unnorm_tol, "measured": mae_vs_torch,
                               "abs_diff": d, "passed": bool(d <= args.expect_mae_unnorm_tol)}
            ok = ok and repro["unnorm"]["passed"]
        if args.expect_mae_norm is not None:
            d = abs(mae_norm - args.expect_mae_norm)
            repro["norm"] = {"expected": args.expect_mae_norm, "tol": args.expect_mae_norm_tol, "measured": mae_norm,
                             "abs_diff": d, "passed": bool(d <= args.expect_mae_norm_tol)}
            ok = ok and repro["norm"]["passed"]
        repro["passed"] = bool(ok and not partial)
        print("\nReproduction check: " + json.dumps(repro))

    # ---- Acceptance (handoff section 6 step 4) ----
    if args.provider == "qnn":
        accept = {
            "single_qnn_partition_no_cpu_fallback": bool(single_partition and sstate["fallback_disabled_success"]),
            "zero_cpu_compute_events": g4_cpu_ok,
            "spill_fill_zero": gate_g5_spillfill,
            "vmhwm_recorded": hwm_after_session is not None,
            "mae_le_0.35deg": gate_mae_pass,
            "g7a": gate_g7a, "g7b": gate_g7b,
            "core_latency_recorded_ms_p50": st["core"]["p50_ms"],
        }
        vals = [accept[k] for k in ("single_qnn_partition_no_cpu_fallback", "zero_cpu_compute_events", "spill_fill_zero",
                                    "vmhwm_recorded", "mae_le_0.35deg", "g7a", "g7b")]
        accept["all_pass"] = bool(all(v is True for v in vals))  # None (unknown) counts as NOT passed
    else:
        accept = {"note": "board acceptance (partition/spill/fill) not evaluable on CPU EP; only the MAE / G7 checks are meaningful",
                  "mae_le_0.35deg": gate_mae_pass, "g7a": gate_g7a, "g7b": gate_g7b,
                  "all_pass": bool(gate_mae_pass and gate_g7a and gate_g7b)}
    print("\nACCEPTANCE: " + json.dumps(accept))

    report.update({
        "session": {"init_time_ms": init_time_ms, "input_types": sess_input_types, "output_types": sess_output_types,
                    "session_providers": session_providers, "fallback_disabled_requested": sstate["fallback_disabled_requested"],
                    "fallback_disabled_success": sstate["fallback_disabled_success"],
                    "fallback_diagnostic_session": sstate["fallback_diagnostic_session"]},
        "partial_run": partial, "frames": num_frames, "steps_per_frame": NUM_STEPS,
        "rollout": {
            "mae_vs_torch_deg": mae_vs_torch, "mae_norm_vs_torch": mae_norm, "mae_vs_gt_deg": mae_vs_gt,
            "mae_torch_vs_gt_deg": mae_torch_vs_gt, "valid_elements": int(valid_mask.sum()),
            "mae_per_joint_deg": mae_per_joint, "mae_per_frame_deg": mae_per_frame,
            "linf_per_joint_deg": linf_per_joint,
        },
        "gate_g4": g4, "gate_g5": g5,
        "gate_g6": {"name": "rollout MAE vs torch <= 0.35 deg", "threshold_deg": GATE_MAE_DEG, "passed": gate_mae_pass,
                    "mae_vs_torch": mae_vs_torch, "mae_vs_gt": mae_vs_gt},
        "gate_g7": {"passed": gate_g7, "g7a_passed": gate_g7a, "g7b_passed": gate_g7b, "is_finite": is_finite,
                    "g7a_bounds_ok": g7a_bounds_ok, "g7a_joint_ok": g7a_joint_ok,
                    "pred_min": pred_min.tolist(), "pred_max": pred_max.tolist(),
                    "lower_bound": lower_bound.tolist(), "upper_bound": upper_bound.tolist(),
                    "g7b_joint_ok": g7b_joint_ok, "max_delta_board": max_delta_board.tolist(),
                    "max_delta_torch": max_delta_torch.tolist(), "allowed_jerk": allowed_jerk.tolist(),
                    "linf_per_joint": linf_per_joint, "max_delta_gt_per_joint": max_delta_gt.tolist(),
                    "dataset_max_delta": dataset_max_delta},
        "gate_g8": g8,
        "task3": {"stepwise": stepwise, "mae_per_joint": mae_per_joint, "mae_per_frame": mae_per_frame},
        "memory": mem,
        "reproduction_check": repro,
        "acceptance": accept,
        "profile_file": profile_path, "verbose_log": verbose_log,
    })
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=to_jsonable)
    print(f"\nSaved audit JSON to: {out_path}")

    failed = (accept["all_pass"] is not True) or (repro is not None and repro["passed"] is not True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
