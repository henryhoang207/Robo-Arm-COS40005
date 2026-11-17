# 0009 — Task scope: ball into a bowl (dataset episode 230)

Date: 2026-11-17 (Asia/Bangkok)
Status: Approved by Hoan in chat on 2026-11-17.
Decision owner: Hoan (PM).

## Decision

The Project A task changes from "one cube placed in one box" to **one ball placed into one bowl**, matching the recorded task in the training dataset: "Place the ball into the bowl to clear the desk."

The simulation environment is the Desk Cleanup scene added in commit `d217dd2` (`so101sim/desk_cleanup.py`). Its objects, start pose and cameras are fitted to episode 230 of `Project-IRA/TPSoSe2026_Dataset_Full_Merged_Final_LeRobot_SO101_V1`, revision `bf6f568e9ec218fff838fb266e161724ec4f7e2c`. The scene contains:

- one ball (radius 16 mm) at the episode position;
- one shallow round bowl;
- an overhead camera and a wrist camera, rendered at 640×480;
- a start pose taken from dataset frame 100.

Commit `79b9201` leaves this scene unchanged. On 2026-11-17 the model, start state and a 500-step rollout gave the same fingerprint in both commits.

This record partly supersedes:

- **Decision 0003:** the task sentence "Pick up the cube and place it in the box." with one cube and one box. All other 0003 content stands.
- **Decision 0008, item 1:** the "cube-to-box task" wording only. MuJoCo stays the simulator.
- **Decision 0008, item 3:** the console's fixed request text "Pick the cube and put it into the box". The fixed command form, with no language-model parser, stays.

## Rationale

The user's reason: the dataset. The SmolVLA checkpoint used in simulation was trained on Project-IRA SO-101 recordings of the ball-into-bowl task. `desk_cleanup.matches_checkpoint_task` checks that dataset and revision against the checkpoint's `train_config.json`. A cube-and-box scene would test the policy on a task and objects it never saw. [Reasoning]

## Alternatives rejected

- Keep one cube into one box. Rejected: it does not match the dataset.
- Use the 4-ball + box scene (`models/SO101/workspace.xml`, `board_server/`). Rejected: it is not the dataset task.

## Open items (not decided by this record)

1. **Dataset of record.** Decision 0008 item 2 still names `lerobot/svla_so100_pickplace`. Whether the Project-IRA dataset at the revision above replaces it needs Hoan's confirmation.
2. **Success rule** for ball into bowl: the inside-bowl region, release condition and settle time. No thresholds are set here. The only existing scorer, `board_server/task.py`, is written for the 4-ball scene.
3. **Board mode** (`board_server/`) still uses the 4-ball scene with its own contact and gripper settings. Moving it to the bowl task needs a physics choice and a new scorer.
4. **Console request text** must change to the new task wording.
5. **Pi0 / X-VLA baselines and the nine profiles:** check that their checkpoints and data match this task.
6. Update the Master Plan, decision 0001 (Proposed) and Jira to the new task wording.

## Amendment — 2026-11-17: one scene version only

Hoan approved this in chat on 2026-11-17. The **dataset-matched** variant (`create_simulation(match_dataset=True)`) is the only scene version from now on. The four-ball scene and the "calibrated" desk-cleanup variant are retired from the local entry points.

In the dataset-matched variant, both cameras are fitted to table, object and jaw landmarks across episode 230 and render at 640×480:

- desk camera: focal length 505.4 px;
- wrist camera: focal length 483.1 px.

The dataset records `desk_view` at 800×600 and `wrist_left` at 640×480. Both are 4:3, and the policy resizes and pads images to 512×512.

The SmolVLA checkpoint `smolvla_so101/selected_100000` was trained on 750 of 930 episodes, and episode 230 is one of them. A rollout in this scene is therefore an in-distribution check, not a held-out test.

## Sim calibration log — 2026-11-17 (laptop evidence, UNVERIFIED)

- Replay of the recorded actions (frames 100–948) with no model: ball lifted 14.0 cm, held on both pads for 4.3 s, ends resting in the bowl. Scene, start pose and joint conversion are therefore consistent with the recording.
- SmolVLA first-chunk error against recorded actions 100–149: mean over 5 arm joints and 4 seeds.

  | Images given to the model | Error |
  |---|---|
  | Real images | 3.95° |
  | Sim images, original | 6.14° |
  | Sim images, colours matched | 5.46° |

- Applied, matched variant only:
  - desk colour scaled to the measured real median (RGB 212, 209, 190);
  - bowl colour set to the measured real median (RGB 52, 77, 67).
- Ball radius 32.6 mm, estimated from the video. The real ball is a soft bean bag, about 29–37 mm depending on direction.
  - A rigid sphere that size does not fit between the jaws: 100 % opening gives a 58.9 mm pad gap with the current gripper conversion, and the replay fails with no lift.
  - **Hoan chose "bigger look, same grip" (2026-11-17).** A visual-only 32.6 mm sphere is shown to the cameras, and contact uses the 16 mm sphere.
  - Results: the rendered ball is 50.6 px wide against 49.9 px in the real video. The replay still gives a 14.0 cm lift and ends in the bowl.
  - First-chunk error with sim images is now **4.42°** (real images 3.95°, original 6.14°).
  - Known artefact: during the grasp the visual ball overlaps the jaws in the wrist view, whereas the real jaws squeeze a soft ball.
- Closed-loop rollout after the ball and colour fixes: 900 steps, seed 0, CPU, `n_action_steps` 50; run in `so101sim/runs/20261117-rollout-seed0`.
  - The gripper came within 3.0 cm of the ball centre at step 250, with the gripper about 46 % open.
  - It never closed on the ball: 0 pad contacts, and the ball did not move.
  - It moved away from step 300 onwards, and from step 550 it was closed far from the ball.
  - Joint error against the recording at the same step: 2–10° up to step 250, rising to 35–40° at steps 600–700.
  - One seed only; this is not a success rate.
- Not applied: wrist-camera field of view and distortion. The marker-based fit gave a 48 px median residual, which is not usable.

Diagnosis of the closed-loop failure, with next steps: [experiment 003 handover](../../../research/experiments/003-smolvla-grasp-closing-diagnosis/HANDOVER.md).

## Local implementation (not committed)

On Hoan's laptop, branch `local/episode-230-default` in the `C:\RobotArm` clone makes this scene the default for local mode and the laptop runners. It is not pushed. Board mode is unchanged.

## Verified by

Pending. Hoan checks the local scene following the test steps given on 2026-11-17.
