#!/usr/bin/env bash
# Official on-board audit runner script for Arduino VENTUNO Q (Qualcomm Hexagon HTP v75).
# Derives from onnx-qnn-experiment board validation suite. Run directly on board host.
set -euo pipefail

PACKAGE=$(cd -- "$(dirname -- "$0")" && pwd)
PY=/home/arduino/onnx-qnn-experiment/venv/bin/python
MODEL=${1:-"xvla_denoise_core_w8a16_htp_v4.onnx"}
BUNDLE=${2:-"xvla_ref_bundle_val20.npz"}
WEIGHTS=${3:-"xvla_io_projector_weights.npz"}
STEPWISE=${4:-"xvla_ref_stepwise.npz"}
OUT=${5:-"$PACKAGE/audit_results_$(date +%Y%m%d_%H%M%S)"}
LABEL=${6:-"xvla_qnn_w8a16_v4"}

mkdir -p "$OUT"
cd "$PACKAGE"

if [ -f SHA256SUMS ]; then
  echo "[1/4] Verifying SHA256 checksums..."
  sha256sum -c SHA256SUMS > "$OUT/checksums.txt" 2>&1 || true
fi

echo "[2/4] Logging runtime environment..."
{
  date -u +%FT%TZ
  uname -a
  "$PY" --version
  "$PY" -m pip list
  dpkg-query -W qairt-libs qairt-dsp-binaries qcom-fastrpc1 || true
  free -h
  df -h "$PACKAGE"
} > "$OUT/environment.txt" 2>&1

echo "[3/4] Starting memory and telemetry monitor..."
monitor() {
  while true; do
    date -u +%FT%TZ
    grep -E 'MemAvailable:|MemFree:' /proc/meminfo
    for f in /sys/class/thermal/thermal_zone*/temp /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq; do
      if [ -r "$f" ]; then printf '%s ' "$f"; cat "$f"; fi
    done
    sleep 1
  done
}
monitor > "$OUT/telemetry.txt" 2>&1 &
MONITOR_PID=$!
trap 'kill "$MONITOR_PID" 2>/dev/null || true' EXIT

echo "[4/4] Executing HTP NPU audit runner via ORT QNN Execution Provider..."
"$PY" xvla_htp_audit_runner.py \
    --model "$MODEL" \
    --bundle "$BUNDLE" \
    --weights "$WEIGHTS" \
    --stepwise "$STEPWISE" \
    --label "$LABEL" \
    --provider qnn \
    --log-dir "$OUT" \
    --out "$OUT/${LABEL}.json" \
    2>&1 | tee "$OUT/${LABEL}.stdout.log"

echo "HTP Audit completed. Report saved at $OUT/${LABEL}.json"
