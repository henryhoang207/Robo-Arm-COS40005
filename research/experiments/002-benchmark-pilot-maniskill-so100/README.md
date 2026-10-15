# 002 — Executable benchmark pilot: bounded pick-and-place in ManiSkill (SO100 model)

**Status:** PLAN — **PROPOSED, NOT APPROVED.** No pilot code has been written. Building is blocked until Hoan approves or modifies the items marked **B** or **C** below.
**Jira:**
- SO101-49 — runnable simulator, due 15 Oct, Nguyen.
- SO101-100 — benchmark and reference-controller pilot acceptance, due 16 Oct, Hoan.
- Parent: SO101-22.
**Depends on:** experiment 001 (joint conventions; UNVERIFIED).

## Purpose

Show the following before any model comparison:

1. A scene for the dataset task that resets and steps from a seed. It returns the dataset's camera names, joint state and action format.
2. An automatic success and failure signal.
3. A simple reference controller that is not a learned model.
4. A fixed, repeatable list of seeded episodes.
5. Measured pilot timing, to test whether the version 3 trial budget fits.
6. A gate test: can a policy trained on the real `svla_so100_pickplace` data produce any successes in this rendered scene?

## Hypotheses

- **P1:** The same seed reproduces the same initial cube and box poses and the same scripted-controller outcome.
- **P2:** The success detector flags clear successes and flags each scripted failure case as a failure. The failure cases are: no grasp, drop outside the box, and timeout.
- **P3:** The scripted reference controller's success count over the pilot seeds is reported. **No pass threshold is set.**
- **P4 (key risk):** A policy trained only on real images will show a **floor effect** in the rendered scene, meaning near-zero success.
  - SIMPLER identifies control and visual disparities between real and simulated environments as the key challenges for this kind of evaluation [8].
  - This is to be **measured, not assumed**.

## Proposed setup — needs approval

The Basis column marks evidence as **[V]** Verified this session, **[M]** From memory, or **[R]** Reasoning.

| # | Item | Proposal | Basis | Cat. |
|---|---|---|---|---|
| S1 | Simulator and robot | ManiSkill 3.0.1, SAPIEN 3.0.3, robot uid `so100`, physx CPU or GPU backend. | Version 3 working route [15] [V]. ManiSkill rates the parameters "realistic, but have not been properly identified" [1] [V]. | Recorded route |
| S2 | Task text | "Pick up the cube and place it in the box." | Dataset task 0 [3] [V]. | A |
| S3 | Control mode and rate | Absolute joint-position targets (`pd_joint_pos`) at **30 Hz** control and **120 Hz** physics (4 substeps). | Dataset is 30 fps and its action is a 6-joint position vector [3] [V]. SmolVLA ran its real robot at 30 fps [7] [V]. The substep count is [R]. | **C** (control loop rate) |
| S4 | Joint PD gains | ManiSkill defaults: stiffness 1e3, damping 1e2, force limit 100, all joints. | [2] [V]. Not system-identified [1] [V]. | **C** (control architecture) |
| S5 | Joint mapping | Arm joints: degrees to radians, no offset. Gripper: −1.1 rad + dataset value in degrees. **Pan sign and wrist-roll zero stay open until dataset video is checked.** | Experiment 001, UNVERIFIED [R]. | B |
| S6 | Start pose | Dataset rest pose (episode 0, frame 0) mapped by S5. Initial-pose noise: none for the scored list. | [3] [V], [R]. | B |
| S7 | Cube | 24 mm cube. Density 200 kg/m³ and friction 0.3 (ManiSkill SO100 digital-twin defaults). No colour or size randomisation in the scored list. | 24 mm is inferred from experiment 001 jaw gaps [R]. Defaults from [2] [V]. | B |
| S8 | Box | Open box. **Inner size and wall height unknown.** Placeholder inner size 9 × 11 cm, walls 3 cm, from the middle of Squint's bin ranges [10] [V]. Placement from the episode-0 release point under S5: about 0.10 m forward, 0.11 m to the side of the base. The side depends on pan sign. | [R]. Replace with real dimensions if the team knows them. | **C** (workspace) |
| S9 | Cube spawn region | A rectangle covering the grasp positions seen so far: reach 0.26–0.32 m, lateral −0.04 to +0.11 m. To be refined from more episodes. | Experiment 001, 3 episodes [R]. | **C** (workspace) |
| S10 | Cameras | Names `top` and `wrist`, 640 × 480 to match the dataset keys `observation.images.top` and `observation.images.wrist`. **Poses unknown.** Placeholder poses will be labelled unvalidated until matched to dataset frames. | [3] [V]. | B |
| S11 | Success rule | Success at step *t* when all hold: cube centre inside the box's inner footprint, cube below the box rim, cube not touching either jaw, cube speed < 2 cm/s. The first success ends the episode. LeRobot-style `info["is_success"]` is returned on every step. | Adapted from Squint `SO101PlaceCube-v1` [10] [V] and the LeRobot benchmark contract [5] [V]. Thresholds are [R]. | B |
| S12 | Timeout | 600 control steps, which is 20 s at 30 Hz. | Longest demonstration is 575 frames, 19.2 s [3] [V]. | B |
| S13 | Failure classes | Never grasped / dropped outside box / grasped but not placed by timeout / unsafe contact (robot–table contact force above a logged threshold) / simulator error. | Adapted from `research/methodology/reproduce-arm/07-evaluation-protocol.md` [15] [V]. | B |
| S14 | Seeds | Pilot list: seeds 0–29. Validation and final-test seed lists are created separately and later, under SO101-35. | Version 3 budget of 30 rollouts [15] [V]. | B |
| S15 | Reference controller | Scripted and privileged: it reads the true cube and box poses. Sequence: pre-grasp above cube → descend → close → lift → move over box → open → retreat. Inverse kinematics uses the SAPIEN/Pinocchio solver. | `compute_inverse_kinematics` exists in SAPIEN 3.0.3 and is used by ManiSkill controllers [2] [V]. Design is [R]. | B |
| S16 | Policy-in-the-loop gate | One checkpoint trained on `svla_so100_pickplace`, 10 seeds. **Which checkpoint is open**: the team's quick ACT run, or a public checkpoint (quality unknown). | [R]. | **C** |

## Measurements

- **Per episode:**
  - success (bool) and first-success step;
  - stage flags: reached, grasped, lifted, over box, released;
  - failure class;
  - simulated time and wall-clock time;
  - time per physics step and per render.
- **Per pilot:** success count out of n with a 95% Wilson interval. This is for reporting, not a target.
- **Logs:**
  - one JSON line per episode;
  - `top` and `wrist` video of every failure;
  - a run manifest with package versions, seed list, dataset revision and code hash.

## Expected outcomes

- **P1 and P2:** expected to hold. Both are engineering checks.
- **P3:** unknown.
- **P4:** a floor effect is expected for real-data policies without visual matching [8] [R]. Not yet measured.

## Where it runs

- **Development:** Claude's cloud CPU workspace (software Vulkan rendering). Already shown to run ManiSkill 3.0.1.
- **Readiness evidence:** SO101-49 and SO101-100 should be reproduced on the team's own machine — the RTX 5060 PC or the school RTX 4090 server.

## Safety

Simulation only. No hardware is commanded. Any later hardware use first needs approved joint, velocity and torque limits and an e-stop path, per `CLAUDE.md`.

## References

See `docs/technical/decisions/0001-simulation-benchmark-and-reference.md` for the numbered reference list [1]–[15].
