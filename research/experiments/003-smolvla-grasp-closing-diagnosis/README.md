# 003 — Why SmolVLA does not close the gripper in the episode-230 sim scene

Status: In progress. T2 is done; T1 and T3 are pending. Owner: Hoan. Laptop and Colab simulation evidence only.

> **New session or teammate?**
> - Set up with [SETUP.md](SETUP.md).
> - Every failure and its status is in [FAILURE_LOG.md](FAILURE_LOG.md).
> - [HANDOVER.md](HANDOVER.md) has the full state, numbers and proposed next directions.

## Background

- Scene: the dataset-matched Desk Cleanup scene ([decision 0009](../../../docs/technical/decisions/0009-task-scope-ball-into-bowl.md)), on branch `local/episode-230-default` in `C:\RobotArm`.
  - Desk and bowl colours are matched to the video.
  - The ball has a 32.6 mm visual radius and a 16 mm contact sphere.
- Checkpoint: `smolvla_so101/selected_100000`, Project-IRA dataset at revision `bf6f568`. Episode 230 is in its training split.
- Replaying the recorded actions grasps the ball, lifts it 14.0 cm and ends in the bowl. Physics and joint conversion therefore reproduce the recording.
- Closed loop, seeds 0–4, re-planning every 50 steps: 0 of 5 grasps.
  - The gripper reaches 2–10 cm from the ball by steps 200–400.
  - It hovers there 35–60 % open and never closes, then drifts away.
- Recorded gripper command in episode 230:
  - 31 % open at frames 300–340;
  - opens to about 43 % at frames 380–440;
  - closes to about 24 % at frames 440–480 (steps 340–380 after the frame-100 start);
  - holds at 24 % to about frame 620.

## Hypotheses

- **H1 (wrist image).** Near the ball, the sim wrist image is unlike the training images:
  - the large visual ball overlaps the jaws, whereas the real jaws squeeze a soft ball;
  - the lens is narrower and has no distortion.

  As a result the policy does not output the closing command.
- **H2 (geometry/height).** The arm hovers at a pose that differs from the recorded grasp pose, for example too high or offset. The ball is then not between the pads when the policy would close, or the policy waits for a view it never gets.
  - The contact ball centre is at 16.5 mm.
  - The video suggests the real ball centre is at about 33 mm.
- **H3 (control loop).** Executing 50 targets per prediction is too coarse to correct small offsets near the ball. This is already running as a labelled experiment: re-plan every 25 and every 10 steps, seed 0.

## Tests

Each test below gives its method, measurement, decision rule and cost.

### T1 — Open-loop closing test at the grasp moment (H1)

- **Method:** use the recorded state at frame 440, just before the recorded close, and the same 4 noise seeds. Give SmolVLA these image sets:
  - A: real desk + real wrist (video frames);
  - B: sim desk + sim wrist, current scene (sim follows the recorded actions to frame 440);
  - C: as B, but with the visual ball at 16 mm;
  - D: real desk + sim wrist (current);
  - E: sim desk (current) + real wrist.
- **Measurement:** the predicted gripper command over the next 50 steps, compared with the recorded 43 % → 24 % close. Also the mean joint error against the recorded frames 440–489.
- **Decision rule:**
  - If A closes and B does not, the images are the cause.
  - D and E show which camera matters.
  - C shows whether the large visual ball helps or hurts at this moment.
  - If A also does not close, the cause is not the image gap; go to T2 or H3.
- **Cost:** about 20 predictions, roughly 15 minutes. No scene change.

### T2 — Hover pose versus recorded grasp pose (H2)

- **Method:**
  - From the seed 0–4 logs (`so101sim/runs/20261117-rollout-seed*/steps.jsonl`), take the step of closest approach.
  - Replay the recorded actions and record the gripper-frame position at frame 460, during the recorded close.
  - Compare the five joint angles and the gripper-frame position (x, y, z) with the ball's contact centre.
- **Measurement:** height and horizontal offset of the hover pose from the recorded grasp pose, in cm.
- **Decision rule:**
  - An offset above about 1.5 cm, consistently in one direction (for example always high), supports H2. Then test T4.
  - If the hover pose matches the recorded grasp pose but the gripper stays open, H2 is not the cause.
- **Cost:** seconds; existing logs plus one replay.

### T3 — Closed-loop A/B on the ball's look (H1, closed loop)

- **Method:** seeds 0–2, re-planning every 50 steps.
  - Visual ball 32.6 mm (current) against visual ball 16 mm (contact unchanged).
  - Same logging as the seed runs.
- **Measurement:** closest approach, jaw-pad contacts, lift, in bowl, and the minimum gripper command within 5 cm of the ball.
- **Decision rule:**
  - If one look produces closing near the ball and the other does not, keep that look.
  - If neither closes, the visual ball size is not the deciding factor.
- **Cost:** 6 runs, about 40 minutes.

### T4 — Only if T2 supports H2: ball height or position

- **Method:** raise the contact sphere to the video-estimated height.
  - Option a: a radius-32.6 contact sphere that collides with the table and bowl only, so the pads still grip a 16 mm core.
  - Option b: lift the ball by the measured offset.
  - Re-run the replay first; it must still grasp. Then closed loop, seeds 0–2.
- This changes scene physics, so a proposal is needed with numbers from T2 before any change.

## Run order

1. T2 (seconds).
2. T1 (about 15 minutes).
3. Read the H3 replan results that are already running.
4. T3, only if T1 points at the wrist image.
5. T4, only if T2 points at height or position.

## Safety

Simulation only; no hardware commands. Nothing here sets real-arm limits.

## Results

### T2 — 2026-11-17 (laptop, existing seed 0–4 logs; UNVERIFIED)

The table gives the jaw-pad midpoint minus the ball's contact centre, in cm, at each seed's closest approach.

| Run | Step | Gripper command | dx | dy | dz |
|---|---|---|---|---|---|
| Recorded grasp | 370 | closing, 28 % | 0.8 | −0.6 | **0.5** |
| Seed 0 | 250 | 46 % | 1.4 | −0.6 | **3.4** |
| Seed 1 | 274 | 38 % | 1.8 | −0.7 | **2.2** |
| Seed 2 | 350 | 37 % | −5.5 | −3.2 | **6.6** |
| Seed 3 | 350 | 50 % | 1.0 | 0.4 | **4.9** |
| Seed 4 | 430 | 48 % | −1.3 | 0.4 | **3.9** |

- **The hover is consistently too high:** +2.2 to +6.6 cm, mean +4.2 cm, against +0.5 cm in the recording. Horizontally it is within 2 cm of the recorded pose, except seed 2.
- Joint differences from the recorded grasp, seeds 0, 1 and 3:
  - shoulder lift 7–11 units less lowered;
  - elbow 7–10 units less flexed.
- **H2 is supported:** the policy stops above the ball and never descends to the grasp height.
- **The cause of the stop is still open:**
  - (a) the large visual ball: its top is 4.9 cm above the table, roughly where the pads stop;
  - (b) the policy's state-to-height behaviour differs from the recording for another reason.
- T3 (16 mm look against 32.6 mm look) separates (a) from (b).

### T1 — 2026-11-17 (Colab T4 GPU, about 0.5 s per prediction; UNVERIFIED)

- Setup: recorded state at frame 440, 4 seeds per image set. The sim images come from replaying the recorded actions to frame 440; the sim state there is within 3° of the recorded state.
- The recorded gripper command goes 42.2 % → 28.7 % (k = 20) → 24.7 % (k = 40); its minimum is 24.7 % at k = 34.

| Images | Mean of lowest gripper command (per-seed values) | Joint error vs recorded 440–489 |
|---|---|---|
| A real desk + real wrist | 31.1 % (28.2, 31.8, 35.7, 28.6) | 1.8° |
| B sim + sim, 32.6 mm look | **35.8 %** (35.0, 37.6, 37.5, 32.8) | 2.8° |
| C sim + sim, 16 mm look | **30.9 %** (23.9, 32.5, 41.5, 25.9) | **1.5°** |
| D real desk + sim wrist (32.6 mm look) | 35.4 % | 2.4° |
| E sim desk (32.6 mm look) + real wrist | 31.6 % | 1.8° |

- **Placed on the recorded path, the policy does start to close with every image set.** None reaches the recorded 24.7 % on average; the real images reach 31 %.
- The **32.6 mm visual ball in the wrist view weakens the close:** B and D are at about 35–36 %, against 31 % for A, C and E. The 16 mm look behaves like the real images, with the lowest joint error.
### H3 — re-planning interval, seed 0, laptop CPU

| Re-plan every | Closest approach | Contact |
|---|---|---|
| 50 steps (default) | 3.0 cm | none |
| 25 steps | 22.7 cm | none |
| 10 steps | 24.7 cm | none |

Re-planning more often made the approach worse, so H3 is not supported. One seed only.

> **INVALID — rendering bug.** On Colab (EGL), every rollout after the first in the same Python process rendered **pure noise** to both cameras. A second `mujoco.Renderer` was created without closing the first.
>
> - Only seed 0 of each batch below is valid, and so are the single-process laptop runs.
> - The "19/20 never approached" result is an artefact, and so is the CPU-noise batch (0/20 reached; seed 0 closest 8.6 cm).
> - T1 was checked and is valid: its images render correctly; B shows the big ball covering the jaws, C the small ball between them.
> - Fix: one process per seed, plus a guard that aborts when an image looks like noise ([scripts/colab/t3_rollout.py](scripts/colab/t3_rollout.py)). The rerun is under "T3 rerun" below.

### T3 rerun — 2026-11-17 (VALID; Colab T4, one process per seed, noise guard, CPU-drawn noise; UNVERIFIED)

20 seeds per look, re-planning every 50 steps, 900 steps each. "Reached" means the pad midpoint came within 5 cm of the ball centre.

| Look | Reached | Any pad contact | Both pads | Lift > 5 cm | In bowl | Median closest | Median height at closest (reached runs) | Median lowest gripper command within 5 cm |
|---|---|---|---|---|---|---|---|---|
| 16 mm | 10/20 | 7/20 | 0 | 0 | 0 | 5.0 cm | **+2.3 cm** | 33.3 % |
| 32.6 mm | 14/20 | 5/20 | 0 | 0 | 0 | 4.2 cm | **+3.4 cm** | 31.9 % |
| Recorded grasp | — | — | yes | 14 cm | yes | — | +0.5 cm | 24 % |

- **0/40 grasps with either look.**
- The approach is now consistent with the laptop CPU runs: the policy usually gets within 2–5 cm.
- The 16 mm look sits **about 1.1 cm lower** (median +2.3 against +3.4 cm) and touches the ball more often (7 against 5 runs). It reaches the ball less often (10 against 14 of 20).
- **Neither look fixes the failure.** The policy still stops about 2–3 cm above the recorded grasp height. Its gripper bottoms out around 32–33 %, against 24 % in the recording, so the pads never close on the ball.
- Conclusion: the visual ball size is a **minor** factor. The main gap is the **height of the hover**: H2, with cause (c) arm calibration or (d) closed-loop drift still open. Next step: the arm-calibration check against the desk video (HANDOVER section 6, item 2).
- Logs: `C:\RobotArm\so101sim\runs\colab-t3fix\runs\t3fix-*`. Summaries in [evidence/colab_t3fix_summaries/](evidence/colab_t3fix_summaries/).

### T3 — 2026-11-17 (Colab T4 GPU, noise drawn on the GPU generator; INVALID except seed 0, see note above)

20 seeds per look, re-planning every 50 steps, 900 steps each.

| Look | Reached < 5 cm | Any pad contact | Both pads | Lift > 5 cm | In bowl | Median closest | Height at closest (reached runs) | Lowest gripper command within 5 cm |
|---|---|---|---|---|---|---|---|---|
| 16 mm | 1/20 | 1 | 0 | 0 | 0 | 22.4 cm | +2.7 cm | 29.2 % |
| 32.6 mm | 1/20 | 0 | 0 | 0 | 0 | 25.6 cm | +4.0 cm | 33.9 % |

- **0/40 grasps.** The only run per look that reached the ball is seed 0.
  - With the 16 mm look it came down 1.3 cm lower and closed further (one pad touched).
  - Still no grasp.
- **This disagrees with the laptop CPU runs**, where 4/5 seeds reached within 2–5 cm. On the GPU, 19/20 per look never approached (closest 18–28 cm).
- **CPU/GPU numerical check** (frame-100 sim observation, one fixed noise tensor):

  | Machine | First-chunk value at step 49 |
  |---|---|
  | Colab CUDA | 13.17, −90.20, 54.27, 81.65, −91.41, 5.33 |
  | Colab CPU | 13.19, −90.24, 54.27, 81.71, −91.43, 5.24 |
  | Laptop CPU (torch 2.8) | 12.73, −90.23, 54.33, 81.90, −91.45, 5.62 |

  All agree within about 0.5°. The model and observation pipeline are equivalent across machines; the image checksums differ by 0.003 % (EGL against WGL rendering).
- The remaining difference is the **noise stream**. A CUDA run draws the flow-matching noise from the CUDA generator, so seed numbers are not comparable across devices.
- A follow-up run with noise drawn on the CPU generator was launched to check whether the approach rate depends on that; see below.

- Together with T2: in closed loop the policy never reaches this grasp pose (it hovers about 4 cm high), so the missing close is mainly a consequence of the hover. The big visual ball adds a further penalty at the grasp moment.
