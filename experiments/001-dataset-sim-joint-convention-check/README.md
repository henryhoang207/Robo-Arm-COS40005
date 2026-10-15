# 001 — Dataset-to-simulator joint convention check

**Status:** Plan written 2026-10-14 (Asia/Bangkok) before the analysis code. All results are **UNVERIFIED** until Hoan confirms them.
**Linked Jira work:** SO101-22 / SO101-100 (benchmark pilot), SO101-37 (action/state contract), SO101-49 (runnable simulator).
**Disclosure:** Before this plan existed, Claude installed ManiSkill 3.0.1 in its cloud workspace and ran two exploratory probes (an environment smoke test and a forward-kinematics probe of the SO100 model). No pilot code was written.

## Question

Can the six joint values in `lerobot/svla_so100_pickplace` be fed to ManiSkill's SO100 model with a plain degrees-to-radians conversion? Or does any joint need an offset or a sign change?

## Hypotheses

- **H0 — identity mapping.** The dataset values are degrees with the same zero pose and sign convention as the ManiSkill SO100 URDF.
  - Prediction 1: forward kinematics (FK) of the frames where the gripper closes on the cube puts the tool centre point (TCP) near the table plane.
  - Prediction 2: FK of the rest frames gives a folded arm above the table, not through it.
- **H1 — offset mapping.** At least one joint needs an offset or a sign flip.
  - Signs of H1: the grasp-phase TCP is far above or below the table plane, or the rest pose intersects the table.

## Setup

- **Data:** episode 0 of `lerobot/svla_so100_pickplace`, revision `main` = tag `v3.0` = `728583b5eaf9e739a7f119e2def466fa1d552402`. The episode has 454 frames at 30 fps.
  - Retrieved through the Hugging Face datasets-server rows API, state and action columns only.
  - About 30 frames are sampled across the rest, reach, grasp, transport, release and return phases.
- **Model:** ManiSkill 3.0.1 SO100 URDF (`mani_skill/assets/robots/so100/so100.urdf`), with SAPIEN 3.0.3.
  - Kinematics only: `set_qpos`, no physics.
  - Runs in Claude's cloud CPU workspace.
- **Base placement:** the robot base frame sits on the table plane (z = 0), as in ManiSkill's `SO100GraspCube-v1` digital-twin scene. Whether the dataset rig matches this is unknown; see Limitations.

## Variables

- **Independent:** the mapping candidate.
  - Identity (degrees to radians).
  - Identity plus the 6.8° elbow correction that ManiSkill's `LeRobotRealAgent` applies for `so100_follower`.
  - Wrist roll is excluded: it barely moves the TCP position.
- **Dependent:** TCP height (z, m) and horizontal reach (m) at each selected frame.

## Measurement

- TCP is the midpoint of the two jaw-tip links. This is ManiSkill's own `tcp_pos` definition.
- Gripper events are identified from the data, not chosen by eye.
  - **Grasp:** the action commands the gripper closed, but the measured state stays open. That means the jaw is blocked by the cube.
  - **Release:** the gripper opening rises while the arm is over the second location.

## Expected outcome

Not known in advance. Under H0, the grasp-phase TCP height should be at centimetre scale above the table: about the cube's half-height plus jaw-tip geometry. The dataset's cube size is not documented on its card.

## Limitations

- Only one episode is used, not all 50.
- The dataset was created on 2025-05-12, probably with LeRobot's older SO100 calibration. This has not been verified.
- ManiSkill rates its SO100 parameters as "realistic, but have not been properly identified".
- The real arm's mounting height and position relative to the table are unknown.
- This check cannot validate cameras, the gripper scale or dynamics.

## Safety

Simulation and kinematics only. No hardware is commanded.

## Results — run 2026-10-14 — UNVERIFIED

### What was run

- Frames used:
  - 49 sampled frames covering all of episode 0 (frames 0–453).
  - 16 grasp-window frames from episodes 10 and 30.
- Source: the datasets-server rows API, revision `main` (sha `728583b5…`), retrieved 2026-10-14. These are copies of rows, not a full download. Spot-check them against the Hub viewer.
- Files:
  - Data: `data/ep0_sampled_frames.csv`, `data/grasp_frames_multi_episode.csv`.
  - Scripts: `fk_check.py`, `fk_multi.py`.
  - Outputs: `results/fk_results.csv`, `results/fk_multi_results.csv`.
  - Software pins: `environment-pins.txt`.

### Grasp identification

In all three episodes the gripper **action** falls to about 5–7. The measured gripper **state** stops at 14.0–14.6. The jaw is blocked by the object, so these frames are grasp-hold frames.

### Main results

| Check | M0 identity (deg to rad) | M1 elbow −6.8° |
|---|---|---|
| TCP height at grasp-hold frames, episodes 0 / 10 / 30 | 6–7 / 8–9 / 7–8 mm | 28–29 / 32 / 29 mm |
| Horizontal reach at grasp, episodes 0 / 10 / 30 | 0.26 / 0.32 / 0.32 m | 0.28 / 0.34 / 0.34 m |
| TCP height at rest (episode 0, frames 0 and 453) | 50 mm | 75–77 mm |
| TCP height while the gripper opens (episode 0, frames 280–296) | 75–82 mm | 98–106 mm |
| Jaw-tip gap at the hold plateau, gripper hypothesis Hg (closed = −1.1 rad + dataset value in degrees) | 23.5–24.3 mm in all three episodes | same |

### Interpretation — [Reasoning]

- **H0 holds for the three pitch joints** (shoulder_lift, elbow_flex, wrist_flex).
  - The arm configurations at grasp are quite different. Episode 0 is about lift −7°, elbow 48°, wrist 25°. Episode 30 is about lift 27°, elbow −5°, wrist 52°.
  - Under H0, all of them place the TCP 6–9 mm above the base plane while holding the object.
  - A constant offset error in one of these joints would generally make these heights disagree.
- **M1 is less plausible.** M1 is the correction ManiSkill applies for the newer LeRobot calibration. It puts the jaw tips about 3 cm above the base plane while holding an object about 2.4 cm wide.
- **Gripper:** under Hg, the hold-plateau jaw gap implies an object about 2.4 cm wide, consistently across the three episodes.

### Not determined

- The sign of `shoulder_pan`, which decides which side of the robot the box is on.
- The zero of `wrist_roll`. The dataset reads about 82–109° during grasps.
  - Both need the camera videos.
- **Absolute heights** assume the arm base sits on the table plane. The data shows consistency, not the true mounting height.
- **Gripper scale (Hg)** is only self-consistent. The real cube size is not documented.
- **Coverage:** 3 of 50 episodes.

### Confidence

- H0 for the three pitch joints: **Medium**.
- Gripper scale: **Low**.
- Pan sign and roll zero: not assessed.

## How to verify

1. Re-run in the pinned environment:
   ```
   VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json python fk_multi.py
   ```
   On a GPU machine, omit `VK_ICD_FILENAMES`. You should get the numbers in the table above, to within rounding.
2. Open the Hugging Face dataset viewer for `lerobot/svla_so100_pickplace`. Compare these rows with `data/*.csv`:
   - Episode 0, frames 0, 175 and 290.
   - Episode 30, frame 200.
3. Watch the **top** camera video of episode 0 around frames 175 (grasp) and 290 (release).
   - Check whether the box is on the robot's right-hand side. Under the identity mapping, positive pan moves the TCP to −y in ManiSkill.
   - Note how the jaws are rolled.
4. If the team has the physical cube, measure it and compare with 2.4 cm.

These results are **UNVERIFIED** until Hoan confirms them.
