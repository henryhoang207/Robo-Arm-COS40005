# SO101-49 — Simulation Validation Results

## 1. Work item

- **Jira:** SO101-49
- **Contributor:** Nguyen
- **Evidence category:** Computer-based MuJoCo simulation
- **Purpose:** Prepare runnable simulator evidence for the 16 October benchmark pilot.

## 2. Setup

- Simulator: MuJoCo
- Model scene: `scene.xml`
- Joint-control test: `so101_controller_test.py`
- Gripper test: `gripper_motion_test.py`
- State capture/restore test: `state_capture_test.py`
- Camera views: `top_camera` and `wrist_cam_view`

The simulation was run locally in the `so101_sim` Conda environment. Exact dependency versions and a clean-clone reproduction procedure still need to be documented.

## 3. Results

| Check | Observed result | Status |
|---|---|---|
| Load scene | `scene.xml` loaded successfully | PASS |
| Camera registration | Two cameras detected: `top_camera`, `wrist_cam_view` | PASS |
| Top-camera rendering | `so101_top_camera.png` saved locally and uploaded | PASS |
| Wrist-camera rendering | `so101_wrist_camera.png` saved locally and uploaded | PASS |
| Six-joint control | Maximum reported position error approximately 0.000670 rad | PASS |
| Invalid joint target | Shoulder-pan target of 10 rad rejected as outside joint limits | PASS |
| Gripper movement | Two target angles reached with reported errors around 0.000003 rad or less | PASS |
| State capture/restore | qpos, qvel and ctrl restoration checks passed locally | PASS |

## 4. Limitations

- These results establish software simulation behavior only.
- No physical STM32H5F5 board or physical SO-101 arm was validated by these checks.
- Gripper movement does not demonstrate grasp force or successful object holding.
- State restoration covers qpos, qvel and ctrl; full internal simulation-state restoration has not been established.
- The 0.01 rad controller tolerance is the current test-code threshold, not a team-approved acceptance criterion.
- Camera images are MuJoCo renders, not physical camera feeds.
- The uploaded test scripts must be rerun from the repository branch before clean-checkout reproducibility can be claimed.

## 5. Evidence artifacts

- `so101_top_camera.png` — top-camera render.
- `so101_wrist_camera.png` — wrist-camera render.
- `gripper_motion_test.py` — gripper joint movement test.
- `state_capture_test.py` — qpos/qvel/ctrl capture and restoration test.

## 6. Outstanding work

- Add the camera-render script and exact run instructions.
- Verify all required model and mesh assets are available from the repository checkout.
- Re-run the tests from the documented setup and record the actual outputs.
- Obtain reviewer confirmation against the agreed SO101-49 acceptance checks.

## 7. Handover

This evidence is intended to support review and preparation for the benchmark pilot. It does not establish physical-arm equivalence or hardware success.

## Reproduction Instructions

### Prerequisites

- Python 3.11 recommended.
- MuJoCo installed in the active Python environment.
- Pillow installed for saving rendered camera images.
- All model XML files and referenced mesh assets available in the repository.

### Repository Layout

- Model scene: `SO-ARM100-main/Simulation/SO101/scene.xml`
- Simulation tests: `tests/simulation/`
- Evidence output: `research/results/SO101-49/`

### Camera Rendering

Run `render_camera_views.py` from the simulation test suite.

Expected output files:

- `so101_top_camera.png`
- `so101_wrist_cam_view.png`

Expected console messages include `CAMERA RENDER: PASS` for both cameras and `CAMERA RENDER TEST: PASS` at the end.

### State Capture and Restore

Run `state_capture_test.py`.

Expected checks:

- `STATE SIZES: PASS`
- `QPOS RESTORE: PASS`
- `QVEL RESTORE: PASS`
- `CTRL RESTORE: PASS`
- `STATE CAPTURE TEST: PASS`

### Gripper Motion

Run `gripper_motion_test.py`.

Expected checks:

- `GRIPPER MOVEMENT: PASS`
- `GRIPPER TARGET ERROR: PASS`
- `GRIPPER MOTION TEST: PASS`

The gripper target-error threshold of 0.01 rad is provisional and has not yet been approved by the team.

### Evidence Limitations

- Results from MuJoCo are simulation evidence, not physical-arm validation.
- Camera images are rendered from the simulation, not captured from physical cameras.
- Gripper motion does not establish grasp force or object-holding capability.
- State restoration checks cover qpos, qvel, and ctrl; they do not establish restoration of every internal simulator state.
- All expected outcomes must be verified by actually rerunning the scripts. Listing an expected result does not prove that it passed.
- The SO101-49 README records local MuJoCo results for scene loading,
  camera registration and rendering, six-joint control, joint-limit
  rejection, gripper movement, and qpos/qvel/ctrl state restoration.
- The README reports a maximum six-joint position error of approximately
  0.000670 rad for its recorded simulation run.
- The controller's 0.01 rad threshold is a test-code threshold only;
  it has not been approved as the team's acceptance criterion.
- Existing camera renders and state-capture artifacts may support
  simulation evidence where relevant to the agreed test cases.
- The SO101-49 README explicitly states that physical STM32H5F5 and
  physical SO-101 validation were not performed by those checks.
- Clean-checkout reproducibility remains unconfirmed until the documented
  setup is reproduced and the scripts are rerun from a repository checkout.
- Source: research/results/SO101-49/README.md.