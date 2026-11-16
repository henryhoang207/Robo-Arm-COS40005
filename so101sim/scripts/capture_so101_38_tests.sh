#!/usr/bin/env bash
# SO101-38 evidence: automated rejection/queue/timeout/abort tests + exact revisions (sha256) + versions.
# Run in WSL from anywhere:  bash /mnt/c/RobotArm/so101sim/scripts/capture_so101_38_tests.sh
set -u
ROOT=/mnt/c/RobotArm
OUT=$ROOT/docs/evidence/so101-38-fault-tests-2026-11-12/automated-tests
mkdir -p "$OUT"
cd "$ROOT/so101sim"
PY=${SO101_PYTHON:-python}
{
  echo "captured_at: $(date -Iseconds)"
  echo "host: $(hostname)"
  $PY -c "import sys,platform,numpy,mujoco;print('python',sys.version.split()[0]);print('platform',platform.platform());print('numpy',numpy.__version__);print('mujoco',mujoco.__version__)"
  $PY -c "import onnxruntime as o;print('onnxruntime',o.__version__)" 2>/dev/null || echo "onnxruntime: not installed"
} > "$OUT/versions.txt" 2>&1
( cd board_server && $PY -B -m unittest discover -s tests -v ) > "$OUT/board_server_unittests.txt" 2>&1; echo "exit=$?" >> "$OUT/board_server_unittests.txt"
( cd board_server && $PY -B tests/self_test.py ) > "$OUT/board_server_self_test.txt" 2>&1; echo "exit=$?" >> "$OUT/board_server_self_test.txt"
$PY -B -m unittest tests.test_board_mode -v > "$OUT/test_board_mode.txt" 2>&1; echo "exit=$?" >> "$OUT/test_board_mode.txt"
( cd "$ROOT" && sha256sum so101sim/board_mode.py so101sim/app.py so101sim/board_server/*.py so101sim/board_server/settings.json \
    so101sim/board_server/tests/*.py so101sim/tests/test_board_mode.py so101arm/python/board_runner.py \
    so101arm/python/smolvla_runner.py so101arm/python/smolvla_config.json ) > "$OUT/sha256_revisions.txt"
echo "--- summary ---"
for f in board_server_unittests board_server_self_test test_board_mode; do printf '%-26s ' "$f"; grep -E "^(Ran|OK|FAILED)|exit=" "$OUT/$f.txt" | tr '\n' ' '; echo; done
echo "Saved to $OUT"
