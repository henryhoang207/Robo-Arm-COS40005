#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
PYTHON="${SO101_PYTHON:-$HOME/.venvs/so101sim/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  printf '%s\n' 'Khong tim thay Python cua so101sim. Dat SO101_PYTHON toi Python trong venv.' >&2
  exit 1
fi
SETTINGS="$("$PYTHON" -B - <<'PY'
import json
from pathlib import Path
config = json.loads((Path.cwd().parent / 'so101sim-applab/python/config.json').read_text())
network = Path.cwd() / '.board-network.json'
if not network.exists():
    raise SystemExit('Chay setup_so101_network.ps1 trong Windows PowerShell (Administrator) truoc.')
allowed = json.loads(network.read_text())['allowed_ip']
token = config.get('sim_token', '')
if len(token) < 16 or token == 'REPLACE_WITH_YOUR_OWN_LONG_RANDOM_TOKEN':
    raise SystemExit('Token chua duoc cau hinh.')
print(allowed)
print(token)
PY
)"
export SO101_TOKEN="${SETTINGS#*$'\n'}"
ALLOWED_IP="${SETTINGS%%$'\n'*}"
export MUJOCO_GL=egl
exec "$PYTHON" -B app.py --mode board --allowed-ip "$ALLOWED_IP" --no-viewer
