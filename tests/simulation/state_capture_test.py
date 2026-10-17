import json
from pathlib import Path

import mujoco

REPO_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    REPO_ROOT
    / "SO-ARM100-main"
    / "Simulation"
    / "SO101"
    / "scene.xml"
)

OUTPUT_PATH = (
    REPO_ROOT
    / "research"
    / "results"
    / "SO101-49"
    / "state_capture.json"
)

model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
data = mujoco.MjData(model)

# Give the simulation a known, valid state.
mujoco.mj_resetData(model, data)
mujoco.mj_forward(model, data)

# Capture the initial joint state.
initial_state = {
    "time": float(data.time),
    "qpos": data.qpos.tolist(),
    "qvel": data.qvel.tolist(),
    "ctrl": data.ctrl.tolist(),
}

# Save the captured state to a JSON file.
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH.write_text(
    json.dumps(initial_state, indent=2),
    encoding="utf-8",
)

print(f"STATE SAVED: {OUTPUT_PATH.resolve()}")

# Change the simulation, then reset it.
data.qpos[:] = 0.1
mujoco.mj_forward(model, data)
mujoco.mj_resetData(model, data)
mujoco.mj_forward(model, data)

# Restore the saved state.
data.time = initial_state["time"]
data.qpos[:] = initial_state["qpos"]
data.qvel[:] = initial_state["qvel"]
data.ctrl[:] = initial_state["ctrl"]
mujoco.mj_forward(model, data)

# Compare the restored values with the captured values.
sizes_ok = (
    len(data.qpos) == len(initial_state["qpos"])
    and len(data.qvel) == len(initial_state["qvel"])
    and len(data.ctrl) == len(initial_state["ctrl"])
)

qpos_ok = all(
    abs(a - b) < 1e-9
    for a, b in zip(data.qpos, initial_state["qpos"])
)
qvel_ok = all(
    abs(a - b) < 1e-9
    for a, b in zip(data.qvel, initial_state["qvel"])
)
ctrl_ok = all(
    abs(a - b) < 1e-9
    for a, b in zip(data.ctrl, initial_state["ctrl"])
)

print(f"STATE SIZES: {'PASS' if sizes_ok else 'FAIL'}")
print(f"QPOS RESTORE: {'PASS' if qpos_ok else 'FAIL'}")
print(f"QVEL RESTORE: {'PASS' if qvel_ok else 'FAIL'}")
print(f"CTRL RESTORE: {'PASS' if ctrl_ok else 'FAIL'}")

if sizes_ok and qpos_ok and qvel_ok and ctrl_ok:
    print("STATE CAPTURE TEST: PASS")
else:
    print("STATE CAPTURE TEST: FAIL")
