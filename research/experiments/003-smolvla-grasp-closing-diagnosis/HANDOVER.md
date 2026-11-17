# Handover — SmolVLA fails to grasp in the episode-230 MuJoCo scene

Written 2026-11-17 (Asia/Bangkok) at the end of a long Claude Code session, for the next session to pick up.

Read this first, then [README.md](README.md) (experiment plan and test results), then [decision 0009](../../../docs/technical/decisions/0009-task-scope-ball-into-bowl.md) (scope and calibration log).

Everything below is laptop or Colab **simulation evidence** and is **UNVERIFIED** by Hoan unless stated. No hardware was commanded.

---

## 1. One-paragraph status

The task is now **one ball into one bowl**, using Project-IRA dataset episode 230 (decision 0009, approved by Hoan).

The simulator setup is good:

- The dataset-matched MuJoCo scene reproduces the recording.
- Replaying the recorded joint actions grasps the ball, lifts it 14.0 cm and drops it in the bowl.
- This was checked on the laptop and on Colab, with identical numbers.

The learned policy fails:

- The SmolVLA checkpoint goes **0 / 5** in closed loop (seeds 0–4).
- In every run it approaches the ball correctly, then **hovers 2–7 cm too high with the gripper open and never descends or closes**, then drifts away.
- Re-planning every 25 steps instead of 50 was worse.

The leading explanation is not yet confirmed. The policy stops at about the height of the enlarged visual ball, or the sim arm calibration differs from the real arm. Section 6 has the proposed next tests and fixes.

---

## 2. Where everything is

| What | Where |
|---|---|
| Hoan's repo copy inside OneDrive (MuJoCo cannot load from it: its path has non-ASCII characters) | `…\OneDrive\<non-ASCII folder>\…\Robo-Arm_sedoitensau` |
| Working clone used for all sim runs (ASCII path) | `C:\RobotArm`, branch **`local/episode-230-default`**, **uncommitted, not pushed** |
| Code changes on that branch | [evidence/local-branch-episode-230-default.diff](evidence/local-branch-episode-230-default.diff) |
| Python venv for the sim | `C:\RobotArm\so101sim\.venv`: Python 3.13, mujoco 3.17.0, torch 2.8.0+cpu, lerobot 0.7.0, av, scipy, pandas, pyarrow |
| Same checkpoint on Google Drive (for Colab) | Team Drive. **Ask Hoan for the folder link**; it is not published in this public repo. See section 7 |
| SmolVLA checkpoint (use this one) | `C:\dev\robot-arm-conversion\staging\results\smolvla_so101\selected_100000\pretrained_model`: Project-IRA @ `bf6f568`, 750 training episodes (**episode 230 is in the training split**), 200k steps, 865 MB |
| Same weights, incomplete (no postprocessor or train_config; do not use) | `C:\dev\Robot_arm_model\_transfer-…\results\smolvla_so101\selected_100000\pretrained_model` |
| Other checkpoints and ONNX exports (Pi0, X-VLA, quantised SmolVLA) | `C:\dev\robot-arm-conversion\staging\results\*`, `C:\dev\robot-arm-conversion\deployments\handover_deployment\*` |
| Episode 230 actions and state (949 × 6, 30 Hz) | `C:\RobotArm\data\raw\desk_cleanup_episode_230.npz` (gitignored) |
| Dataset files downloaded from Hugging Face | `C:\RobotArm\data\raw\hf\project-ira\` (data parquet, episode meta, desk video `file-002.mp4`, wrist video `file-004.mp4`) |
| Hugging Face cache (SmolVLM2 config and tokenizer) | `C:\RobotArm\data\models\huggingface` (set `HF_HUB_CACHE` to this) |
| Rollout logs (per-step jsonl, per-chunk camera images, summary) | `C:\RobotArm\so101sim\runs\20261117-rollout-*` (summaries copied to [evidence/](evidence/)) |
| Analysis scripts used in this session | [scripts/](scripts/), with the Colab ones in [scripts/colab/](scripts/colab/) |

Dataset metadata (verified from Hugging Face `meta/info.json`):

- `observation.images.desk_view` at 800×600;
- `observation.images.wrist_left` at 640×480;
- 6-D state and action in degrees, gripper in 0–100 %;
- 30 fps;
- episode 230 occupies desk video file-002 from t = 601.53 s, and wrist video file-004 from t = 0.

## 3. Scene as it stands (branch `local/episode-230-default`)

- **Only one scene version is used:** `desk_cleanup.create_simulation(match_dataset=True)`.
  - The four-ball scene and the "calibrated" desk variant are retired from `app.py`, `run_smolvla.py`, `run_smolvla_onnx.py` and `replay_desk_cleanup.py`.
  - The old flags are still accepted and ignored.
  - Board mode (`board_server/`) is untouched and still uses the four-ball scene.
- **Start pose:** dataset frame 100. The episode's first 100 frames are skipped because the folded pose intersects the shoulder meshes.
- **Cameras:**
  - Overhead and wrist poses and intrinsics were fitted earlier to the episode-230 video; both render at 640×480.
  - The overhead camera matches well: the bowl width is about 190 px in both.
  - **The wrist camera is not calibrated.** The real camera is wide-angle with barrel distortion; the sim one is a pinhole with 52.8° fovy.
- **Colours** (applied 2026-11-17):
  - desk rgba 0.872, 0.874, 0.860 → rendered median RGB 212, 209, 191 (real 212, 209, 190);
  - bowl rgba 0.274, 0.421, 0.395 → rendered 51, 77, 66 (real 52, 77, 67).
- **Ball, "bigger look, same grip"** (Hoan's choice):
  - The cameras see a visual-only sphere `blue_ball_visual`, radius **32.6 mm** (estimated from the video).
  - Contact uses the original **16 mm** sphere `blue_ball_geom`, moved to geom group 3 so it is hidden. Its centre is at z = 16.5 mm.
  - The visual sphere is concentric, so its lower 16.6 mm is below the table surface. During the grasp it visibly swallows the jaws.
- **Gripper conversion:** rad = −0.170 + 0.0095 × percent.
  - The pad gap is 25.4 mm at 24 % and 58.9 mm at 100 %.
  - The recording holds the ball at 24 %.
  - A rigid 65 mm sphere cannot fit between the jaws, which is why the contact ball stays 16 mm.

## 4. What was measured (chronological, with numbers)

| # | Test | Result |
|---|---|---|
| 1 | Scene fingerprint, `d217dd2` vs `79b9201` | Identical model, start state and 500-step rollout. The episode-230 scene was untouched by the 16/11 commit |
| 2 | Replay of recorded actions (frames 100–948), no model | 849/849 targets, 0 limited. **Lift 14.0 cm, 4.3 s on both pads, ends in the bowl.** Same result on Colab, and after the colour and visual-ball changes |
| 3 | SmolVLA on the laptop CPU | Works end to end. About 40 s per 50-step prediction at first, then about 20 s. A 900-step run takes about 6–8 min |
| 4 | First predicted chunk vs recorded frames 100–149, original scene | Right direction, too far. Arm lift +51° / +17° (seeds 0 / 1) against +23° recorded |
| 5 | Real vs sim images at frame 100 (4 seeds; mean abs error over 5 arm joints) | Real + real **3.95°**; real desk + sim wrist 4.59°; sim desk + real wrist 5.77°; sim + sim **6.14°** |
| 6 | Visual differences, side by side ([before](evidence/camera_compare_before.jpg), [after](evidence/camera_compare_after_ball_colour.jpg)) | Ball too small (16 mm against about 32.6 mm, measured on 3 frames); desk too bright; bowl too dark; real wrist lens wider and distorted; no background clutter in the sim |
| 7 | Wrist-camera fit from table markers | **Failed:** 48 px median residual. Clutter was detected as markers, and the sim marker positions are themselves estimates |
| 8 | Error after the colour fix | sim + sim 6.14 → **5.46°** |
| 9 | Rigid 32.6 mm ball | Replay **fails** (0 lift): the jaws cannot open wide enough. Reverted |
| 10 | Error after the visual-only 32.6 mm ball | sim + sim → **4.42°** (real 3.95°). The visual ball measures 50.6 px against 49.9 px real |
| 11 | Closed loop, re-planning every 50 steps, seeds 0–4 | **0/5.** Closest approach 3.0 / 2.1 / 10.2 / 4.2 / 4.3 cm. 0 lifts. Seed 1 touched one pad once. No clipped targets ([seed 0 approach images](evidence/seed0_approach_sheet.jpg)) |
| 12 | Closed loop, re-planning every 25 steps, seed 0 | **Worse:** closest approach 22.7 cm, no contact |
| 13 | Closed loop, re-planning every 10 steps, seed 0 | **Was still running** when this note was written. Result will be in `C:\RobotArm\so101sim\runs\20261117-rollout-seed0-replan10\summary.json` |
| 14 | **T2:** hover pose vs recorded grasp pose | Pad midpoint minus ball centre, dz: recorded **+0.5 cm**; seeds **+3.4, +2.2, +6.6, +4.9, +3.9** (mean +4.2). Horizontal offset under 2 cm (except seed 2). The shoulder is lowered 7–11° less and the elbow is 7–10° straighter than in the recorded grasp |

Recorded gripper timing in episode 230: 31 % at frames 300–340, opens to about 43 % at 380–440, **closes to about 24 % between frames 440 and 480** (steps 340–380 from the frame-100 start), and holds to about frame 620.

### Update — later on 2026-11-17 (Colab GPU)

- **T1 (valid):** the policy was placed on the recorded path at frame 440, just before the close.
  - It starts closing with all image sets: lowest command 31 % with real images, against 24.7 % recorded.
  - The 32.6 mm visual ball in the wrist view weakens the close (35.8 %). The 16 mm look behaves like the real images (30.9 %, lowest joint error 1.5°).
- **H3:** re-planning every 25 or every 10 steps was worse than every 50 (seed 0, laptop).
- **T3 (valid rerun), 20 seeds per look: 0/40 grasps.**
  - 16 mm look: reached 10/20, median hover +2.3 cm.
  - 32.6 mm look: reached 14/20, median hover +3.4 cm.
  - The gripper bottoms out at about 32 % (recorded 24 %).
  - **Ball look is a minor factor; the hover height is the main failure.**
- The first Colab T3 batch was invalid because of the EGL noise bug (section 7).
- **Next recommended step:** the arm-calibration overlay against the desk video (section 6, item 2), then the wrist-camera fit.
- **The session ended here on 2026-11-17 at Hoan's request.** The Colab T4 session `robotarm` was stopped, so no VM is running. To resume on a GPU:
  1. `colab new -s robotarm --gpu T4`;
  2. upload `sim.zip`, rebuilt from `C:\RobotArm` (see the commands earlier in this section);
  3. run `scripts/colab/setup_env.py`, then `pip uninstall -y datasets`;
  4. run `scripts/colab/get_ckpt.py`.

## 5. Diagnosis so far

- **Not the cause:**
  - joint unit conversion and start pose (the replay works; state is identical at frame 100);
  - joint limits (no clipping);
  - checkpoint or task mismatch (the dataset revision and prompt match);
  - inference speed (physics pauses during inference).
- **Confirmed contributor:** the visual sim-to-real gap. Sim images add about 55 % to the first-chunk error; the colour and ball fixes removed about 80 % of that gap at frame 100.
- **Confirmed failure mode:** the policy stops about 4 cm above the grasp height and never descends or closes (T2).
- **Open, needs testing:**
  - (a) The **large visual ball** makes the policy stop early. Its top is 4.9 cm above the table, about where the pads stop.
  - (b) The **wrist image near the ball** is unrealistic: the visual ball swallows the jaws, and the lens is uncalibrated.
  - (c) **Arm kinematic calibration** differs between the sim SO-101 model and the real arm, for example shoulder or elbow zero offsets (`desk_cleanup.ZERO_RAD`). The recorded joints grasp the sim's 16 mm-centre ball, while the real ball's centre is about 33 mm high. If the real jaws were at about 33 mm with the same joint angles, the sim kinematics place the jaws about 1.7 cm lower than reality. A policy imitating real images would then aim higher.
  - (d) **Closed-loop compounding:** small early errors push the robot into states the policy never saw. Episode 230 was in training, but only one trajectory.

## 6. Proposed next directions (cheapest first)

1. **Run T1 and T3** (planned in [README.md](README.md); scripts ready).
   - T1, [scripts/colab/t1_grasp_moment.py](scripts/colab/t1_grasp_moment.py): at frame 440, give SmolVLA real, sim-big-ball, sim-small-ball and mixed images. Does it command the 43 % → 24 % close?
   - T3: rerun [scripts/logged_rollout.py](scripts/logged_rollout.py) with the 16 mm look. In the sim, set `geom_group` of `blue_ball_visual` to 3 and of `blue_ball_geom` to 0. Use seeds 0–2 and check whether the hover dz drops toward +0.5 cm.
   - These settle (a) and (b).
2. **Check arm calibration against the desk video** (direction (c); new, not started).
   - Replay the recorded actions and overlay the sim arm silhouette (segmentation render) on real desk frames at 6–8 moments.
   - A consistent vertical or angular offset of the gripper indicates `ZERO_RAD` or link errors.
   - Fit the 5 arm-joint offsets by minimising silhouette mismatch. Fitting from video is a category B proposal: get Hoan's approval before changing values.
3. **Calibrate the wrist camera by whole-image matching**, not markers.
   - Optimise fovy, tilt and one radial-distortion term so that sim wrist renders match real wrist frames.
   - Use edge or segmentation masks of the jaws, bowl and table markers.
   - MuJoCo has no lens distortion, so render wide and warp the image in `run_smolvla.observation()`.
4. **Better ball model.** Options:
   - a flattened ellipsoid visual (the real bean bag is about 55 × 49 px, wider than tall);
   - a MuJoCo flex or composite soft ball with the gripper conversion recalibrated so the pads squeeze a 65 mm ball at 24 %. This is the most realistic, costs days, and changes physics, so it needs a decision.
5. **Control-loop settings** (labelled experiments only; this is a control-architecture choice, category C):
   - re-planning every 50 steps fails and every 25 is worse; check the 10-step result;
   - alternatives: temporal ensembling of overlapping chunks, or a slower target-speed limit near the ball.
6. **If the visual and calibration fixes are not enough:** evaluate on held-out episodes, or fine-tune / co-train SmolVLA on simulated rollouts of the replayed trajectories (sim-to-real gap closure by training). This is a bigger change to the experiment design and needs a decision.
7. **The success rule is still undefined** (decision 0009 open item 2). Until it is set, report reached / both-pads grasp / lift > 5 cm / in bowl separately. No pass threshold has been invented.

## 7. Colab status and gotchas

- **The Colab CLI is installed and signed in:** `"$env:APPDATA\Python\Python314\Scripts\colab.exe"`. It is not on PATH. Account balance was 139.55 compute units at about 17:00.
- **Session `robotarm` (T4 GPU) was stopped on 2026-11-17** at Hoan's request; balance afterwards was 139.17.
  - A new `colab new -s robotarm --gpu T4` starts from a blank VM.
  - Setup there takes about 2 minutes: unzip the code, `apt-get install libegl1 libgl1`, then `pip install mujoco==3.17.0 'lerobot[smolvla]==0.7.0' av scipy pandas pyarrow`. See [scripts/colab/setup_env.py](scripts/colab/setup_env.py).
  - On that VM, the replay and unit tests matched the laptop exactly.
  - Rendering needs `MUJOCO_GL=egl`. A harmless EGL error is printed at process exit.
  - Another CPU session (`m-s-usc1c0-…`, probably Hoan's notebook) was left alone.
- **Uploading the checkpoint from the laptop failed:**
  - a single 865 MB upload aborted with WinError 10053;
  - 50 MB parts also failed, each after 4 retries.
- **Use Google Drive instead.** The same SmolVLA checkpoint is already on Hoan's Drive, complete with all 7 files: config, model, pre/post-processors and their normaliser stats, and `train_config.json`.

  - **The Drive folder ids are deliberately not in this public repo:** the folder is link-shared and contains the team's model. Ask Hoan for the `pretrained_model` folder link. A copy exists in Hoan's Drive and in the team's `Capsule/…/smolvla_so101/…` folder.
  - Both Drive copies are 906,712,520 bytes. Check that `train_config.json` shows Project-IRA @ `bf6f568`.
- **The Drive route worked on 2026-11-17.**
  - On the VM: `DRIVE_FOLDER_ID=<id from Hoan>` with [scripts/colab/get_ckpt.py](scripts/colab/get_ckpt.py), which runs `gdown --folder`.
  - Alternative: `colab drivemount -s robotarm` (interactive, run by the Drive owner), then copy to `/content/ckpt/pretrained_model`.
  - The downloaded `model.safetensors` sha256 starts `5d3e70bd5892550f…`, matching the laptop copy.
- **Colab EGL rendering bug (critical):** creating a second `mujoco.Renderer` in the same Python process, without closing the first, made the cameras render **pure noise**. Run one seed per process, and keep the noise guard in `t3_rollout.py`. The first 46 Colab T3 rollouts were invalidated by this.
- **Colab-only fix:** run `pip uninstall -y datasets`. Colab preinstalls `datasets`, which makes `lerobot.policies` import `lerobot.datasets.pyav_utils`, and that needs `av.option`, which PyAV 19 no longer has. The laptop has no `datasets`, so it never hits this.
- **Speed:** SmolVLA on a T4 takes about 0.5 s per prediction, against 20–40 s on the laptop CPU.
- **`colab exec`:** send scripts with `-f file.py`. Piping from PowerShell adds a BOM, which gives a SyntaxError (U+FEFF).
- **Windows paths:** MuJoCo cannot open files under the OneDrive path, because the path contains a non-ASCII (Vietnamese) folder name. `subst` drives and junctions do not help, because `Path.resolve()` expands them. Work in `C:\RobotArm`.
- **Do not run anything in the venv while pip is installing.** Hoan hit `torch` DLL-load and `No module named lerobot` errors that way.
- **NumPy 2:** use `np.ptp(arr)`, not `arr.ptp()`.

## 8. Uncommitted work (needs Hoan's decision before committing or pushing)

- `C:\RobotArm` branch `local/episode-230-default`: 6 modified files (see the diff in evidence/).
- OneDrive repo `main`, modified:
  - decisions 0003 and 0008 (supersede banners);
  - new decision 0009;
  - new experiment folder 003 (this note, README, scripts, evidence).
- `CLAUDE.md` (course folder, outside git): the scope line was updated to ball-into-bowl, and this handover is linked.
- Committed-by-others issue seen in `79b9201`: `so101sim/.board-network.json` (lab IPs) and `.board-mode.pid` are tracked, and were removed from `.gitignore`. Not fixed.
