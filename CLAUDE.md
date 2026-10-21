# CLAUDE.md — Robot Arm Project

## Project status

Updated 21 October 2026 (Asia/Bangkok). The workflow snapshot below was checked on **21 October 2026**; refresh Jira before describing it as live status.

- **Stage:** Project Plan consolidation and team review, alongside benchmark/runtime/interface validation and baseline work. A plan or approved approach is not execution evidence.
- **Owner / final decision-maker:** Hoan (the user), PM and integration/reporting coordinator. AI: Duc (lead) and Hoan; software: Khanh (lead) and Trieu; IoT: Chung (sole Project A member, responsible for every retained IoT task).
- **Bounded scope:** one cube placed in one box. Project A minimum: simulation benchmark, nine VENTUNO Q model/precision profiles, reports and minimum experiment console. Printed-arm work and its isolated procurement/build/test tasks are removed from Project A under decision 0004. Speech/free text, multiple object classes, MQTT, OTA and Cartesian controls are outside the current core. See [approved scope](docs/technical/decisions/0003-scope-acceptance-and-minimum-console.md).
- **Working route:** ManiSkill SO100, joint-position control, and `lerobot/svla_so100_pickplace` with its existing splits. The [benchmark/reference decision](docs/technical/decisions/0001-simulation-benchmark-and-reference.md) remains Proposed; the working route does not establish final protocol acceptance or exact physical SO101 equivalence.
- **Models and compute:** SmolVLA, ACT and Diffusion Policy × FP16, INT8 and INT4 on the VENTUNO Q Kryo CPU. [Decision 0002](docs/technical/decisions/0002-ventuno-q-runtime-precision-and-test-plan.md) approves one runtime per model across its precisions, ExecuTorch/XNNPACK as the primary route, model-dependent alternatives and disclosed mixed precision. Board verification remains pending; OpenVLA is a reserve, not an automatic replacement.
- **Open physical/interface values:** exact embodiment, dimensions, payload/reach, actuators, power, budget, numeric limits/rates and calibration/stop procedures remain subject to their recorded decisions. Do not infer these from the SO100 simulation model.

## Master plan and source records

- **Current integrated plan:** [Master Team and Project Plan](docs/project-management/plans/SO101_Master_Team_and_Project_Plan_2026-10-20.docx), created from `Group Project A Team and Project Plan-1.docx`. It contains the course-template sections, responsibilities, schedule, risk proposals, measurement definitions, source register and review checklist. **Team approval and completion of the marked open items remain pending.**
- **Document management:** maintain this master as the integrated review document. Keep decisions, assumptions, experiment protocols, raw evidence and formal reports as linked supporting records. Preserve the course template and earlier plans as source/history; do not silently merge superseded requirements back into the master.
- **Authority:** user-approved decisions and the [adopted version 3 timeline](docs/project-management/plans/SO101_Timeline_Review_and_Revised_Schedule_2026-10-12_v3.md) establish scope and dates; Jira records workflow state; run logs/manifests establish execution. Report contradictions explicitly. Approval, Jira Done and demonstrated results are separate facts.
- **Before submission:** complete member names/IDs and self-reported profiles, acknowledge team conduct, approve risk owners/ratings, reconcile acceptance records, and provide accessible source links plus a dated Jira snapshot. Record review in SO101-106 and final submission evidence in SO101-73. Drafting the master does not close either issue.

## Schedule and PM handoff

- All dates are Asia/Bangkok. Preserve existing Jira sprint memberships. Adopted overlapping envelopes: Pre-Sprint 13 September–24 October; Sprint 1 10 October–15 November; Sprint 2 12 October–6 December 2026. Administrative sprint end times do not replace course portal cutoffs.
- Fixed deliverables: EDA 16 October; baseline 24 October; Project Plan 25 October; conversion report 14 November; Sprint 1 package 15 November; Project A final 6 December. Individual research due 11 October is user-confirmed completed. Project B course deadline remains TBD; its roadmap is provisional.
- Plan handoff sequence: sections 20 October, integrated draft 21 October, review 22–23 October, preflight 24 October, submission 25 October. Internal handoff is planned by 17:00; acceptance and portal submission require their own evidence.
- Simulator readiness 15 October and final benchmark pilot 16 October are planned gates, not proof that acceptance occurred. Freeze benchmark/reference/protocol before scored comparisons. Conversion preparation may overlap harness work; scored runs wait for 29 October end-to-end acceptance.
- Final integration: full components 20 November → integration 23–26 November → review 29 November → retests 3 December → evidence approval 4 December → preflight 5 December → submission 6 December.
- Project A delivers simulation plus VENTUNO Q evidence without a 30 November arm-availability gate. Commercial-arm work is conditional Project B scope; confirm future ownership at rebaseline.
- **21 October PM snapshot:** 18 direct PM tasks: 3 Done, 2 In Review, 1 In Progress and 12 To Do. This is not a completion percentage. SO101-26 schedule is In Progress; SO101-27 governance, SO101-28 risks and SO101-37 contract are To Do. Immediate work is decision/evidence reconciliation, governance/risk completion and plan review.
- **Known discrepancies to reconcile:** scope decision 0003 is approved but SO101-23 is In Review / SO101-98 To Do; runtime decision 0002 is approved but SO101-34 is To Do and board evidence pending; simulator readiness SO101-49 is Done but benchmark acceptance SO101-100 is To Do and local experiment 002 remains Proposed. EDA parent SO101-11 is Done while report SO101-43 is To Do; hardware/access parent SO101-25 is Done while SO101-48 remains To Do. Printed-fit task SO101-64 is removed.

## Research and evidence rules

- Primary outcome: task success rate. Secondary outcomes: task duration, board inference latency, observed memory, package size and failures. Research acceptance requires valid reproducible coverage; do not invent a minimum success percentage or revive retired thresholds.
- Define the task/environment/protocol separately from the reference controller and learned policy/checkpoint. Validate camera/state/action/gripper conventions and record simulation-to-physical limitations. Freeze software, data, scene, seeds, configuration and checkpoint revisions.
- Use decision 0002's measurement boundaries and evidence classes. Distinguish laptop/external results, base-weight board probes, frozen-checkpoint board probes and scored runs. Simulation and board evidence do not establish physical performance.
- Existing approvals are not open questions. The decision rules below apply to new unresolved substantive choices or changes to an approved decision. Continue already-authorized document work and routine verification; preserve unresolved values visibly instead of inventing them.

## Scope and team amendment — 21 October 2026

- [Decision 0004](docs/technical/decisions/0004-project-a-simulation-board-scope-and-iot-ownership.md) records the user-approved removal of printed-arm tasks and Chung's sole Project A IoT ownership. The active team has five members: Hoan, Duc, Khanh, Trieu and Chung.
- SO101-13 was already absent. SO101-14, SO101-15 and SO101-64–69 are removed from active work; shared access, simulator, interface/fault and integration tasks remain. SO101-21/40/47/49 are reassigned to Chung without changing their recorded status.
- SO101-88 remains conditional commercial-arm Project B work and is unassigned pending Project B rebaseline. Do not invent Project B staffing or treat the removal of printing as removal of the simulator or board path.
- Earlier detailed plans are retained under `docs/technical/source-archives/planning-before-2026-10-21/`. Current companion copies point to the integrated master; source archives and dated Jira exports retain historical facts.

### Acknowledgment

The team acknowledges Nguyen for contributions during the earlier project phase. Nguyen has no active project-plan assignment. Preserve historical authorship/activity records and do not invent contribution details.

---

## Core rule: do not silently assume

Every non-trivial technical choice falls into one of three categories. Classify before acting.

| Category | When it applies | What Claude does |
|---|---|---|
| **A. Established** | Answer is well supported by reliable sources and has no meaningful project-specific trade-off (e.g., standard DH convention definitions, Ohm's law, a datasheet value). | Proceed, and cite the source inline. |
| **B. Proposed assumption** | Literature supports a reasonable default, but it depends on project goals, or sources partly disagree. | **Stop.** Present the proposal in the *Assumption Proposal* format below and wait for my approval. |
| **C. Open decision** | Literature is insufficient, contradictory, or the choice depends on my preferences, budget, hardware on hand, or risk tolerance. | **Stop.** Ask me using the *Decision Request* format. Do not pick a default and continue. |

If unsure which category applies, treat it as **C**.

Never proceed on a B or C item "for now" and tell me later. Blocking is preferred over guessing.

### Always category C (always ask me)
- Mechanical dimensions, link lengths, DOF count, workspace
- Actuator, gearbox, motor driver, or sensor selection
- Safety limits: torque/current limits, speed limits, e-stop behavior, collision handling
- Power supply design, voltage levels, battery use
- Control architecture (position/velocity/torque control, PID vs. MPC vs. learned, control loop rates)
- Anything that costs money, is hard to reverse, or could damage hardware or injure someone
- Changing a previously recorded decision

---

## Evidence & citation standards

### Every claim that drives a decision needs a source
- Cite inline as `[n]` and list full references at the end of the response.
- Reference format: Author(s), *Title*, Venue/Publisher, Year, plus DOI / URL / datasheet section / page number.
- Prefer, in order:
  1. Manufacturer datasheets & official documentation (for component specs)
  2. Standard textbooks (e.g., Craig *Introduction to Robotics*; Siciliano et al. *Robotics: Modelling, Planning and Control*; Lynch & Park *Modern Robotics*; Spong et al. *Robot Modeling and Control*)
  3. Peer-reviewed papers (IEEE T-RO, ICRA, IROS, RA-L, IJRR, etc.)
  4. Standards (e.g., ISO 10218, ISO/TS 15066 for collaborative safety)
  5. Reputable open-source projects / official ROS docs
  6. Forums, blogs, videos — **supporting evidence only, never sole justification**, and labeled as such.

### Honesty rules (non-negotiable)
- **Never fabricate a citation, DOI, page number, or quote.** If Claude cannot verify a source exists, say so explicitly: "I believe this is from X but could not verify it — please check."
- Distinguish clearly between:
  - **[Verified]** — Claude retrieved/read the source in this session
  - **[From memory]** — Claude recalls it but did not retrieve it; I must verify
  - **[Reasoning]** — Claude's own derivation/engineering judgment, no external source
- State confidence (High / Medium / Low) for each recommendation.
- If sources disagree, show both sides; do not pick the convenient one.
- Show calculations (torque, inertia, gear ratio, power budget, etc.) step by step with units so I can check them.

---

## Response templates

### Assumption Proposal (category B)
```
## Assumption proposal: <short title>
**Context:** why this choice is needed now
**Proposed assumption:** <the default Claude suggests>
**Reasons:**
1. <reason> [1] — [Verified/From memory/Reasoning]
2. <reason> [2] — ...
**Alternatives considered:**
- <option> — pros / cons [n]
**Risks if wrong:** <what breaks, cost to reverse>
**Confidence:** High / Medium / Low
**How you can verify:** <specific check: datasheet section, calculation, test, sim>
**References:**
[1] ...
[2] ...

→ Approve, reject, or modify?
```

### Decision Request (category C)
```
## Decision needed: <short title>
**Why I'm stopping:** literature is insufficient / conflicting / depends on your goals
**What I found:** brief summary with citations [n]
**Gaps in the evidence:** what I could not determine
**Options:**
| Option | Pros | Cons | Cost/effort | Evidence |
|---|---|---|---|---|
**Information that would settle it:** <measurement, test, spec, or preference from you>
**References:**
[1] ...

→ Which option, or what would you like me to investigate further?
```

---

## Verification hand-off
I verify; Claude does not self-certify. For any result Claude produces (calculation, code, design value, sim result):
- Provide a **"How to verify"** section with concrete steps: which number to check against which source, a test to run, an expected output range, or a sanity check (e.g., order-of-magnitude, unit consistency, simulation vs. hand calculation).
- Mark the item **UNVERIFIED** until I confirm it. Do not build further work on unverified results without telling me.
- For physical tests: propose the test procedure, expected results, pass/fail criteria, and safety precautions — then wait for me to run it and report back.

---

## Decision log
- Record every approved decision in `docs/technical/decisions/NNNN-short-title.md`:
  ```
  # NNNN — Title
  Date: YYYY-MM-DD
  Status: Proposed | Approved | Superseded by NNNN
  Decision: ...
  Rationale: ... (with references)
  Alternatives rejected: ...
  Verified by: <me> on <date> via <method>
  ```
- Record approved assumptions in `docs/technical/assumptions.md` with ID, statement, source, confidence, and verification status.
- Before proposing anything, check these files so Claude doesn't contradict or re-ask settled questions.

---

## Experiments
- Every experiment gets a plan in `research/experiments/NNN-name/README.md` before code is written: hypothesis, setup, variables, measurement method, expected outcome (with source if possible), safety notes.
- Report results honestly, including failures and noise. Do not tune the narrative to match expectations.

---

## Code & hardware safety
- Never write code that commands real hardware without: software joint limits, velocity/torque limits, and an e-stop/abort path. Ask me for limit values — do not invent them.
- Default new motion code to **simulation or dry-run mode**.
- Flag any code path that could move the arm unexpectedly (startup, homing, error recovery).

---

## Communication style
- Be direct. If my idea has a problem, say so and cite why.
- Ask one focused set of questions at a time rather than a long questionnaire.
- Prefer "I don't know, here's how we could find out" over a confident guess.
