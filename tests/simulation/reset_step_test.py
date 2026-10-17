
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

def main():
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)

    # Test 1: reset to the initial simulation state.
    mujoco.mj_resetData(model, data)
    mujoco.mj_forward(model, data)

    initial_time = data.time
    initial_qpos = data.qpos.copy()
    initial_qvel = data.qvel.copy()

    reset_ok = (
        initial_time == 0.0
        and all(abs(x) < 1e-12 for x in data.qvel)
    )

    print(f"RESET TEST: {'PASS' if reset_ok else 'FAIL'}")

    # Test 2: advance the simulation by one physics step.
    mujoco.mj_step(model, data)

    step_ok = data.time > initial_time

    print(f"STEP TEST: {'PASS' if step_ok else 'FAIL'}")
    print(f"Simulation time after step: {data.time:.6f} s")

    # Test 3: reset again after stepping.
    mujoco.mj_resetData(model, data)
    mujoco.mj_forward(model, data)

    reset_after_step_ok = (
        abs(data.time) < 1e-12
        and all(
            abs(a - b) < 1e-12
            for a, b in zip(data.qpos, initial_qpos)
        )
        and all(
            abs(a - b) < 1e-12
            for a, b in zip(data.qvel, initial_qvel)
        )
    )

    print(
        "RESET AFTER STEP TEST: "
        f"{'PASS' if reset_after_step_ok else 'FAIL'}"
    )

    if reset_ok and step_ok and reset_after_step_ok:
        print("RESET/STEP TEST: PASS")
    else:
        print("RESET/STEP TEST: FAIL")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
