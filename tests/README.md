# Tests and validation

Keep implementation tests and repeatable validation procedures here.

| Stage | What to verify |
| --- | --- |
| Mocks | App connection/status/error handling, supported control inputs and UI |
| Computer reference | Model inputs, preprocessing and reference outputs |
| Board | Conversion comparison, prediction time, memory and sustained operation |
| Simulation | Action mapping, observation feedback, resets and communication faults |
| Physical SO-101 | Calibration, task execution, timing, stop/reset and recovery |

Record expected behavior, setup, actual outcome and evidence. Agreed test commands, cases and numerical targets: **[TBD TEAM]**.

A passed mock or simulation test does not prove physical-arm behavior.


# Tests and validation

Keep implementation tests and repeatable validation procedures here.

## 1. Test environment

- Python: 3.11.17
- MuJoCo: 3.15.0
- Simulation model: `SO-ARM100-main/Simulation/SO101/scene.xml`
- Evidence directory: `research/results/SO101-49/`

Run the tests using the project's configured Python environment with MuJoCo installed. Run commands from the repository root unless otherwise specified.

## 2. Validation stages

| Stage | What to verify | Current status |
|---|---|---|
| Mocks and binary protocol | Action/state packet encoding, valid inputs, malformed frames, CRC and replay rejection | Passed for tested cases |
| Joint control | Six-joint target execution and rejection of invalid joint targets | Passed in simulation |
| Gripper | Gripper movement and target-position error | Passed in simulation |
| Trajectory | Synchronized six-joint trajectory execution | Passed in simulation |
| Supervision | Command acceptance, replay rejection, incomplete target rejection and simulated watchdog timeout | Passed for tested cases |
| Camera rendering | Render and save both agreed camera views | Passed |
| State capture | Save and restore `time`, `qpos`, `qvel` and `ctrl` | Passed |
| Reset and step | Reset to initial state, advance one simulation step and reset again | Passed |
| Physical SO-101 | Calibration, task execution, timing, stop/reset and recovery on the physical arm | Not yet tested |

## 3. Test procedures and results

| Test file | Expected behavior | Recorded outcome |
|---|---|---|
| `tests/simulation/render_camera_views.py` | Render `top_camera` and `wrist_cam_view` and save PNG images | Both camera renders passed |
| `tests/simulation/state_capture_test.py` | Save state to JSON and restore joint position, velocity and control values | All state checks passed |
| `tests/simulation/reset_step_test.py` | Reset succeeds, simulation time advances after a step, and reset restores the initial state | All three checks passed |
| `tests/simulation/so101_controller_test.py` | Execute valid six-joint targets and reject an invalid target | Passed |
| `tests/simulation/trajectory_test.py` | Execute a synchronized six-joint trajectory | Passed |
| `tests/simulation/gripper_motion_test.py` | Move the gripper to valid targets within the configured range | Passed |
| `tests/simulation/stm32_interface_test.py` | Accept a valid action packet and reject an invalid joint target | Both test cases passed |
| `tests/simulation/supervision_test.py` | Check fresh commands, replay rejection, incomplete target rejection and watchdog timeout | All four checks passed |
| `SO-ARM100-main/Simulation/SO101/end_to_end_test.py` | Test valid command execution, replay rejection, joint-limit rejection and corrupted-frame rejection | All four checks passed |

## 4. Evidence artifacts

The following artifacts were generated during local simulation testing:

- `research/results/SO101-49/so101_top_camera.png`
- `research/results/SO101-49/so101_wrist_camera.png`
- `research/results/SO101-49/state_capture.json`

Keep the test output or screenshots with the project evidence where appropriate. Confirm that the files are tracked in Git before relying on them for review.

## 5. Limitations

- These results demonstrate behavior in the local MuJoCo simulation and software test environment only.
- The simulation does not establish that commands have been transmitted to or executed by a physical STM32H5F5 board.
- Physical SO-101 calibration, movement accuracy, grasp force, object holding, hardware watchdog behavior and recovery have not been verified by these tests.
- Numerical joint errors reported by the simulator must not be presented as measured physical-arm accuracy.

## 6. Reporting requirements

For each additional test, record the setup, test input, expected behavior, actual outcome, relevant numerical measurements and evidence artifact. Record the software revision used and any blockers or deviations. Agree on additional test cases and numerical acceptance thresholds with the team before treating them as formal acceptance criteria.

A passed mock or simulation test does not prove physical-arm behavior.
