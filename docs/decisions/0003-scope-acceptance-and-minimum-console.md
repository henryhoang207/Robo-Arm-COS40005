# 0003 — Bounded research scope, platform-specific claims and minimum console (SO101-23 / SO101-98)

Date: 2026-10-14
Status: Approved (Hoan, 2026-10-14, in chat; see §1b). Inputs still to reconcile: SO101-10 requirements list and SO101-97 rubric (§0). Open values: SO101-37 limits; the physical envelope, deferred to SO101-38 (22 Oct).
Decision: Project A minimum is simulation benchmark + nine VENTUNO Q cells + reports + minimum web console. Physical printed-arm trials are a conditional target tier. The core is a single task, "Pick up the cube and place it in the box.", with one cube and one box. Speech, free-text commands, multiple object classes, MQTT, OTA update/rollback and Cartesian controls are out of the current core. The console accepts a closed command set and rejects invalid input without starting anything. Every reported number carries its platform and evidence class (A-004). Old thresholds F04 and F05 are retired. The physical workspace, lighting, payload and supervision rules are deferred to the SO101-38 procedure gate on 22 Oct.
Rationale: The confirmed direction (S-1 to S-5) makes the physical arm conditional and sets no minimum success threshold. Version 3, decisions 0001/0002 and the dataset contain one task, and none requires the older draft features (§2) [2][3][4][6][7].
Alternatives rejected: keeping F04/F05 as acceptance or reference targets; setting physical envelope values now; physical trials in the minimum tier; keeping a closed text-command parser; keeping MQTT, rollback or Cartesian controls as core or stretch; adding a live camera to the minimum console.
Verified by: Not applicable to scope decisions. The SO101-10 and SO101-97 inputs are still to be reconciled (§0).

- **Decision owner:** Hoan (PM, SO101-23/SO101-98 assignee) [1].
- **Consumers:**
  - SO101-42 console workflow (Khanh, due 15 Oct);
  - SO101-5 sketch (Trieu, from 16 Oct);
  - SO101-22/SO101-35 benchmark and protocol;
  - SO101-106 Project Plan review (25 Oct submission) [1][2][9].
- **Prepared by:** Claude. Claude advises and does not decide.
- **Evidence labels:**
  - **[V]** Verified: read this session (14 Oct 2026).
  - **[M]** From memory: Hoan must check.
  - **[R]** Reasoning: Claude's own derivation.

---

## 0. Input status (gaps)

| Input named by SO101-23 | Status found | Effect |
|---|---|---|
| SO101-10 requirements list (Trieu, due 13 Oct) | Jira To Do. No requirements file found in the COS40005 folder [9] [V]. | This draft works from the Word plan's R01–R09 and F-fields [3] and the SoftDev AC document [4] instead. Trieu's list must be reconciled against §3 when it arrives. |
| SO101-97 / SO101-29 early rubric scan | Jira To Do. No marking rubric found. Only the D01 *template* exists [8] [V]. | §4 is a scan of the D01 template, not of the marking rubric. The Alpha expectation for Project A is still unknown (Word field X02) [3] [V]. |

## 1. Already settled. Recorded here, no new decision.

| ID | Settled item | Source |
|---|---|---|
| S-1 | Academic robot-arm performance research project. The web deliverable is an **experiment console** for control, monitoring and result collection. | User-confirmed; SO101-2/SO101-42 [1][9] [V] |
| S-2 | **Fallback acceptance:** if the printed arm is unavailable by **30 Nov 2026**, simulation and VENTUNO Q results are accepted for current deliverables. Arm availability is recorded at that checkpoint. Physical assembly, joint-position testing and physical performance claims stay conditional on an available arm and are never reported as done unless performed. | User-confirmed; SO101-23 [1] [V] |
| S-3 | **Outcomes:** task success rate is primary. Duration, board latency, memory, package size and failures are secondary. No minimum success percentage is set. | Version 3 §2 [2] [V] |
| S-4 | **Board matrix:** SmolVLA, ACT and Diffusion Policy × FP16/INT8/INT4 on the VENTUNO Q Kryo CPU (nine cells). NPU and GPU runs are exploratory and start only after the nine CPU cells exist. | Decision 0002 D1 (approved 14 Oct) [6] [V] |
| S-5 | Dataset `lerobot/svla_so100_pickplace` with the existing splits. Simulator working route: ManiSkill SO100. | Version 3 §1–2 [2] [V] |

## 1b. Approved 2026-10-14 (Hoan, in chat)

All items DR-1 to DR-7 are approved.

| ID | Approved | Still open inside it |
|---|---|---|
| DR-1 | Tiers exactly as proposed in §3. The minimum is fully non-physical. Physical trials are the target tier, gated by the 30 Nov checkpoint. | Alpha mapping, until the real rubric is found (§0) |
| DR-2 (task core) | Single task "Pick up the cube and place it in the box.", one cube, one box. Speech, free-text commands and five object classes are out of the current core. F06/F09 lapse. | Physical workspace, lighting, payload and supervision (see DR-2) |
| DR-5 | MQTT telemetry, OTA update/rollback tooling and Cartesian/XYZ controls are all out of the core; they are not stretch items either. Accelerator stays exploratory per 0002 D1. | None |
| DR-6 | Closed command set: create run / start / abort / export. Parameters are checked against frozen catalogues. Invalid input is rejected with a reason and logged, and starts nothing. Abort is always accepted. | Numeric joint, velocity and torque limits for SO101-37 (Hoan to supply) |
| DR-7 | Minimum console as proposed. Mobile client, live camera and manual jog are out of the minimum. | Hosting (SO101-9) |
| DR-2 (physical) | Physical workspace, lighting, payload and supervision rules are deferred to the SO101-38 procedure gate (22 Oct). Hoan and Chung supply the values. No powered test happens before then. | All values |
| DR-3 | Claims rule approved as assumption A-004 (`docs/assumptions.md`). | None |
| DR-4 | Principles adopted. F04 (28/40, 30 s) and F05 (12/20) are retired as acceptance criteria. Operational definitions stay with decision 0001 and SO101-35. | 0001 approval |

## 2. Conflicts between the older drafts and the confirmed direction

These conflicts are why the open decisions in §3 are needed.

| Older draft content | Source | Conflict with S-1 to S-5 |
|---|---|---|
| Physical target 28/40 successes within 30 s (F04); 12/20 PC development gate (F05) | Word plan, Framing [3] [V] | S-3 sets no minimum success percentage. Both targets assume a physical arm that S-2 makes conditional. |
| Text parser 196/200 and reject 50/50 (F06); local speech; five object classes (F09) | Word plan [3] [V] | None of these appears in version 3, decision 0001 or 0002. The dataset has one task text [7] [V]. |
| Mobile application, AC-01 to AC-12, including joint/gripper/speed/XYZ control and "selected target mobile device" (AC-12) | SoftDev AC [4] [V] | S-1 makes the deliverable a **web** experiment console. AC-06 XYZ control requires the control layer to support it [4] [V]. SmolVLA outputs continuous joint actions, not XYZ, without an extra perception/IK pipeline [3] [V]. |
| MQTT telemetry, OTA/model-registry update and rollback (A02) | Word plan [3] [V] | No source in version 3 makes them mandatory [2] [V]. |

## 3. Open decisions (category C unless marked)

### DR-1 — Minimum, target and stretch deliverables (F07) — APPROVED 2026-10-14

**Proposal for discussion, not a default:**

| Tier | Contents | Conditional on |
|---|---|---|
| **Minimum** | Versioned simulation benchmark with reference controller (SO101-22). Three trained references. Nine VENTUNO Q cells with simulation success per cell (S-4). EDA, baseline and conversion reports. Minimum console (DR-7) working against simulation and board. | Nothing physical |
| **Target** | Minimum, plus supervised physical trials on the printed arm with the same task and protocol, reported as a separate evidence class. | Arm available by 30 Nov (S-2) |
| **Stretch** | NPU/GPU exploratory profiles (S-4); console extras from DR-5. | After minimum is met |

**Gap:** Alpha expectations are unknown (§0).

### DR-2 — Core task catalogue and operating envelope (F08) — APPROVED 2026-10-14 (physical values deferred to 22 Oct)

| Field | Proposal | Basis |
|---|---|---|
| Task text | Single task: "Pick up the cube and place it in the box." | Dataset task 0 [7] [V] |
| Objects / destination | One cube, one open box | [7] [V] |
| Simulated workspace | As decided in experiment 002, S7–S10. Those items are still open there. | [7] [V] |
| Payload | Simulation only: 24 mm cube at 200 kg/m³ is about **2.8 g**. Physical payload is **not proposed**; it needs the measured mass of the real object. | Calculation below [R]; cube size UNVERIFIED (experiment 001) |
| Speech, free-text commands, multiple object classes | **Out of the current core** (Project B candidates) | §2 conflict |
| Physical workspace, lighting, supervision | **Deferred** to the physical gate. SO101-38 procedure gate is 22 Oct. Values come from Hoan/Chung; Claude does not invent them. | CLAUDE.md, always category C |

**Payload calculation [R]:**
- V = 0.024³ m³ = 1.3824 × 10⁻⁵ m³
- m = 200 kg/m³ × V = 2.76 × 10⁻³ kg ≈ 2.8 g

### DR-3 — Platform-specific claims rule (category B) — APPROVED 2026-10-14 as A-004

Every reported number carries:
- its platform: ManiSkill scene version, VENTUNO Q + CPU + runtime, or printed arm;
- its evidence class (E1–E5 per A-003) [6] [V].

Rules:
- Simulation success is reported as "in the defined scene", never as robot performance [2] [V].
- Board latency and memory are reported as "VENTUNO Q, runtime X, profile Y". Laptop or server numbers never substitute [2][6] [V].
- Physical claims exist only if physical trials ran.
- No claim is generalised to the SO101 or to other boards.

### DR-4 — Task-success and execution-time reporting (with SO101-22/35) — APPROVED 2026-10-14: option (a), retire

**Proposal:** SO101-23 adopts the principles only:
- primary outcome is success;
- no threshold;
- uncertainty is reported;
- duration is reported over successes only, with the completed count.

The operational definitions stay in decision 0001 §3 and SO101-35. 0001 is still unapproved [5] [V].

**Retire F04 (28/40, 30 s) and F05 (12/20) as acceptance thresholds?** Options:
- **(a) Retire.** Consistent with S-3.
- **(b) Keep F04 as a target-tier reporting reference only.**

### DR-5 — APPROVED 2026-10-14 — Priority of MQTT telemetry, update/rollback, Cartesian controls, accelerator (A02)

| Item | Proposal | Reason |
|---|---|---|
| Accelerator (NPU/GPU) | Already decided: exploratory, after the nine cells. Just reference it. | 0002 D1 [6] [V] |
| MQTT telemetry | Out of core. The telemetry transport is chosen in SO101-7 (architecture); MQTT is not preselected. | No source requires it [2] [V] |
| Update/rollback tooling | Out of core. Replaced by versioned artifacts with SHA-256 and run manifests. | 0002 §3 / A-003 [6] [V] |
| Cartesian / XYZ controls | Out of core. Joint-space only. Physical manual jog is conditional on the arm and needs approved limits. | §2 [3][4] [V] |

### DR-6 — APPROVED 2026-10-14 (limit values open) — Accepted-command validation and invalid-input behaviour (R01)

**Proposal:** the console accepts only a closed command set:
- create run;
- start;
- abort/stop;
- export results.

Run parameters are validated against frozen catalogues:
- model ∈ {SmolVLA, ACT, DP};
- profile ∈ {FP32-ref, FP16, INT8, INT4};
- seed-list ID;
- episode count.

On invalid input:
- the request is rejected with a reason and logged;
- no run starts;
- no action is sent.

Abort is always accepted.

Policy action bounds are enforced below the console by the SO101-37 action/state contract. The numeric joint, velocity and torque limits are **to be supplied by Hoan**, per CLAUDE.md.

Free-text and voice commands are out of scope (DR-2), so the F06 parser targets lapse.

### DR-7 — Minimum console (boundary for SO101-42) — APPROVED 2026-10-14

**Proposal:**
1. Configure a run from the frozen catalogues (DR-6).
2. Start and abort.
3. Live run state, including:
   - episode counter;
   - connection;
   - fault states;
   - per-episode success/failure class.
4. Result records with run ID, code hash, dataset revision and artifact SHA-256.
5. Export to CSV/JSON.

It works against simulation and the board, with versioned mocks allowed first [9] [V].

Out of the minimum:
- mobile client (AC-12);
- camera live view: optional, recorded failure videos suffice [7];
- manual joint/gripper/speed jog: conditional on the physical arm.

Hosting stays with SO101-9 (AWS question).

## 4. Early rubric scan (D01 template only)

The D01 Project Plan template [8] [V] needs these items, which this decision feeds:
- Part 2 "Scope": an explicit in-scope/out-of-scope statement;
- "High-level requirements": whether the system is a prototype or a component, plus functional and non-functional requirements;
- "Product backlog": Alpha mapping per item;
- "Quality plan";
- "Ethical considerations".

DR-1 to DR-7 supply the Scope and Requirements sections. The Alpha mapping cannot be finished until the real rubric (SO101-97) is found.

## 5. Scope and schedule effects if approved as proposed [R]

| Affected item | Effect |
|---|---|
| SO101-42 | Can close 15 Oct on DR-7. |
| SO101-5 | Sketch scope shrinks: no mobile layouts and no XYZ panel. |
| SO101-14/15 | Unchanged; still conditional. |
| Older Word plan | F06/F09/A02 fields become "out of scope (0003)". |
| SoftDev AC document | Needs a web-console revision. |

No deadline changes.

## How to verify

1. Open SO101-23 and SO101-98 and check that §1 matches what you confirmed.
2. Compare §2 against the Word plan Framing table and the AC document.
3. Check the payload arithmetic in §3, DR-2.
4. When SO101-10 and SO101-97 outputs arrive, diff them against DR-1 to DR-7.

## References

1. SO101-23 and SO101-98 Jira descriptions, read-only snapshot 14 Oct 2026, `.so101_report_2026-10-14/jira_snapshot.json` [V]
2. *SO101 resolved planning decisions and revised schedule*, version 3, 12 Oct 2026, §1–2, `SO101_Timeline_Review_and_Revised_Schedule_2026-10-12_v3.md` [V]
3. *SO101 AI Robotics Project Plan (Literature Updated)*, `SO101_AI_Robotics_Project_Plan_Literature_Updated.docx`. Sections used: Framing (F04–F09, G0/F22), Build vs reuse (A02), Requirements R01–R09, Backlog B01 [V]
4. *AC, Scope, Constraints – SoftDev*, `Robo-Arm_sedoitensau/AC, Scope, Constraints - SoftDev.docx`, AC-01 to AC-12 [V]
5. Decision 0001 (Proposed), §3 [V]
6. Decision 0002 (Approved 14 Oct), §1 and §3; `docs/assumptions.md` A-001 to A-003 [V]
7. `experiments/002-benchmark-pilot-maniskill-so100/README.md`, S2 and S7–S13 [V]
8. *Team and Project Plan* template (D01), `Robo-Arm_sedoitensau/Group Project A Team and Project Plan-1.docx` [V]
9. SO101-10, SO101-42, SO101-29 Jira descriptions, same snapshot as [1] [V]
