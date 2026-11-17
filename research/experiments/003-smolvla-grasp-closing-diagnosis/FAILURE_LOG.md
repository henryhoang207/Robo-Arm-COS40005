# Failure log — SmolVLA ball-into-bowl simulation (experiment 003)

Every failure seen on 2026-11-17. Each entry gives what happened, the evidence, the cause (or "unknown"), the status, and where to look next. It is written so a teammate or a new session can investigate without repeating the work.

- Context and full numbers: [HANDOVER.md](HANDOVER.md).
- Test plan and per-test results: [README.md](README.md).
- All results are **simulation-only and UNVERIFIED** by Hoan.

Status key:

- **OPEN**: not explained.
- **PARTIAL**: contributor found, not fixed.
- **FIXED**: fixed and re-checked.
- **WORKAROUND**: avoided, not fixed.
- **RULED OUT**: tested, and not the cause.

---

## A. Policy / task failures (the main problem)

### A1. SmolVLA never grasps the ball in closed loop — OPEN

- **What:** 0 grasps in all valid closed-loop runs.
  - Laptop CPU, seeds 0–4: 0/5.
  - Colab GPU, 32.6 mm visual-ball look: 0/20.
  - Colab GPU, 16 mm look: 0/20.
  - No run lifted the ball or left it in the bowl.
- **Evidence:**
  - `evidence/*rollout-seed*_summary.json` and `evidence/colab_t3fix_summaries/`;
  - per-step logs in `C:\RobotArm\so101sim\runs\` on Hoan's laptop (not in git);
  - [evidence/seed0_approach_sheet.jpg](evidence/seed0_approach_sheet.jpg).
- **Typical behaviour:**
  1. A correct approach to within 2–5 cm of the ball (about 50–70 % of runs).
  2. Then a hover with the gripper about 32 % open.
  3. Then a drift away. The joint error against the recording grows from 2–10° to 35–80° after about step 450.
- **Control check:** replaying the recorded actions in the same scene grasps the ball, lifts it 14.0 cm and ends in the bowl. So the scene can be solved.
- **Explained by:** A2, plus A3 (minor). The root cause of A2 is still unknown.

### A2. The arm hovers 2–4 cm above the grasp height and never descends — OPEN (the key failure)

- **What:** at closest approach, the jaw-pad midpoint is above the ball centre by:
  - laptop seeds 0–4: +2.2 to +6.6 cm (mean +4.2);
  - Colab median: +3.4 cm with the 32.6 mm look, +2.3 cm with the 16 mm look;
  - recorded grasp: **+0.5 cm**.
  
  The horizontal position is within about 2 cm of the recorded grasp.
- **Joints:** against the recorded grasp, the shoulder is lowered 7–11 units less and the elbow is 7–10 units straighter.
- **Evidence:** T2 in README; [scripts/t2_hover_pose.py](scripts/t2_hover_pose.py).
- **Candidate causes, not yet tested:**
  - (c) **Arm calibration:** sim joint zero offsets (`desk_cleanup.ZERO_RAD`) or link geometry differ from the real arm. The same joint angles would then put the sim gripper lower than the real one. The recorded joints grasp the sim's 16 mm-centre ball; the real ball's centre is about 33 mm high.
  - (d) **Closed-loop compounding:** small early errors put the robot in states not covered by the 750 training episodes.
  - (e) **Wrist camera** field of view and distortion are uncalibrated (see B3), so depth cues near the ball are wrong.
- **Next test:** overlay the sim arm silhouette, during the replay, on the real desk-video frames at 6–8 moments, and measure any consistent offset (HANDOVER section 6, item 2).

### A3. The gripper command never closes enough near the ball — PARTIAL

- **What:** within 5 cm of the ball, the lowest gripper command is about 32–33 % (median), against 24 % in the recording.
- **Open-loop test T1** (policy placed on the recorded path at frame 440):
  - it starts to close with every image set;
  - the lowest command is 31 % with real images, 35.8 % with sim images and the 32.6 mm visual ball, 30.9 % with sim images and the 16 mm look.
- **Cause, partly:** the enlarged visual ball covering the jaws in the wrist view weakens the close. Even with real images it reaches only 31 %, so part of the gap is the policy itself.
- **Status:** the minor visual factor is understood; it cannot be fixed while A2 keeps the arm too high.

### A4. Re-planning more often makes the approach worse — RULED OUT as a fix

- Seed 0 on the laptop, closest approach:

  | Re-plan every | Closest approach |
  |---|---|
  | 50 steps | 3.0 cm |
  | 25 steps | 22.7 cm |
  | 10 steps | 24.7 cm |

- Not investigated why; one seed only.

### A5. First predicted chunk overshoots the recorded motion — PARTIAL

- At frame 100 the first chunk has the right direction but too large an amplitude. For example, arm lift is +29° with real images, against +23° recorded.
- Mean first-chunk error over the 5 arm joints:

  | Images | Error |
  |---|---|
  | Real | 3.95° |
  | Sim, original | 6.14° |
  | Sim, colours fixed | 5.46° |
  | Sim, colours + 32.6 mm visual ball | 4.42° |

- The image fixes closed about 80 % of the sim-to-real image gap at that frame. Part of the overshoot is the policy itself.

## B. Simulation-model failures

### B1. A rigid ball of the real size cannot be grasped — WORKAROUND

- The video suggests a ball radius of about 32.6 mm (29–37 mm; a soft, flattened bean bag). The sim used 16 mm.
- A rigid 32.6 mm sphere does not fit between the jaws: 100 % open gives a 58.9 mm pad gap with the current gripper conversion. The replay then fails with no lift.
- **Workaround (Hoan's choice):** "bigger look, same grip".
  - A visual-only 32.6 mm sphere, `blue_ball_visual`.
  - The 16 mm contact sphere, hidden in group 3.
- **Side effects:**
  - in the wrist view the visual ball swallows the jaws during the grasp (feeds A3);
  - the visual ball sits 16.6 mm into the table.
- **Proper fix (needs a decision):** a soft or flex ball and a recalibrated gripper conversion, or a flattened visual ellipsoid.

### B2. Sim colours did not match the video — FIXED

- The desk rendered too bright (243, 239, 221 against real 212, 209, 190) and the bowl too dark (19, 42, 39 against 52, 77, 67).
- Fixed in `desk_cleanup.py` (matched variant). The rendered medians are now within 1 RGB unit, and the replay still passes.

### B3. Wrist camera intrinsics and distortion uncalibrated — OPEN

- The real wrist camera is wide-angle with barrel distortion; the sim is a 52.8° pinhole.
- The table-marker fit failed with a 48 px median residual, because clutter was detected as markers and the marker positions are themselves estimates.
- **Next:** fit field of view, tilt and radial distortion by whole-image matching, and apply the distortion as an image warp in `observation()`.

### B4. Episode 230 is in the training split — limitation, not a bug

- A rollout in this scene is an in-distribution sanity check, not a held-out test.

## C. Tooling and environment failures (all FIXED or WORKAROUND)

| # | Failure | Cause | Fix / workaround |
|---|---|---|---|
| C1 | `ParseXML: Error opening file …workspace.xml` | MuJoCo cannot open paths with non-ASCII characters (Hoan's OneDrive folder). `subst` and junctions do not help, because `Path.resolve()` expands them | Work in an ASCII path, e.g. `C:\RobotArm` |
| C2 | `ImportError: DLL load failed … torch._C` | `run_smolvla.py` was started while pip was still installing torch | Wait for pip to finish |
| C3 | `No module named 'lerobot'` | Same: run during the install | Same |
| C4 | `np.ptp` AttributeError | NumPy 2 removed `ndarray.ptp()` | Use `np.ptp(arr)` |
| C5 | `MUJOCO_GL=egl` invalid on Windows | EGL exists only on Linux | Use `MUJOCO_GL=egl` only on Colab/Linux; on Windows leave it unset or use `glfw` |
| C6 | Colab upload of the 865 MB checkpoint aborted (WinError 10053), including 50 MB parts | Network or upload limit through the Colab CLI | Get the checkpoint from Google Drive with `gdown --folder` on the VM ([scripts/colab/get_ckpt.py](scripts/colab/get_ckpt.py)); ask Hoan for the folder link |
| C7 | `AttributeError: module 'av' has no attribute 'option'` on Colab | Colab preinstalls `datasets`, so `lerobot.policies` imports `lerobot.datasets.pyav_utils`, which needs `av.option` (gone in PyAV 19) | `pip uninstall -y datasets` on the VM |
| C8 | `SyntaxError: invalid non-printable character U+FEFF` | PowerShell piping into `colab exec` adds a BOM | Use `colab exec -f script.py` |
| C9 | `colab exec` TimeoutError after 30 s of silence | Long silent subprocess | Launch with `nohup … &` on the VM and poll, or pass `--timeout` |
| C10 | **Colab cameras rendered pure noise** after the first rollout in a process | A second `mujoco.Renderer` was created in one process without closing the first (EGL). This invalidated 46 rollouts and produced a false "19/20 never approached" result | One seed per process, plus a noise guard in [scripts/colab/t3_rollout.py](scripts/colab/t3_rollout.py) that aborts when an image looks like noise |
| C11 | Seeds not comparable between CPU and GPU | CUDA draws the flow-matching noise from a different generator | Draw noise on the CPU and pass `noise=` (option `NOISE=cpu` in `t3_rollout.py`). The model itself matches across machines within about 0.5° with fixed noise |
| C12 | Harmless `EGLError` / `TypeError: 'NoneType' object is not callable` at process exit | MuJoCo EGL context cleanup on interpreter shutdown | Ignore |

## D. Repository issues noticed (not fixed)

- Commit `79b9201` tracks `so101sim/.board-network.json` (lab IP addresses) and `.board-mode.pid`, and removed them from `.gitignore`.
- The repo-root `CLAUDE.md` is older than the course-folder copy and still says ManiSkill.
