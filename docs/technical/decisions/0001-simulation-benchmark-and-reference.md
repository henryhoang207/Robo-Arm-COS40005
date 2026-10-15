# 0001 — Simulation benchmark, reference controller and outcome definitions (SO101-22)

Date: 2026-10-14
Status: Proposed (DRAFT)
Decision: Pending. Sections 2, 3 and 7 hold proposals awaiting Hoan's approval. The recommendation is withheld until the runnable pilot (experiment 002) and the dataset/embodiment check (experiment 001 plus a video check) have been reviewed.
Rationale: Pending.
Alternatives rejected: None yet.
Verified by: Not yet verified.

- **Decision owner:** Hoan, per `CLAUDE.md` and the Jira owner of SO101-22 and SO101-100 [15].
- **Prepared by:** Claude. Claude advises and does not decide.
- **Evidence labels:**
  - **[V]** Verified: retrieved or read this session.
  - **[M]** From memory: Hoan must check.
  - **[R]** Reasoning: Claude's own derivation.

---

## 1. What SO101-22 asks for

SO101-22 requires the following [15] [V]:

- A research question and a bounded technical contribution.
- A benchmark defined separately from the reference controller and the learned checkpoints. The benchmark is the task, environment and protocol.
- A compatibility review covering:
  - the SO101 or printed-fallback embodiment;
  - action and controller conventions;
  - the camera and state schema;
  - the selected models, compute and schedule.
- Definitions of success, execution time, inference speed and resource use, plus which measure drives conclusions. No numerical targets are invented.
- A candidate comparison, a small pilot with observations and a recommendation. Then the revisions are frozen.

Version 3 (12 Oct) already records these points [15] [V]:

- ManiSkill SO100 is the *working route*.
- Task success rate is the primary outcome.
- Task duration, board inference latency, memory, package size and failures are secondary outcomes.
- No minimum success percentage is set.
- LIBERO is "not automatically substituted".

## 2. Proposed research question and contribution (category B: needs approval)

**Question:** On a fixed simulated SO-arm pick-and-place benchmark ("Pick up the cube and place it in the box."), how does deploying SmolVLA, ACT and Diffusion Policy at FP16, INT8 and INT4 on the VENTUNO Q change task success rate? What latency, memory, package-size and failure costs come with each profile? INT8 and INT4 may use disclosed mixed precision.

**Bounded contribution:**

1. A versioned, reproducible benchmark for the SO-arm task: scene, seed lists, success rule and scripted reference controller.
2. A measured nine-profile comparison on the actual board.
3. Explicit sim-to-real limitations.

Physical performance claims remain conditional on the printed-arm branch [15].

## 3. Proposed measurement definitions (category B)

| Measure | Proposed operational definition | Reported as |
|---|---|---|
| **Task success (PRIMARY)** | An episode succeeds if the success rule (experiment 002, S11) holds before the timeout (S12). The denominator is every scheduled episode on the frozen seed list. Crashes and timeouts are failures, not exclusions. | n_success / n with a 95% Wilson interval |
| Task duration | Simulated time from reset to first success: steps ÷ control rate. Failed episodes are "not completed" and are never averaged in. Wall-clock time per episode is logged separately. | Median and range over successes, plus the count completed |
| Board inference latency | Model execution time for one action-chunk call on VENTUNO Q. The full request–response time is measured separately. Version 3 proposes 100 timed calls after 5 warm-ups [15]. | Median and p95, with call count and clock boundaries |
| Observed memory | Peak resident memory of the inference process on the board during the timed calls. Accelerator memory is added if a GPU or NPU path is used. | MB |
| Package size | On-disk size of the deployable artifact: weights plus runtime-specific files. | MB |
| Failures | Episode failure classes (experiment 002, S13), plus runtime failures: load error, out-of-memory, invalid action, timeout. | Counts by class |

**Primary measure that drives conclusions:** task success rate (already in version 3) [15] [V].

## 4. Candidate comparison

| | A. Adapted SO-arm task in ManiSkill (working route) | B. LIBERO via LeRobot | C. LeIsaac (Isaac Lab, SO101) | D. Squint SO-101 tasks (ManiSkill) | E. ManiSkill built-in SO100 tasks, as-is |
|---|---|---|---|---|---|
| **Embodiment** | SO100 model, same six joint names and order as the dataset [2][3] [V]. Parameters not identified [1] [V]. | Franka Panda in robosuite [6] [V] | SO101 follower, native [9] [V] | SO-101 URDF in ManiSkill [10] [V] | SO100 [2] [V] |
| **Task match to dataset** | Can reproduce "Pick up the cube and place it in the box." Geometry must be inferred (experiment 001). | 130 tasks, none is this one [4] [V] | PickOrange, LiftCube, CleanToyTable. No cube-in-box single-arm task [9] [V] | `SO101PlaceCube-v1`: "Pick up a cube and place in the bin" [10] [V] | `PickCubeSO100-v1` lifts to a goal point. `SO100GraspCube-v1` grasps and returns to rest [2] [V] |
| **Action / state convention** | Absolute joint positions. Experiment 001 supports degrees to radians for the pitch joints (UNVERIFIED). | 7-D end-effector delta in Box(−1, 1); 8-D state [4] [V] | Not checked. Teleoperation uses an SO101 leader arm [9] [V], so joint-space actions are likely [R]. | Joint position or delta controllers [10] [V] | Delta by default; `pd_joint_pos` available [2] [V] |
| **Cameras** | Must add `top` and `wrist`. Poses unknown. | Agent view plus wrist, 256 × 256 in the dataset table [4] [V] | Not checked | Wrist camera used for sim2real [10] [V]. Other cameras not checked. | One 128 × 128 camera [2] [V] |
| **Published baselines** | None. Reference controller plus team references. | SmolVLA 87.3%, Diffusion Policy 72.4%, OpenVLA 76.5% average. No ACT in that table [7] [V]. | None found | RL training curves only [10] [V] | None for imitation learning |
| **Compute / OS** | Runs CPU-only (this session) [V]. NVIDIA GPU for fast simulation [M]. | Linux only; MuJoCo EGL for headless [4] [V] | Isaac Sim 5.1 / Isaac Lab 2.3, Python 3.11, CUDA 12.8 [9] [V]. RTX-class GPU [M]. | RTX 3080+ with ≥10 GB for training; ManiSkill nightly [10] [V] | Same as A |
| **Effort for this team** | Moderate: scene, cameras, success rule, scripted controller | Low to run published checkpoints. High to re-scope data, training and SO-arm relevance. | High: heavy stack on student GPUs | Moderate: research code, unpinned nightly | Low, but wrong task |
| **Main risk** | Real-to-sim visual and dynamics gap gives a floor effect for real-data policies [8] | Changes the embodiment and the dataset decision (SO101-31). Needs an explicit scope decision [15]. | Same real-to-sim gap; setup time | Same gap; maintenance | Does not measure the dataset task |

## 5. Evidence gathered so far

- **E1 — runs on CPU.** ManiSkill 3.0.1 runs CPU-only with software Vulkan in Claude's workspace [V].
  - This was an exploratory smoke test run before `CLAUDE.md` was read.
  - `PickCubeSO100-v1` was created and reset in 8.6 s.
  - 20 random steps with one 128 × 128 camera took 0.41 s.
  - Single run, indicative only.
- **E2 — no built-in task matches.** None of ManiSkill's built-in SO100 tasks is the dataset task [2] [V], so an adapted scene is required.
- **E3 — dataset facts** [3] [V]:
  - 50 episodes, 19,631 frames, 30 fps, one task text.
  - Six joints in state and action, in the order shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper.
  - Cameras `top` and `wrist`, 640 × 480, AV1.
  - Created 2025-05-12. Only `train` (episodes 0–49) is published.
  - Values are consistent with degrees. For example, shoulder_lift ranges −89.8 to 41.9 and the gripper −0.2 to 34.7.
- **E4 — experiment 001 (UNVERIFIED):**
  - The identity degrees-to-radians mapping fits the three pitch joints. Grasp-hold TCP heights are 6–9 mm across three episodes.
  - The gripper hypothesis implies an object about 2.4 cm wide.
  - Pan sign and wrist-roll zero are still open.
- **E5 — current LeRobot units.** LeRobot 0.6.2 (main) defaults SO-100/101 followers to degrees for the five body joints, "for backward compatibility with previous policies/dataset". The gripper uses a 0–100 range [13] [V].
  - For the physical branch, the gripper unit and any calibration offsets between the 2025 dataset and the team's arm must be checked.
- **E6 — SmolVLA precedent.** SmolVLA used this exact dataset for its real SO100 Pick-Place task, with partial scoring (0.5 for the grasp). SO101 results used a separate SO101 pick-place dataset [7] [V]. This is a precedent for scoring, not a simulator baseline.
- **E7 — SO-101 vs SO-100.** The SO-101 is the "next-generation version of the SO-100" with "improved wiring", easier assembly and updated leader-arm motors [11] [V].
  - Follower kinematic equivalence with the ManiSkill SO100 model is **not** verified.

## 6. Main open issue (category C): what simulated success will mean

The three models are to be trained on real camera images from `svla_so100_pickplace`. A rendered ManiSkill scene will not look like those images, and its contact dynamics are not identified.

SIMPLER names "control and visual disparities between real and simulated environments" as the key challenges for evaluating real-world policies in simulation. It mitigates them before trusting simulated scores [8] [V].

If the unquantized references score zero in the scene, the primary outcome cannot separate the nine profiles. The options are set out in the decision request accompanying this draft:

- A — keep the real data and gate on a measured floor effect;
- B — simulation-generated demonstrations;
- C — visual matching;
- D — LIBERO.

## 7. Proposed gates before production comparisons (category B)

- **G1 (15 Oct, SO101-49):**
  - The scene resets and steps from the seed list.
  - Both cameras, joint state and a valid action work.
  - Run instructions have been reproduced on the team's machine.
- **G2 (16 Oct, SO101-100):**
  - Experiment 002 P1–P3 are shown with logs.
  - P4 is measured on 10 seeds with one checkpoint trained on real data.
- **G3 (validity condition, before SO101-101 protocol approval):**
  - If every unquantized learned reference scores zero on the pilot seeds, the benchmark cannot separate precision profiles. Hoan then chooses among the options in Section 6.
  - This is a validity check, not a performance target.

## 8. Revisions to freeze (proposed)

- **Dataset:** choose one revision and record it under SO101-31.
  - `lerobot/svla_so100_pickplace` @ `728583b5eaf9e739a7f119e2def466fa1d552402` (tag v3.0, LeRobot dataset format v3.0).
  - Or tag v2.1 @ `87169e502b742f989b96c952bff7af55e248d467` [3] [V].
- **Simulator:** mani-skill 3.0.1 and sapien 3.0.3, as used in the pilot.
  - The pilot used torch 2.11.0 CPU-only and Python 3.12.3.
  - The team machine's torch/CUDA build is to be recorded.
- **LeRobot:** version to be decided. Main is 0.6.2 as of 2026-10-14 [13] [V].
- **Benchmark code:** commit hash once written.
- **Checkpoints:** under SO101-52.

## 9. Unresolved questions

1. Section 6: what simulated success will mean.
2. Camera poses, pan sign and wrist-roll zero. These need `top` and `wrist` frames from at least two dataset episodes.
3. The real box size and position, and the cube size, if the team has the physical props.
4. Which checkpoint to use for the P4 gate.
5. Where the team's prepared validation/test split manifest is. Version 3 says it is ready; it was not found in the COS40005 folder.
6. SO101 vs SO100 kinematic equivalence, by URDF comparison, for the physical branch.
7. The calibration convention of the physical SO101 vs the 2025 dataset (E5).

## 10. Dependent work to update once decided

These are proposals only. Nothing has been applied to Jira.

- **SO101-49:** build the scene per experiment 002 once approved.
- **SO101-100:** acceptance evidence is the experiment 002 outputs.
- **SO101-35 / SO101-101:** inherit the Section 3 definitions, seed lists, timeout, success rule and failure classes.
- **SO101-37:** the action/state contract takes joint order and units from experiment 001. The gripper convention stays open.
- **SO101-33 / SO101-102:** final model approval needs the P4 gate result.
- **SO101-12:** the baseline training data source depends on the Section 6 choice.

## References

[1] ManiSkill documentation, "Standard Open Arm 100 (SO100)", https://maniskill.readthedocs.io/en/latest/robots/so100/ (accessed 2026-10-14). [V]

[2] ManiSkill 3.0.1 source, PyPI wheel `mani-skill==3.0.1`. Files read: `agents/robots/so100/so_100.py`, `envs/tasks/tabletop/pick_cube.py`, `pick_cube_cfgs.py`, `envs/tasks/digital_twins/so100_arm/grasp_cube.py`, `agents/robots/lerobot/manipulator.py`, `assets/robots/so100/README.md`. [V]

[3] Hugging Face Hub, `lerobot/svla_so100_pickplace`: `meta/info.json`, `meta/stats.json` (main = v3.0 = 728583b…), `meta/tasks.jsonl`, `meta/episodes.jsonl` (tag v2.1 = 87169e5…), and refs API. https://huggingface.co/datasets/lerobot/svla_so100_pickplace (accessed 2026-10-14). [V]

[4] Hugging Face, "LIBERO", LeRobot documentation, https://huggingface.co/docs/lerobot/libero (accessed 2026-10-14). [V]

[5] Hugging Face, "Adding a simulation benchmark", LeRobot documentation, https://huggingface.co/docs/lerobot/adding_benchmarks (accessed 2026-10-14). [V]

[6] LIBERO code, Lifelong-Robot-Learning/LIBERO: `libero/libero/envs/robots/__init__.py` (MountedPanda, OnTheGroundPanda) and `bddl_base_domain.py` (control_freq=20). [V] Paper: B. Liu et al., "LIBERO: Benchmarking Knowledge Transfer for Lifelong Robot Learning", arXiv:2306.03310. The venue (NeurIPS 2023 Datasets & Benchmarks) and author list are [M].

[7] SmolVLA paper, arXiv:2506.01844 (2025), Tables 2–5 and the datasets section. [V] First author "M. Shukor et al." is [M].

[8] X. Li, K. Hsu, J. Gu, K. Pertsch et al., "Evaluating Real-World Robot Manipulation Policies in Simulation", arXiv:2405.05941, 2024. Abstract read. [V]

[9] LightwheelAI, LeIsaac README (https://github.com/LightwheelAI/leisaac); LeIsaac documentation pages "Available environments" and "Installation"; Hugging Face, "LeIsaac × LeRobot EnvHub", https://huggingface.co/docs/lerobot/en/envhub_leisaac (all accessed 2026-10-14). [V]

[10] A. Almuzairee and H. I. Christensen, "Squint: Fast Visual Reinforcement Learning for Sim-to-Real Robotics", IEEE RA-L 2026, arXiv:2602.21203. Code read: README, `envs/robot/so101.py`, `envs/place.py`, `environment.yaml` at https://github.com/aalmuzairee/squint. [V for code and README; paper body not read]

[11] TheRobotStudio, SO-ARM100 repository README, https://github.com/TheRobotStudio/SO-ARM100 (accessed 2026-10-14). [V]

[12] S. Tao, `lerobot-sim2real` README, https://github.com/StoneT2000/lerobot-sim2real (accessed 2026-10-14). [V]

[13] Hugging Face LeRobot source, main branch (`pyproject.toml` version 0.6.2): `src/lerobot/robots/so_follower/config_so_follower.py`, `so_follower.py` (accessed 2026-10-14). [V]

[14] S. Tao et al., "ManiSkill3: GPU Parallelized Robotics Simulation and Rendering for Generalizable Embodied AI", RSS 2025, arXiv:2410.00425. Citation as given in [12]; paper not read. [V citation only]

[15] Local project records, read this session [V]:
- `docs/project-management/plans/SO101_Timeline_Review_and_Revised_Schedule_2026-10-12_v3.md`;
- `docs/project-management/jira/snapshots/2026-10-14.json` (SO101-21, 22, 31, 35, 37, 47, 49, 100, 101, 102);
- `research/methodology/reproduce-arm/07-evaluation-protocol.md`;
- `CLAUDE.md`.
