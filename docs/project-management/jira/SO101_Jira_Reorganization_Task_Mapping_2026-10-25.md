# SO101 Jira reorganization — complete task and subtask mapping

Date: 25 October 2026 (Asia/Bangkok)  
Status: **Stage A complete; model roster/ownership in section 12 and latest refined timelines in section 13. Stage B split deferred.**  
Purpose: Review every existing issue's proposed destination before any Jira mutation.

## 1. Scope and inventory

[Verified] A fresh read-only Jira query, `project = SO101 ORDER BY key ASC`, returned all 95 visible project issues in one completed page (`isLast = true`): **5 epics, 54 tasks and 36 subtasks**. The mapping below accounts for every one of the **90 non-epic issues exactly once**. Missing numerical keys are not presumed to be missing work; previously removed issues are not recreated.

[Reasoning] The proposed structure has **six Project A outcome epics**, **four provisional Project B outcome epics**, and **six standalone PM tasks**. Project B's final structure is shown completely for review but its migration is deferred until rebaseline. Confidence: medium in the proposed grouping; completeness has been mechanically checked against the fetched inventory.

This document is a planning artifact, not an executable migration script or authorization to change Jira. Existing keys, history, evidence, owners, statuses, dates, and sprint memberships are preserved unless a later approved edit explicitly says otherwise. A status shown here is a snapshot, not proof of execution.

### Important boundaries

- A1–A6 and B1–B4 are **document aliases**, not existing Jira keys or extra hierarchy levels.
- A standard task has one epic parent. A subtask has one task parent and belongs to that task's epic indirectly.
- Three existing subtasks are proposed for promotion to standalone Tasks: SO101-56, SO101-58 and SO101-71. They cannot simply be attached directly to an epic while remaining subtasks.
- Cross-epic dependencies are links, not duplicate copies or second parents.
- Six PM tasks intentionally have no epic; they remain visible through a governance filter.
- The earlier suggestion to replace overlapping course sprints with short delivery sprints is **a separate, unapproved proposal**. Local project guidance says to preserve existing memberships. This mapping does not reschedule or alter sprints.
- Project A excludes the removed printed-arm branch. Commercial-arm work remains conditional Project B scope.
- Local decision 0005 already includes bounded console chat. Its detailed request set, ambiguity behavior, language-model use and acceptance tests remain unresolved; this plan does not select them.
- Local decision 0002 and the approved assumptions already define runtime/precision choices. SO101-34 should reconcile approved decisions with verification evidence, not reopen those decisions by default.

## 2. Epic disposition and totals

Counts below refer to existing non-epic issues before the three proposed type conversions. The 12 proposed new tasks in section 5 are excluded.

| Alias | Proposed outcome | Existing epic disposition | Existing tasks | Existing subtasks | Total |
|---|---|---|---:|---:|---:|
| A1 | Reproducible simulation benchmark and evaluation protocol | New epic (no Jira key yet) | 5 | 5 | 10 |
| A2 | Three-model baseline comparison | Rename SO101-3 | 5 | 5 | 10 |
| A3 | Validated VENTUNO Q–MCU–simulator measurement path | Rename SO101-4 | 10 | 8 | 18 |
| A4 | Nine-profile precision comparison | New epic (no Jira key yet) | 1 | 6 | 7 |
| A5 | Experiment console v1 and integrated demonstration | Rename SO101-2 | 6 | 2 | 8 |
| A6 | Project A submission and reproducible handover | Rename SO101-1 | 6 | 6 | 12 |
| B1 | Reproduced Project A baseline | New provisional epic; defer creation to Project B rebaseline | 3 | 0 | 3 |
| B2 | Extended research campaign | New provisional epic; defer creation to Project B rebaseline | 6 | 3 | 9 |
| B3 | Conditional commercial-arm validation | New provisional epic; defer creation to Project B rebaseline | 2 | 1 | 3 |
| B4 | Final research release and handover | Eventually narrow/rename SO101-81; defer to Project B rebaseline | 4 | 0 | 4 |
| PM | Standalone project governance — no epic | No epic parent | 6 | 0 | 6 |
| **Total** | | | **54** | **36** | **90** |

Project A: **65 existing issues**. Project B: **19 existing issues**, including SO101-80 preparation currently under SO101-1. Standalone PM: **6 existing issues**.

Existing epic keys are all accounted for: SO101-1 → A6; SO101-2 → A5; SO101-3 → A2; SO101-4 → A3; SO101-81 → B4 only after the deferred Project B split. A1/A4 need two new epics for Project A. B1/B2/B3 would need three new epics later. No old epic is deleted or marked complete merely because its scope changes.

## 3. Complete existing-issue mapping

Current titles are reproduced below for identification. Proposed title/scope changes are listed separately in section 4. In the proposed-parent column, an issue key alone identifies a retained task parent; an epic destination is explicitly marked with its alias.

### A1. Reproducible simulation benchmark and evaluation protocol

**Proposed epic:** New epic (no Jira key yet).  
**Completion boundary:** A teammate can reproduce the executable benchmark/reference pilot and use the approved comparison protocol. Simulation conventions and limitations are explicit.

**Placement rationale:** Requirements, simulator suitability and scientific acceptance belong to the benchmark outcome. SO101-10 is retained as completed requirements evidence, not reopened.

| Existing issue and current title | Current type | Current direct parent | Proposed direct parent | Current status |
|---|---|---|---|---|
| [SO101-10](https://huu-hoan-hoang.atlassian.net/browse/SO101-10) — Brainstorm the requirements needed to complete the project | Task | [SO101-2](https://huu-hoan-hoang.atlassian.net/browse/SO101-2) | A1 — new epic | Done |
| [SO101-21](https://huu-hoan-hoang.atlassian.net/browse/SO101-21) — Select the simulator for robot arm testing | Task | [SO101-4](https://huu-hoan-hoang.atlassian.net/browse/SO101-4) | A1 — new epic | Done |
| [SO101-47](https://huu-hoan-hoang.atlassian.net/browse/SO101-47) — Select the initial simulator and record the compatibility rationale | Subtask | [SO101-21](https://huu-hoan-hoang.atlassian.net/browse/SO101-21) | [SO101-21](https://huu-hoan-hoang.atlassian.net/browse/SO101-21) | Done |
| [SO101-49](https://huu-hoan-hoang.atlassian.net/browse/SO101-49) — Demonstrate a runnable simulator with the agreed observations and actions | Subtask | [SO101-21](https://huu-hoan-hoang.atlassian.net/browse/SO101-21) | [SO101-21](https://huu-hoan-hoang.atlassian.net/browse/SO101-21) | Done |
| [SO101-22](https://huu-hoan-hoang.atlassian.net/browse/SO101-22) — Research and define the simulation benchmark, baseline and performance objectives | Task | [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) | A1 — new epic | In Review |
| [SO101-100](https://huu-hoan-hoang.atlassian.net/browse/SO101-100) — Accept the executable benchmark and reference controller pilot | Subtask | [SO101-22](https://huu-hoan-hoang.atlassian.net/browse/SO101-22) | [SO101-22](https://huu-hoan-hoang.atlassian.net/browse/SO101-22) | To Do |
| [SO101-23](https://huu-hoan-hoang.atlassian.net/browse/SO101-23) — Approve the core task catalogue, operating envelope and acceptance targets | Task | [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) | A1 — new epic | In Review |
| [SO101-98](https://huu-hoan-hoang.atlassian.net/browse/SO101-98) — Approve the bounded research scope and acceptance approach | Subtask | [SO101-23](https://huu-hoan-hoang.atlassian.net/browse/SO101-23) | [SO101-23](https://huu-hoan-hoang.atlassian.net/browse/SO101-23) | Done |
| [SO101-35](https://huu-hoan-hoang.atlassian.net/browse/SO101-35) — Approve the simulation and VENTUNO Q evaluation protocol | Task | [SO101-3](https://huu-hoan-hoang.atlassian.net/browse/SO101-3) | A1 — new epic | To Do |
| [SO101-101](https://huu-hoan-hoang.atlassian.net/browse/SO101-101) — Approve the comparison protocol before model commitment and scored trials | Subtask | [SO101-35](https://huu-hoan-hoang.atlassian.net/browse/SO101-35) | [SO101-35](https://huu-hoan-hoang.atlassian.net/browse/SO101-35) | To Do |

### A2. Three-model baseline comparison

**Proposed epic:** Rename SO101-3.  
**Completion boundary:** Three trained model references, pinned configurations, comparable results and a reviewed baseline report are traceable.

**Placement rationale:** Dataset/learning decisions feed the trained baseline. The same records also support A1 through dependency links; each issue has only one epic.

| Existing issue and current title | Current type | Current direct parent | Proposed direct parent | Current status |
|---|---|---|---|---|
| [SO101-11](https://huu-hoan-hoang.atlassian.net/browse/SO101-11) — Complete single-dataset EDA, training strategy and report | Task | [SO101-3](https://huu-hoan-hoang.atlassian.net/browse/SO101-3) | SO101-3 (A2) | Done |
| [SO101-43](https://huu-hoan-hoang.atlassian.net/browse/SO101-43) — Write the dataset EDA and training strategy report | Subtask | [SO101-11](https://huu-hoan-hoang.atlassian.net/browse/SO101-11) | [SO101-11](https://huu-hoan-hoang.atlassian.net/browse/SO101-11) | Done |
| [SO101-12](https://huu-hoan-hoang.atlassian.net/browse/SO101-12) — Select three of four models, train, evaluate and report the baseline | Task | [SO101-3](https://huu-hoan-hoang.atlassian.net/browse/SO101-3) | SO101-3 (A2) | In Progress |
| [SO101-44](https://huu-hoan-hoang.atlassian.net/browse/SO101-44) — Write the Sprint 1 model experiment and baseline report | Subtask | [SO101-12](https://huu-hoan-hoang.atlassian.net/browse/SO101-12) | [SO101-12](https://huu-hoan-hoang.atlassian.net/browse/SO101-12) | To Do |
| [SO101-52](https://huu-hoan-hoang.atlassian.net/browse/SO101-52) — Freeze the three-model reference checkpoints and baseline evidence | Subtask | [SO101-12](https://huu-hoan-hoang.atlassian.net/browse/SO101-12) | [SO101-12](https://huu-hoan-hoang.atlassian.net/browse/SO101-12) | To Do |
| [SO101-53](https://huu-hoan-hoang.atlassian.net/browse/SO101-53) — Review the baseline evidence and report before the 24 October deadline | Subtask | [SO101-12](https://huu-hoan-hoang.atlassian.net/browse/SO101-12) | [SO101-12](https://huu-hoan-hoang.atlassian.net/browse/SO101-12) | To Do |
| [SO101-31](https://huu-hoan-hoang.atlassian.net/browse/SO101-31) — Decide the single dataset, coverage, recording plan and session-level splits | Task | [SO101-3](https://huu-hoan-hoang.atlassian.net/browse/SO101-3) | SO101-3 (A2) | Done |
| [SO101-32](https://huu-hoan-hoang.atlassian.net/browse/SO101-32) — Decide the learning, adaptation and demonstration-capture strategy | Task | [SO101-3](https://huu-hoan-hoang.atlassian.net/browse/SO101-3) | SO101-3 (A2) | Done |
| [SO101-33](https://huu-hoan-hoang.atlassian.net/browse/SO101-33) — Approve the four-model shortlist and three-model experiment protocol | Task | [SO101-3](https://huu-hoan-hoang.atlassian.net/browse/SO101-3) | SO101-3 (A2) | Done |
| [SO101-102](https://huu-hoan-hoang.atlassian.net/browse/SO101-102) — Approve the final three models using protocol runtime and benchmark evidence | Subtask | [SO101-33](https://huu-hoan-hoang.atlassian.net/browse/SO101-33) | [SO101-33](https://huu-hoan-hoang.atlassian.net/browse/SO101-33) | Done |

### A3. Validated VENTUNO Q–MCU–simulator measurement path

**Proposed epic:** Rename SO101-4.  
**Completion boundary:** The board, MCU, simulator and minimal runner/logger produce a reproducible, accepted measurement run, including validation and fault evidence.

**Placement rationale:** Shared architecture and the backend implementation-design handoff stay together in SO101-7. Console implementation consumes that design through a dependency. Early runtime probes belong here; frozen-model profile execution belongs to A4.

| Existing issue and current title | Current type | Current direct parent | Proposed direct parent | Current status |
|---|---|---|---|---|
| [SO101-7](https://huu-hoan-hoang.atlassian.net/browse/SO101-7) — Research robotics architecture, communication protocol and integration links | Task | [SO101-2](https://huu-hoan-hoang.atlassian.net/browse/SO101-2) | SO101-4 (A3) | In Progress |
| [SO101-50](https://huu-hoan-hoang.atlassian.net/browse/SO101-50) — Publish the preliminary architecture and communication handoff | Subtask | [SO101-7](https://huu-hoan-hoang.atlassian.net/browse/SO101-7) | [SO101-7](https://huu-hoan-hoang.atlassian.net/browse/SO101-7) | To Do |
| [SO101-51](https://huu-hoan-hoang.atlassian.net/browse/SO101-51) — Freeze the backend implementation design after the action/state contract | Subtask | [SO101-7](https://huu-hoan-hoang.atlassian.net/browse/SO101-7) | [SO101-7](https://huu-hoan-hoang.atlassian.net/browse/SO101-7) | To Do |
| [SO101-19](https://huu-hoan-hoang.atlassian.net/browse/SO101-19) — Run STM32H5F5 output in the selected simulator | Task | [SO101-4](https://huu-hoan-hoang.atlassian.net/browse/SO101-4) | SO101-4 (A3) | To Do |
| [SO101-57](https://huu-hoan-hoang.atlassian.net/browse/SO101-57) — Deliver the early STM32H5F5-to-simulator measurement path | Subtask | [SO101-19](https://huu-hoan-hoang.atlassian.net/browse/SO101-19) | [SO101-19](https://huu-hoan-hoang.atlassian.net/browse/SO101-19) | To Do |
| [SO101-20](https://huu-hoan-hoang.atlassian.net/browse/SO101-20) — Research AI-to-STM32H5F5 and MCU-to-simulator links with sample tests | Task | [SO101-4](https://huu-hoan-hoang.atlassian.net/browse/SO101-4) | SO101-4 (A3) | To Do |
| [SO101-55](https://huu-hoan-hoang.atlassian.net/browse/SO101-55) — Accept sample tests for both communication legs | Subtask | [SO101-20](https://huu-hoan-hoang.atlassian.net/browse/SO101-20) | [SO101-20](https://huu-hoan-hoang.atlassian.net/browse/SO101-20) | To Do |
| [SO101-25](https://huu-hoan-hoang.atlassian.net/browse/SO101-25) — Confirm hardware and compute access for simulation and board research | Task | [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) | SO101-4 (A3) | Done |
| [SO101-48](https://huu-hoan-hoang.atlassian.net/browse/SO101-48) — Confirm school GPU and VENTUNO Q access for the readiness gates | Subtask | [SO101-25](https://huu-hoan-hoang.atlassian.net/browse/SO101-25) | [SO101-25](https://huu-hoan-hoang.atlassian.net/browse/SO101-25) | To Do |
| [SO101-34](https://huu-hoan-hoang.atlassian.net/browse/SO101-34) — Decide the VENTUNO Q runtime, precision comparison and resource-test plan | Task | [SO101-3](https://huu-hoan-hoang.atlassian.net/browse/SO101-3) | SO101-4 (A3) | To Do |
| [SO101-36](https://huu-hoan-hoang.atlassian.net/browse/SO101-36) — Decide the STM32H5F5 execution path and USB reference baseline | Task | [SO101-4](https://huu-hoan-hoang.atlassian.net/browse/SO101-4) | SO101-4 (A3) | To Do |
| [SO101-37](https://huu-hoan-hoang.atlassian.net/browse/SO101-37) — Approve the versioned AI, STM32H5F5 and backend action/state contract | Task | [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) | SO101-4 (A3) | To Do |
| [SO101-38](https://huu-hoan-hoang.atlassian.net/browse/SO101-38) — Approve board/simulator transport, command validation and stop/fault tests | Task | [SO101-4](https://huu-hoan-hoang.atlassian.net/browse/SO101-4) | SO101-4 (A3) | To Do |
| [SO101-54](https://huu-hoan-hoang.atlassian.net/browse/SO101-54) — Approve the command validation and stop/fault test procedure | Subtask | [SO101-38](https://huu-hoan-hoang.atlassian.net/browse/SO101-38) | [SO101-38](https://huu-hoan-hoang.atlassian.net/browse/SO101-38) | To Do |
| [SO101-39](https://huu-hoan-hoang.atlassian.net/browse/SO101-39) — Resolve simulator selection and communication sample-test ordering | Task | [SO101-4](https://huu-hoan-hoang.atlassian.net/browse/SO101-4) | SO101-4 (A3) | Done |
| [SO101-40](https://huu-hoan-hoang.atlassian.net/browse/SO101-40) — Clarify the STM32H5F5 simulator test's complete deliverables | Task | [SO101-4](https://huu-hoan-hoang.atlassian.net/browse/SO101-4) | SO101-4 (A3) | In Review |
| [SO101-56](https://huu-hoan-hoang.atlassian.net/browse/SO101-56) — Deliver the minimal experiment runner and result logger | Subtask → **Task (proposed)** | [SO101-8](https://huu-hoan-hoang.atlassian.net/browse/SO101-8) | SO101-4 (A3) | To Do |
| [SO101-58](https://huu-hoan-hoang.atlassian.net/browse/SO101-58) — Accept and reproduce the complete board and simulation measurement path | Subtask → **Task (proposed)** | [SO101-46](https://huu-hoan-hoang.atlassian.net/browse/SO101-46) | SO101-4 (A3) | To Do |

### A4. Nine-profile precision comparison

**Proposed epic:** New epic (no Jira key yet).  
**Completion boundary:** All nine required model/precision profiles have accepted simulation and actual-board evidence plus the reviewed comparison report. Unsupported paths require an explicit scope/runtime resolution; recording a blocker alone does not fulfil a required profile.

**Placement rationale:** Existing campaign/report records stay together. Twelve proposed new tasks across A2/A4 are listed separately, so they cannot be mistaken for existing Jira issues.

| Existing issue and current title | Current type | Current direct parent | Proposed direct parent | Current status |
|---|---|---|---|---|
| [SO101-18](https://huu-hoan-hoang.atlassian.net/browse/SO101-18) — Evaluate all three models at INT8, INT4 and FP16 for the Sprint 2 report | Task | [SO101-3](https://huu-hoan-hoang.atlassian.net/browse/SO101-3) | A4 — new epic | To Do |
| [SO101-45](https://huu-hoan-hoang.atlassian.net/browse/SO101-45) — Write the Sprint 2 conversion and deployment experiment report | Subtask | [SO101-18](https://huu-hoan-hoang.atlassian.net/browse/SO101-18) | [SO101-18](https://huu-hoan-hoang.atlassian.net/browse/SO101-18) | To Do |
| [SO101-59](https://huu-hoan-hoang.atlassian.net/browse/SO101-59) — Convert calibrate and probe all nine frozen model precision profiles | Subtask | [SO101-18](https://huu-hoan-hoang.atlassian.net/browse/SO101-18) | [SO101-18](https://huu-hoan-hoang.atlassian.net/browse/SO101-18) | To Do |
| [SO101-60](https://huu-hoan-hoang.atlassian.net/browse/SO101-60) — Record the first actual run or evidenced blocker for all nine profiles | Subtask | [SO101-18](https://huu-hoan-hoang.atlassian.net/browse/SO101-18) | [SO101-18](https://huu-hoan-hoang.atlassian.net/browse/SO101-18) | To Do |
| [SO101-61](https://huu-hoan-hoang.atlassian.net/browse/SO101-61) — Run the matched nine-profile simulation and VENTUNO Q comparisons | Subtask | [SO101-18](https://huu-hoan-hoang.atlassian.net/browse/SO101-18) | [SO101-18](https://huu-hoan-hoang.atlassian.net/browse/SO101-18) | To Do |
| [SO101-62](https://huu-hoan-hoang.atlassian.net/browse/SO101-62) — Complete required reruns and freeze the nine-profile evidence | Subtask | [SO101-18](https://huu-hoan-hoang.atlassian.net/browse/SO101-18) | [SO101-18](https://huu-hoan-hoang.atlassian.net/browse/SO101-18) | To Do |
| [SO101-63](https://huu-hoan-hoang.atlassian.net/browse/SO101-63) — Technically review the nine-profile conversion report | Subtask | [SO101-18](https://huu-hoan-hoang.atlassian.net/browse/SO101-18) | [SO101-18](https://huu-hoan-hoang.atlassian.net/browse/SO101-18) | To Do |

### A5. Experiment console v1 and integrated demonstration

**Proposed epic:** Rename SO101-2.  
**Completion boundary:** An operator can run the agreed console workflow, see state/faults and export traceable results through the integrated system. Include approved bounded chat scope; its unresolved behavior and acceptance tests still require decisions.

**Placement rationale:** The minimal logger and early measurement acceptance move to A3 as standalone tasks. Full console integration stays here. A6 owns final cross-project reproduction and submission acceptance.

| Existing issue and current title | Current type | Current direct parent | Proposed direct parent | Current status |
|---|---|---|---|---|
| [SO101-5](https://huu-hoan-hoang.atlassian.net/browse/SO101-5) — Research UX/UI and finalize the interface sketch | Task | [SO101-2](https://huu-hoan-hoang.atlassian.net/browse/SO101-2) | SO101-2 (A5) | Done |
| [SO101-6](https://huu-hoan-hoang.atlassian.net/browse/SO101-6) — Build the frontend from the finalized sketch | Task | [SO101-2](https://huu-hoan-hoang.atlassian.net/browse/SO101-2) | SO101-2 (A5) | In Progress |
| [SO101-8](https://huu-hoan-hoang.atlassian.net/browse/SO101-8) — Build the backend from the agreed architecture and protocol | Task | [SO101-2](https://huu-hoan-hoang.atlassian.net/browse/SO101-2) | SO101-2 (A5) | To Do |
| [SO101-9](https://huu-hoan-hoang.atlassian.net/browse/SO101-9) — Clarify AWS requirements with the supervisor | Task | [SO101-2](https://huu-hoan-hoang.atlassian.net/browse/SO101-2) | SO101-2 (A5) | In Review |
| [SO101-42](https://huu-hoan-hoang.atlassian.net/browse/SO101-42) — Define the experiment-console workflow and feature catalogue | Task | [SO101-2](https://huu-hoan-hoang.atlassian.net/browse/SO101-2) | SO101-2 (A5) | To Do |
| [SO101-99](https://huu-hoan-hoang.atlassian.net/browse/SO101-99) — Approve the minimum experiment console workflow and evidence schema | Subtask | [SO101-42](https://huu-hoan-hoang.atlassian.net/browse/SO101-42) | [SO101-42](https://huu-hoan-hoang.atlassian.net/browse/SO101-42) | To Do |
| [SO101-46](https://huu-hoan-hoang.atlassian.net/browse/SO101-46) — Coordinate core AI, STM32H5F5, simulator and web integration | Task | [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) | SO101-2 (A5) | To Do |
| [SO101-70](https://huu-hoan-hoang.atlassian.net/browse/SO101-70) — Accept the full console AI board MCU and simulator integration | Subtask | [SO101-46](https://huu-hoan-hoang.atlassian.net/browse/SO101-46) | [SO101-46](https://huu-hoan-hoang.atlassian.net/browse/SO101-46) | To Do |

### A6. Project A submission and reproducible handover

**Proposed epic:** Rename SO101-1.  
**Completion boundary:** The reviewed course submissions, final demonstration/evidence archive and handover are recorded, with submission receipts where applicable.

**Placement rationale:** SO101-71 becomes standalone final defect-closure/reproduction acceptance. Actual fixes remain with their owning technical epic; link fixes to this acceptance record rather than duplicate implementation.

| Existing issue and current title | Current type | Current direct parent | Proposed direct parent | Current status |
|---|---|---|---|---|
| [SO101-29](https://huu-hoan-hoang.atlassian.net/browse/SO101-29) — Confirm the course rubric, submission checklist and authorship responsibilities | Task | [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) | SO101-1 (A6) | Done |
| [SO101-97](https://huu-hoan-hoang.atlassian.net/browse/SO101-97) — Publish the initial Project A rubric and submission checklist | Subtask | [SO101-29](https://huu-hoan-hoang.atlassian.net/browse/SO101-29) | [SO101-29](https://huu-hoan-hoang.atlassian.net/browse/SO101-29) | Done |
| [SO101-30](https://huu-hoan-hoang.atlassian.net/browse/SO101-30) — Approve the final evidence, reproducibility, demonstration and report package | Task | [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) | SO101-1 (A6) | To Do |
| [SO101-72](https://huu-hoan-hoang.atlassian.net/browse/SO101-72) — Approve the final Project A evidence after retesting | Subtask | [SO101-30](https://huu-hoan-hoang.atlassian.net/browse/SO101-30) | [SO101-30](https://huu-hoan-hoang.atlassian.net/browse/SO101-30) | To Do |
| [SO101-71](https://huu-hoan-hoang.atlassian.net/browse/SO101-71) — Close integration defects and independently reproduce Project A evidence | Subtask → **Task (proposed)** | [SO101-46](https://huu-hoan-hoang.atlassian.net/browse/SO101-46) | SO101-1 (A6) | To Do |
| [SO101-73](https://huu-hoan-hoang.atlassian.net/browse/SO101-73) — Compile review and submit the Project Plan by 25 October | Task | [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) | SO101-1 (A6) | To Do |
| [SO101-106](https://huu-hoan-hoang.atlassian.net/browse/SO101-106) — Review the complete Project Plan before submission | Subtask | [SO101-73](https://huu-hoan-hoang.atlassian.net/browse/SO101-73) | [SO101-73](https://huu-hoan-hoang.atlassian.net/browse/SO101-73) | To Do |
| [SO101-74](https://huu-hoan-hoang.atlassian.net/browse/SO101-74) — Compile and submit the Sprint 1 course package by 15 November | Task | [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) | SO101-1 (A6) | To Do |
| [SO101-75](https://huu-hoan-hoang.atlassian.net/browse/SO101-75) — Submit the reviewed Sprint 1 course package and verify receipt | Subtask | [SO101-74](https://huu-hoan-hoang.atlassian.net/browse/SO101-74) | [SO101-74](https://huu-hoan-hoang.atlassian.net/browse/SO101-74) | To Do |
| [SO101-77](https://huu-hoan-hoang.atlassian.net/browse/SO101-77) — Map Alpha evidence demonstration and archive to the Project A checklist | Task | [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) | SO101-1 (A6) | To Do |
| [SO101-78](https://huu-hoan-hoang.atlassian.net/browse/SO101-78) — Deliver the reproducibility archive and handover manifest for approval | Subtask | [SO101-77](https://huu-hoan-hoang.atlassian.net/browse/SO101-77) | [SO101-77](https://huu-hoan-hoang.atlassian.net/browse/SO101-77) | To Do |
| [SO101-79](https://huu-hoan-hoang.atlassian.net/browse/SO101-79) — Preflight and submit the final Project A package by 6 December | Task | [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) | SO101-1 (A6) | To Do |

### B1. Reproduced Project A baseline

**Proposed epic:** New provisional epic; defer creation to Project B rebaseline.  
**Completion boundary:** Project B scope/calendar are confirmed and the accepted Project A evidence paths can be reproduced.

**Placement rationale:** SO101-80 is Project B preparation even if performed during Project A. Its date and sprint membership stay unchanged; it remains discoverable in a transition-work filter.

| Existing issue and current title | Current type | Current direct parent | Proposed direct parent | Current status |
|---|---|---|---|---|
| [SO101-80](https://huu-hoan-hoang.atlassian.net/browse/SO101-80) — Confirm the Project B calendar and Beta requirements or record the publication checkpoint | Task | [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) | B1 — new provisional epic | To Do |
| [SO101-82](https://huu-hoan-hoang.atlassian.net/browse/SO101-82) — Rebaseline Project B scope calendar hardware and final deliverables | Task | [SO101-81](https://huu-hoan-hoang.atlassian.net/browse/SO101-81) | B1 — new provisional epic | To Do |
| [SO101-83](https://huu-hoan-hoang.atlassian.net/browse/SO101-83) — Restore the pinned Project A environment and reproduce each valid evidence path | Task | [SO101-81](https://huu-hoan-hoang.atlassian.net/browse/SO101-81) | B1 — new provisional epic | To Do |

### B2. Extended research campaign

**Proposed epic:** New provisional epic; defer creation to Project B rebaseline.  
**Completion boundary:** The extension protocol, accepted setup, expanded core campaign, reruns and independently reviewed analysis are complete.

**Placement rationale:** SO101-85 is measurement-enabling console/simulator hardening for the research campaign. SO101-94 below owns packaging the final demonstration release, avoiding two epics claiming the same implementation.

| Existing issue and current title | Current type | Current direct parent | Proposed direct parent | Current status |
|---|---|---|---|---|
| [SO101-84](https://huu-hoan-hoang.atlassian.net/browse/SO101-84) — Freeze the Project B extension questions protocol and trial budget | Task | [SO101-81](https://huu-hoan-hoang.atlassian.net/browse/SO101-81) | B2 — new provisional epic | To Do |
| [SO101-85](https://huu-hoan-hoang.atlassian.net/browse/SO101-85) — Harden the experiment console simulator reliability and evidence export | Task | [SO101-81](https://huu-hoan-hoang.atlassian.net/browse/SO101-81) | B2 — new provisional epic | To Do |
| [SO101-86](https://huu-hoan-hoang.atlassian.net/browse/SO101-86) — Pilot the extension and freeze the accepted experiment setup | Task | [SO101-81](https://huu-hoan-hoang.atlassian.net/browse/SO101-81) | B2 — new provisional epic | To Do |
| [SO101-103](https://huu-hoan-hoang.atlassian.net/browse/SO101-103) — Accept the stable Project B measurement components after delivery | Subtask | [SO101-86](https://huu-hoan-hoang.atlassian.net/browse/SO101-86) | [SO101-86](https://huu-hoan-hoang.atlassian.net/browse/SO101-86) | To Do |
| [SO101-104](https://huu-hoan-hoang.atlassian.net/browse/SO101-104) — Freeze the accepted Project B experiment setup before the campaign | Subtask | [SO101-86](https://huu-hoan-hoang.atlassian.net/browse/SO101-86) | [SO101-86](https://huu-hoan-hoang.atlassian.net/browse/SO101-86) | To Do |
| [SO101-87](https://huu-hoan-hoang.atlassian.net/browse/SO101-87) — Run the expanded matched simulation and VENTUNO Q campaign | Task | [SO101-81](https://huu-hoan-hoang.atlassian.net/browse/SO101-81) | B2 — new provisional epic | To Do |
| [SO101-91](https://huu-hoan-hoang.atlassian.net/browse/SO101-91) — Complete core reruns robustness tests and final evidence freeze | Task | [SO101-81](https://huu-hoan-hoang.atlassian.net/browse/SO101-81) | B2 — new provisional epic | To Do |
| [SO101-105](https://huu-hoan-hoang.atlassian.net/browse/SO101-105) — Run core board reruns in the reserved post-physical-test window | Subtask | [SO101-91](https://huu-hoan-hoang.atlassian.net/browse/SO101-91) | [SO101-91](https://huu-hoan-hoang.atlassian.net/browse/SO101-91) | To Do |
| [SO101-92](https://huu-hoan-hoang.atlassian.net/browse/SO101-92) — Analyse the final evidence and independently reproduce the key results | Task | [SO101-81](https://huu-hoan-hoang.atlassian.net/browse/SO101-81) | B2 — new provisional epic | To Do |

### B3. Conditional commercial-arm validation

**Proposed epic:** New provisional epic; defer creation to Project B rebaseline.  
**Completion boundary:** If hardware arrives and readiness gates pass, calibration/pilot and physical comparisons are evidenced. Otherwise retain a documented conditional/deferred outcome without claiming validation.

**Placement rationale:** Hardware arrival and Project B staffing remain unconfirmed. SO101-88 stays unassigned in this plan. This epic does not block the mandatory simulation/board research.

| Existing issue and current title | Current type | Current direct parent | Proposed direct parent | Current status |
|---|---|---|---|---|
| [SO101-88](https://huu-hoan-hoang.atlassian.net/browse/SO101-88) — Receive calibrate and pilot the commercial arm if it arrives | Task | [SO101-81](https://huu-hoan-hoang.atlassian.net/browse/SO101-81) | B3 — new provisional epic | To Do |
| [SO101-89](https://huu-hoan-hoang.atlassian.net/browse/SO101-89) — Prepare and run the conditional physical comparison campaign | Task | [SO101-81](https://huu-hoan-hoang.atlassian.net/browse/SO101-81) | B3 — new provisional epic | To Do |
| [SO101-90](https://huu-hoan-hoang.atlassian.net/browse/SO101-90) — Run the conditional physical comparisons after core board measurements close | Subtask | [SO101-89](https://huu-hoan-hoang.atlassian.net/browse/SO101-89) | [SO101-89](https://huu-hoan-hoang.atlassian.net/browse/SO101-89) | To Do |

### B4. Final research release and handover

**Proposed epic:** Eventually narrow/rename SO101-81; defer to Project B rebaseline.  
**Completion boundary:** The reviewed Project B report, demonstration release, submission and handover are complete against the confirmed course calendar.

**Placement rationale:** SO101-81 remains the existing provisional container until the deferred B split is approved. Its proposed destination here describes the final structure, not an immediate rename.

| Existing issue and current title | Current type | Current direct parent | Proposed direct parent | Current status |
|---|---|---|---|---|
| [SO101-93](https://huu-hoan-hoang.atlassian.net/browse/SO101-93) — Compile the final Project B report from reviewed analysis | Task | [SO101-81](https://huu-hoan-hoang.atlassian.net/browse/SO101-81) | SO101-81 (B4, deferred) | To Do |
| [SO101-94](https://huu-hoan-hoang.atlassian.net/browse/SO101-94) — Prepare the Beta demonstration release and handover candidate | Task | [SO101-81](https://huu-hoan-hoang.atlassian.net/browse/SO101-81) | SO101-81 (B4, deferred) | To Do |
| [SO101-95](https://huu-hoan-hoang.atlassian.net/browse/SO101-95) — Review and correct the Project B report demonstration and release | Task | [SO101-81](https://huu-hoan-hoang.atlassian.net/browse/SO101-81) | SO101-81 (B4, deferred) | To Do |
| [SO101-96](https://huu-hoan-hoang.atlassian.net/browse/SO101-96) — Reserve final Project B submission demonstration and closeout | Task | [SO101-81](https://huu-hoan-hoang.atlassian.net/browse/SO101-81) | SO101-81 (B4, deferred) | To Do |

### PM. Standalone project governance — no epic

**Proposed epic:** No epic parent.  
**Completion boundary:** Maintain project-wide coordination without creating a permanent catch-all epic.

**Placement rationale:** These are cross-project meetings, capacity, scheduling, governance and risk coordination. Use a pm label and a governance filter. Specific risk-mitigation implementation belongs in the relevant delivery epic.

| Existing issue and current title | Current type | Current direct parent | Proposed direct parent | Current status |
|---|---|---|---|---|
| [SO101-16](https://huu-hoan-hoang.atlassian.net/browse/SO101-16) — Hold the Sprint 1 review and project meeting | Task | [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) | None — standalone | To Do |
| [SO101-17](https://huu-hoan-hoang.atlassian.net/browse/SO101-17) — Hold the Sprint 2 review and project meeting | Task | [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) | None — standalone | To Do |
| [SO101-24](https://huu-hoan-hoang.atlassian.net/browse/SO101-24) — Confirm team capacity, decision ownership and KOST support plan | Task | [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) | None — standalone | Done |
| [SO101-26](https://huu-hoan-hoang.atlassian.net/browse/SO101-26) — Maintain sprint membership, course milestones and delivery handoffs | Task | [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) | None — standalone | In Progress |
| [SO101-27](https://huu-hoan-hoang.atlassian.net/browse/SO101-27) — Approve collaboration, repository, document review and conduct rules | Task | [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) | None — standalone | To Do |
| [SO101-28](https://huu-hoan-hoang.atlassian.net/browse/SO101-28) — Approve risk owners, rankings, review cadence and escalation triggers | Task | [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) | None — standalone | To Do |

## 4. Required structural changes and scope clarifications

These are proposals for a later approved migration. None has been applied.

### 4.1 Promote three subtasks while preserving their keys and history

| Existing issue | Current parent | Proposed type and epic | Reason / boundary |
|---|---|---|---|
| [SO101-56](https://huu-hoan-hoang.atlassian.net/browse/SO101-56) | SO101-8 | Task → A3 / SO101-4 | The minimal runner/logger must be independently ready for board measurements before the full console backend is complete. SO101-8 consumes it, rather than implementing it again. |
| [SO101-58](https://huu-hoan-hoang.atlassian.net/browse/SO101-58) | SO101-46 | Task → A3 / SO101-4 | Early end-to-end measurement acceptance is a separate deliverable from the later console integration. |
| [SO101-71](https://huu-hoan-hoang.atlassian.net/browse/SO101-71) | SO101-46 | Task → A6 / SO101-1 | Final defect-closure checks and independent reproduction support final evidence acceptance; technical fixes remain with their owning implementation tasks or linked bugs. |

All other **33 existing subtasks retain their current task parent**. They follow that parent's proposed epic. There are no new subtask-to-task reparentings in this proposal.

Before any later conversion, verify the site's supported conversion operation and required fields, capture the old type/parent, and confirm the same key and history survive. Do not substitute delete-and-recreate if conversion is unavailable.

### 4.2 Narrow oversized tasks instead of duplicating their work

| Existing issue | Proposed summary / responsibility | How overlap is removed |
|---|---|---|
| SO101-12 | **Consolidate and accept the three-model baseline comparison** | New BASE-01–03 tasks own each model's training/evaluation. SO101-12 owns synthesis, reference freeze, review and report; SO101-44/52/53 stay beneath it. Selection evidence remains in SO101-33/102. |
| SO101-18 | **Coordinate the nine-profile comparison and deliver the reviewed report** | New PROFILE-01–09 tasks own per-profile conversion, calibration, actual board/simulation runs and required reruns. SO101-18 owns campaign-wide acceptance and reporting. |
| SO101-59 | **Verify conversion, calibration and probe evidence across all nine profiles** | Review the nine profile tasks' evidence; do not repeat their conversion work. Remains a subtask of SO101-18. |
| SO101-60 | **Review the first-run or blocker matrix for all nine profiles** | Aggregate linked profile results and escalate evidenced blockers. A blocked profile is not a completed required profile. Remains under SO101-18. |
| SO101-61 | **Accept coverage and comparability of the matched nine-profile campaign** | Check protocol consistency and cross-profile coverage; individual execution stays in profile tasks. Remains under SO101-18. |
| SO101-62 | **Verify required reruns and freeze the nine-profile evidence set** | Profile owners execute reruns; this subtask verifies their disposition and freezes the shared evidence manifest. Remains under SO101-18. |
| SO101-46 | **Integrate the full console with the AI, board, MCU and simulator** | Early measurement acceptance moves out as SO101-58; final independent reproduction moves out as SO101-71. SO101-70 remains the full-integration acceptance subtask. |
| SO101-71 | **Accept integration fixes and independently reproduce Project A evidence** | Check linked fixes and independently reproduce outputs before SO101-30/72 final approval. Do not create a second implementation backlog inside this task. |
| SO101-34 | **Verify approved VENTUNO Q runtime and precision/resource test readiness** | Preserve approved local decisions and their evidence classifications. Record remaining board verification and mismatches; changes to approved decisions require their own decision record. |

SO101-45 remains the report-writing subtask of SO101-18, and SO101-63 remains its technical report-review subtask. SO101-52/53 remain distinct reference-freeze and review deliverables beneath SO101-12.

### 4.3 Carry bounded chat scope into the existing console work

This proposes where to record the already-approved scope, not a new choice of language model or control behavior.

| Existing issue | Proposed handling under A5 |
|---|---|
| SO101-42 | Define the bounded typed-request workflow, permitted requests, ambiguity/unsupported-request behavior and required evidence. Surface unresolved choices explicitly. |
| SO101-99 | Record acceptance of the revised workflow and evidence schema after those choices are settled. |
| SO101-6 | Include the approved chat interface design/frontend work. Keep completed SO101-5 as historical sketch evidence; do not treat its Done status as evidence that chat design is finished. |
| SO101-8 | Implement the approved request-to-command validation path and logging. Do not assume that a language model is required or already selected. |
| SO101-46/70 | Verify the approved chat behavior during integrated console acceptance, including rejection without execution and retained abort access. |

No extra chat issue is created by this mapping. If refinement shows separately deliverable chat work, propose additional tasks within A5 before creating them.

## 5. Proposed new standard tasks — no Jira keys yet

The following are planning placeholders, not existing issues, not extra epic levels, and not subtasks of SO101-12/18. Each would be a direct child of its indicated epic. Owners, estimates, dates and sprint membership for these new records require allocation from the existing approved plan and actual capacity; they are not invented here.

### 5.1 Three baseline tasks under A2 / SO101-3

| Placeholder | Proposed task | Completion evidence |
|---|---|---|
| BASE-01 | Train and evaluate the SmolVLA reference baseline | Approved recipe, exact dataset/split/checkpoint/configuration revisions, training/validation record, protocol-compliant evaluation and linked failures/limitations. |
| BASE-02 | Train and evaluate the ACT reference baseline | Same evidence requirements, using ACT's approved recipe and reference. |
| BASE-03 | Train and evaluate the Diffusion Policy reference baseline | Same evidence requirements, using Diffusion Policy's approved recipe and reference. |

Extract work/evidence already recorded under SO101-12 into these tasks by reference. Do not imply training must be repeated if valid evidence already exists. Newly created statuses must be based on checked evidence, not guessed from SO101-12's In Progress status.

### 5.2 Nine profile tasks under A4

| Placeholder | Proposed task |
|---|---|
| PROFILE-01 | Convert, deploy and evaluate SmolVLA FP16 |
| PROFILE-02 | Convert, deploy and evaluate SmolVLA INT8-mixed |
| PROFILE-03 | Convert, deploy and evaluate SmolVLA INT4-mixed |
| PROFILE-04 | Convert, deploy and evaluate ACT FP16 |
| PROFILE-05 | Convert, deploy and evaluate ACT INT8-mixed |
| PROFILE-06 | Convert, deploy and evaluate ACT INT4-mixed |
| PROFILE-07 | Convert, deploy and evaluate Diffusion Policy FP16 |
| PROFILE-08 | Convert, deploy and evaluate Diffusion Policy INT8-mixed |
| PROFILE-09 | Convert, deploy and evaluate Diffusion Policy INT4-mixed |

Each profile task must link:

- The frozen trained reference, profile artifact, exact revisions and approved runtime/compute placement.
- Calibration provenance, actual weight/activation precision and quantized coverage, exceptions and runtime/delegation evidence.
- Conversion/load/parity evidence, actual VENTUNO Q measurements and matched simulation outcomes under the approved protocol.
- Raw results, required reruns, failures, unsupported-path evidence and limitations.
- The reviewer decision and the report/evidence-manifest entry.

Use the approved precision definitions in decision 0002 and assumptions A-001–A-004. INT4-mixed is not a claim that every operation or weight executes at four bits. Numerical criteria come from approved records; this document adds none.

Conversion preparation can proceed when its own prerequisites are met. Scored comparisons depend on the accepted protocol, frozen references and SO101-58 measurement-path acceptance. Unsupported combinations stay visible and require an explicit decision; no silent omission or substitution.

### 5.3 Resulting counts if the entire proposal is later adopted

- Existing work items retained: 90 (54 Tasks + 36 Subtasks).
- Three promotions: 57 Tasks + 33 Subtasks; still 90 existing work items.
- Twelve new standard tasks: **69 Tasks + 33 Subtasks = 102 non-epic items**.
- Final target after both stages: **10 epics**, reusing all five existing epic keys and adding five.
- Final target total: **112 issues**, including six standalone PM Tasks.
- Stage A only would add two epics and twelve tasks: **109 total issues**, with Project B still under its provisional container until the later split.

These counts are planning arithmetic, not a report of Jira mutations.

## 6. Dependency and placement rules

These describe dependencies to review, not verified existing Jira issue links.

| Consumer / deliverable | Prerequisite or evidence input |
|---|---|
| A1 benchmark/protocol | A2 dataset and model compatibility evidence; A3 early runtime feasibility where required. Treat readiness as named issue-level handoffs, not blanket epic-to-epic blocks. |
| BASE-01–03 scored baseline work | Approved data/learning choices, final model selection and applicable benchmark/protocol acceptance. |
| A3 measurement acceptance / SO101-58 | Shared architecture/interface contract, available access/setup, communication/fault tests, SO101-56 runner/logger and SO101-57 early MCU–simulator path. |
| PROFILE-01–09 scored runs | Frozen model references, approved protocol/runtime definitions and SO101-58 acceptance. Conversion preparation may overlap path delivery. |
| A5 console implementation | Shared A3 architecture/contract and runner/logger; console scope decisions under SO101-42/99. |
| SO101-46/70 full integration | Console components and the accepted measurement path. |
| SO101-71 final reproduction | Integration results, resolved linked defects and accepted experiment evidence. |
| SO101-30/72 final approval | Final reproduction and evidence/report readiness. |
| SO101-77/78/79 final package | Reviewed reports, manifest/archive, final acceptance and course checklist. |
| B2 expanded campaign | B1 reproduced baseline and approved extension protocol/setup. |
| B3 physical campaign | Actual arm receipt/readiness and approved physical-test decisions; no assumed arrival or invented future staffing. |
| B4 final release | Accepted core analysis and evidence; include physical claims only when B3 actually provides them. |

The fixed Project Plan submission (SO101-73) does not wait for unavailable final experimental results. Its plan must state verified progress and limitations. Do not turn this mapping into a new prerequisite that blocks submission.

## 7. Reconciliation items before any later migration

1. **Live status versus evidence:** preserve current workflow states until checked. As fetched, SO101-11 and SO101-43 are both Done; older local notes saying SO101-43 is To Do are stale. SO101-23 is In Review while SO101-98 is Done. SO101-25 is Done while SO101-48 remains To Do.
2. **Runtime approval versus verification:** approved local runtime/precision choices exist, while SO101-34 is To Do. Separate those two facts in a later description update.
3. **Wrong phase label:** SO101-100 is a Project A benchmark pilot carrying `semester-2-provisional`. Propose correcting it to Project A after scope review; its destination is A1.
4. **Past/today deadlines:** the baseline task SO101-12 is In Progress against the recorded 24 October report deadline; SO101-73 is To Do with the 25 October Project Plan deadline. Check artifacts/receipts before interpreting actual delivery.
5. **Sprint records:** the earlier board inspection returned three future-state sprints and no active sprint; sprint goals contained superseded printing/hardware-checkpoint language. Refresh before any later cleanup. No sprint replacement, activation or reassignment is part of this mapping.
6. **Project B calendar and staffing:** retain provisional dates as provisional. SO101-88 remains unassigned; no physical arrival or staffing commitment is made.
7. **Retired work:** do not recreate absent printed-arm issues or reintroduce a Project A arm-arrival gate.
8. **Completed issues:** regrouping Done work must not reopen it or assert it satisfies newer scope. In particular, SO101-5 is historical sketch work, not proof of completed chat-interface design.
9. **PM tasks:** removing the epic parent of SO101-16/17/24/26/27/28 does not remove them from the project or erase their dates/history.

## 8. Proposed execution sequence — not executed

### Stage A: Project A structure, only after explicit approval

1. Capture a fresh pre-change snapshot of all affected issue fields and parent/type relations.
2. Create A1/A4 and rename/narrow SO101-1/2/3/4 using the completion boundaries above.
3. Reparent existing standard tasks to their mapped A epics; keep subtasks under their existing tasks except the three explicit promotions.
4. Promote SO101-56/58/71 with key/history preservation and assign their proposed epic parents.
5. Detach the six standalone PM tasks from the old catch-all epic; retain governance visibility.
6. Apply approved scope/title clarifications and create BASE-01–03 / PROFILE-01–09 without duplicating execution ownership.
7. For the interim Project B state, move SO101-80 from SO101-1 to the existing provisional SO101-81 container, preserving its dates and sprint membership; record B1 as its intended final destination.
8. Verify every affected parent/type, dependency, description and preserved field. Do not change completion status simply because an item was moved.

### Stage B: Project B structure, deferred until rebaseline/approval

1. Confirm the course calendar, research questions, real hardware availability and actual future ownership.
2. If the B1–B4 grouping is still appropriate, create B1/B2/B3 and move the mapped tasks with their subtasks.
3. Narrow/rename SO101-81 to B4 only after its unrelated children have been reassigned.
4. Keep conditional physical work out of mandatory core-completion criteria.

If only Stage A is approved, the complete B mapping remains a documented target; it does not authorize Stage B.

## 9. How to verify this plan

- Compare the 90 linked items in section 3 against the live SO101 project query; each current Task/Subtask should appear in exactly one destination section.
- Check the five original epics against section 2; every existing epic key has a disposition.
- Check every retained subtask's proposed task parent and verify it resolves to the same destination epic.
- Review the three promotions and the narrowed scopes before authorizing conversion.
- Confirm that new BASE/PROFILE placeholders have no assigned Jira keys and do not duplicate work remaining in the aggregate tasks.
- Confirm the six standalone PM tasks, the bounded-chat handling and the deferred Project B split.
- Confirm no dates, owners, sprint memberships or measured results have been invented.

Mechanical document checks performed during authoring: all 90 non-epic issues mapped; no duplicate assignments; no unknown issue keys; all 33 retained subtasks share their proposed epic with their retained parent; exactly three explicit promotions. Human review and approval remain pending.

## 10. Source records and assistance disclosure

1. [SO101 board](https://huu-hoan-hoang.atlassian.net/jira/software/projects/SO101/boards/2) and read-only Jira inventory fetched on 25 October 2026. Exact issue links appear in section 3. [Verified]
2. [Repository project guidance](../../../CLAUDE.md), including authority, scope, team, schedule and preservation rules. [Verified]
3. [Approved assumptions](../../technical/assumptions.md), especially A-001–A-004 for runtime, precision and evidence definitions. [Verified]
4. [Decision 0005 — bounded console chat](../../technical/decisions/0005-console-bounded-chat-interface.md), including approved scope and open interface values. [Verified]
5. The preceding chat proposal for six Project A epics, future Project B outcomes and separate governance tasks. The destination grouping and task decomposition are recommendations, not previously approved decisions. [Reasoning]

Prepared with Codex assistance at Hoan's request to list every task/subtask and save the proposal in Markdown before execution. At the proposal stage, assistance was limited to reading Jira/local records, proposing the mapping, writing this document and checking its coverage. The later authorized Jira execution is recorded in section 11. No experiment result is claimed.

## 11. Execution record — 25 October 2026

Authorization: Hoan replied **“Execute”** after the full mapping was saved. This authorized Stage A as documented; the Project B split and sprint redesign remain deferred.

### Applied Stage A work

- Created A1 [SO101-107](https://huu-hoan-hoang.atlassian.net/browse/SO101-107) and A4 [SO101-108](https://huu-hoan-hoang.atlassian.net/browse/SO101-108).
- Renamed/narrowed the four existing Project A epics: A2 [SO101-3](https://huu-hoan-hoang.atlassian.net/browse/SO101-3), A3 [SO101-4](https://huu-hoan-hoang.atlassian.net/browse/SO101-4), A5 [SO101-2](https://huu-hoan-hoang.atlassian.net/browse/SO101-2), A6 [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1).
- Applied all 18 planned standard-task parent changes, including detaching the six standalone PM tasks and moving SO101-80 into provisional SO101-81.
- Applied the agreed aggregate-task scope clarifications and bounded-chat allocation. Original description content was retained beneath the current-scope amendments.
- Added project-a/project-b and migration labels while preserving prior labels, except the explicitly identified wrong semester-2-provisional label on SO101-100. Added pm/governance visibility for the six standalone tasks.
- Created the 12 planned tasks listed below. New task owners, dates, estimates and sprint membership remain unset as specified by the plan.
- Added 60 issue links for the new tasks. Frozen reference availability blocks profile tasks; measurement acceptance relates to them, with descriptions explicitly gating scored runs while allowing earlier conversion preparation.
- Preserved all 120 pre-existing issue links.

### Actual epic and task keys

| Plan alias | Actual Jira issue |
|---|---|
| A1 | [SO101-107](https://huu-hoan-hoang.atlassian.net/browse/SO101-107) |
| A2 | [SO101-3](https://huu-hoan-hoang.atlassian.net/browse/SO101-3) |
| A3 | [SO101-4](https://huu-hoan-hoang.atlassian.net/browse/SO101-4) |
| A4 | [SO101-108](https://huu-hoan-hoang.atlassian.net/browse/SO101-108) |
| A5 | [SO101-2](https://huu-hoan-hoang.atlassian.net/browse/SO101-2) |
| A6 | [SO101-1](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) |

| Placeholder | Created issue | Summary |
|---|---|---|
| BASE-01 | [SO101-109](https://huu-hoan-hoang.atlassian.net/browse/SO101-109) | Train and evaluate the SmolVLA reference baseline |
| BASE-02 | [SO101-110](https://huu-hoan-hoang.atlassian.net/browse/SO101-110) | Train and evaluate the ACT reference baseline |
| BASE-03 | [SO101-111](https://huu-hoan-hoang.atlassian.net/browse/SO101-111) | Train and evaluate the Diffusion Policy reference baseline |
| PROFILE-01 | [SO101-112](https://huu-hoan-hoang.atlassian.net/browse/SO101-112) | Convert, deploy and evaluate SmolVLA FP16 |
| PROFILE-02 | [SO101-113](https://huu-hoan-hoang.atlassian.net/browse/SO101-113) | Convert, deploy and evaluate SmolVLA INT8-mixed |
| PROFILE-03 | [SO101-114](https://huu-hoan-hoang.atlassian.net/browse/SO101-114) | Convert, deploy and evaluate SmolVLA INT4-mixed |
| PROFILE-04 | [SO101-115](https://huu-hoan-hoang.atlassian.net/browse/SO101-115) | Convert, deploy and evaluate ACT FP16 |
| PROFILE-05 | [SO101-116](https://huu-hoan-hoang.atlassian.net/browse/SO101-116) | Convert, deploy and evaluate ACT INT8-mixed |
| PROFILE-06 | [SO101-117](https://huu-hoan-hoang.atlassian.net/browse/SO101-117) | Convert, deploy and evaluate ACT INT4-mixed |
| PROFILE-07 | [SO101-118](https://huu-hoan-hoang.atlassian.net/browse/SO101-118) | Convert, deploy and evaluate Diffusion Policy FP16 |
| PROFILE-08 | [SO101-119](https://huu-hoan-hoang.atlassian.net/browse/SO101-119) | Convert, deploy and evaluate Diffusion Policy INT8-mixed |
| PROFILE-09 | [SO101-120](https://huu-hoan-hoang.atlassian.net/browse/SO101-120) | Convert, deploy and evaluate Diffusion Policy INT4-mixed |

### Completed: three separately confirmed Move conversions

The Atlassian conversion tool could not promote these through a direct edit. It returned **MOVE_CONFIRMATION_REQUIRED** for Jira's Move fallback. Hoan explicitly replied **“Approve conversions and restore Medium priority”**. All three conversions have now been completed with their original issue keys and IDs retained.

| Issue | Previous type / parent | Verified final type / parent | Move destination and status |
|---|---|---|---|
| [SO101-56](https://huu-hoan-hoang.atlassian.net/browse/SO101-56) | Subtask / SO101-8 | Task / SO101-4 | SO101; To Do → To Do |
| [SO101-58](https://huu-hoan-hoang.atlassian.net/browse/SO101-58) | Subtask / SO101-46 | Task / SO101-4 | SO101; To Do → To Do |
| [SO101-71](https://huu-hoan-hoang.atlassian.net/browse/SO101-71) | Subtask / SO101-46 | Task / SO101-1 | SO101; To Do → To Do |

For each conversion Jira reported dropping **Priority** and computed **Status category**. After the approved conversions, **Medium** priority was explicitly restored and the derived status category verified as **To Do**. The Move also cleared inherited sprint membership; all three were restored to their original **SO101 Sprint 2 (ID 3)** and verified. Due/start dates, owners, original IDs, reporters and creation timestamps remain unchanged.

SO101-56 and SO101-58 are now direct Tasks of A3 / SO101-4. SO101-71 is now a direct Task of A6 / SO101-1. Their issue links remain intact. Pending-conversion wording in the current Jira scope amendments was replaced with the confirmed final placement.

### Read-back verification

- Total Jira issues: **109**, comprising **7 Epics, 69 Tasks and 33 Subtasks** after the three promotions.
- Promotion changed issue types and parents while retaining the total issue count and original IDs.
- All 95 original issue keys still exist.
- Original owners, reporters, creation timestamps, statuses, priorities, due dates, start dates and sprint memberships were compared with the pre-change snapshot: **no differences**.
- Existing parent assignments and issue types match the approved Stage A mapping, including all three promotions.
- The six PM tasks have no epic parent and carry pm/governance labels: [open governance work](https://huu-hoan-hoang.atlassian.net/issues/?jql=project%20%3D%20SO101%20AND%20labels%20%3D%20governance%20ORDER%20BY%20Rank%20ASC). This is a direct filtered Jira view; no custom board-filter control was created.
- All 12 new tasks have their correct epic parents.
- All 120 original issue links remain and all 60 intended new links are present.
- No experimental result, submission receipt or completion state was asserted by this reorganization.
- Stage B is still provisional under SO101-81; no B1/B2/B3 epic has been created.

### Audit files

- [Pre-change snapshot](snapshots/2026-10-25-before-reorganization.json)
- [Final completed snapshot, verification and full operation log](snapshots/2026-10-25-reorganization-complete.json)
- [Historical post-change snapshot before promotions](snapshots/2026-10-25-after-reorganization.json)
- [Historical operation log before promotions](snapshots/2026-10-25-reorganization-execution.json)
- [Intermediate recovery checkpoint](snapshots/2026-10-25-reorganization-checkpoint.json)

The original proposal and inventory in sections 1–10 remain a dated planning record. This execution section supersedes their “not executed” wording for the completed Stage A actions. Hoan explicitly approved execution and the separately confirmed Move conversions. **Stage A has no remaining reorganization actions.** Stage B remains deferred until Project B rebaseline/approval; the unrelated sprint-redesign proposal remains unexecuted.

## 12. Current model and allocation amendment — 25 October 2026

This section supersedes model names, dates and ownership in the original mapping where changed below. The reorganization itself remains complete. Source: Hoan's subsequent explicit instruction; see [decision 0006](../../technical/decisions/0006-model-roster-baseline-and-profile-allocation.md).

### Baselines — Duc owns all three, with Hoan supporting

| Issue | Current model | Start | Due | Status after update |
|---|---|---|---|---|
| [SO101-109](https://huu-hoan-hoang.atlassian.net/browse/SO101-109) | SmolVLA | 13 October 2026 | 24 October 2026 | Done — user-reported completion |
| [SO101-110](https://huu-hoan-hoang.atlassian.net/browse/SO101-110) | Pi0, replacing ACT | 23 October 2026 | 1 November 2026 | To Do — no completion inferred |
| [SO101-111](https://huu-hoan-hoang.atlassian.net/browse/SO101-111) | X-VLA, replacing Diffusion Policy | 23 October 2026 | 1 November 2026 | To Do — no completion inferred |

SO101-12/44/52/53 working consolidation, reporting, reference-freeze and review handoffs were aligned to 1 November. The original full-baseline report target of 24 October is retained as historical context, not claimed as an official extended university deadline.

### Nine-profile allocation — every item uses 1–19 November 2026

| Model | FP16 | INT8-mixed | INT4-mixed |
|---|---|---|---|
| SmolVLA | Hoan — SO101-112 | Hoan — SO101-113 | Hoan — SO101-114 |
| Pi0 | Hoan — SO101-115 | Duc — SO101-116 | Duc — SO101-117 |
| X-VLA | Duc — SO101-118 | Duc — SO101-119 | Duc — SO101-120 |

This implements the authorized ownership split as four profiles for Hoan and five for Duc; it is not an effort/capacity estimate.

| Coordination / acceptance work | Primary owner | Window |
|---|---|---|
| SO101-108 epic and SO101-18 campaign coordination | Hoan (deployment primary responder); Duc support — amended 25 October; previously Duc, with Hoan co-owning delivery | 1–19 November |
| SO101-45 report writing | Hoan | 1–19 November |
| SO101-59 cross-profile conversion/calibration evidence verification | Duc | 1–19 November |
| SO101-60 first-run/blocker matrix review | Hoan | 1–19 November |
| SO101-61 matched-campaign coverage/comparability acceptance | Duc | 1–19 November |
| SO101-62 rerun disposition and evidence freeze | Hoan | 1–19 November |
| SO101-63 technical report review | Duc | 1–19 November |

**Ownership amendment, 25 October 2026:** at Hoan's instruction, SO101-108 and SO101-18 were reassigned from Duc to Hoan, with a support comment on each (IDs 10003, 10004). The profile split and the other rows above are unchanged. See the amendment in decision 0006.

All nine direct profile Tasks, the campaign Task, six campaign Subtasks and the Epic have actual Start date = 2026-11-01 and Due date = 2026-11-19.

### Scope, evidence and schedule consequences

- The active experiment matrix is now SmolVLA, Pi0 and X-VLA × three precisions. ACT/Diffusion Policy are removed from active scope; their existing issue keys were reused for the replacements and their previous descriptions preserved as collapsed superseded history.
- Pi0/X-VLA exact checkpoint revisions, adaptation recipes, input/action mapping, runtime compatibility, quantization coverage and native precision execution require evidence. Previous ACT/DP-specific findings do not establish support for them.
- The new comparison window supersedes the old 14 November working report target in affected work.
- The 15 November course-package and 6 December final deadlines remain unchanged. SO101-74 explicitly records that the course package must use available interim evidence and limitations, rather than claim final comparison results scheduled for 19 November.
- A reported completed SmolVLA baseline does not mark its FP16/INT8/INT4 profile experiments complete.

### Verification and audit

31 Jira issues were updated for scope/allocation/date consistency. All 109 issues were read back; issue IDs/keys, hierarchy, links, priorities and sprint memberships were preserved. Only SO101-109 changed workflow status, following Hoan's explicit completion report. All planned owner/date/title values matched the read-back; no discrepancies remained.

- [Pre-change snapshot](snapshots/2026-10-25-before-model-roster-update.json)
- [Updated snapshot, exact edit log and verification](snapshots/2026-10-25-model-roster-update.json)

Earlier snapshots retain their capture-time model roster and are historical, not the current allocation.

## 13. Current refined epic timelines — 25 October 2026

The later instruction “Then refine the timeline of each epic” was applied after section 12. The [refined timeline and complete child-handoff schedule](SO101_Epic_Timeline_Refinement_2026-10-25.md) supersede earlier date windows where they differ. Model selection and owners from section 12 remain unchanged.

| Epic | Current start | Current due |
|---|---|---|
| [SO101-107 — Benchmark and evaluation protocol](https://huu-hoan-hoang.atlassian.net/browse/SO101-107) | 2026-10-12 | 2026-10-31 |
| [SO101-3 — Three-model baseline comparison](https://huu-hoan-hoang.atlassian.net/browse/SO101-3) | 2026-10-12 | 2026-11-01 |
| [SO101-4 — VENTUNO Q–MCU–simulator measurement path](https://huu-hoan-hoang.atlassian.net/browse/SO101-4) | 2026-10-12 | 2026-11-20 |
| [SO101-108 — Nine-profile precision comparison](https://huu-hoan-hoang.atlassian.net/browse/SO101-108) | 2026-11-01 | 2026-11-19 |
| [SO101-2 — Experiment console and integrated demonstration](https://huu-hoan-hoang.atlassian.net/browse/SO101-2) | 2026-10-12 | 2026-12-03 |
| [SO101-1 — Project A submission and reproducible handover](https://huu-hoan-hoang.atlassian.net/browse/SO101-1) | 2026-10-12 | 2026-12-06 |
| [SO101-81 — Project B provisional roadmap](https://huu-hoan-hoang.atlassian.net/browse/SO101-81) | 2027-01-11 | 2027-05-12 |

The comparison campaign/Epic remain 1–19 November. Profile execution is now 1–16 November, shared evidence freeze is 17 November, report completion is 18 November and final technical review is 19 November. This refines the uniform child windows from the initial allocation.

SO101-58 path acceptance now targets 1 November after the baseline reference freeze. Final comparison/report items SO101-18/45/63 are now Relates links to the 15 November course-package submission; SO101-53 remains its baseline-review prerequisite. The package carries interim comparison evidence and limitations. Final university submission remains 6 December.

Project B retains 11 January–12 May 2027 as its provisional main execution window; the official deadline remains unknown. SO101-80 is explicitly earlier calendar/requirements preparation. No Project B split or sprint redesign was executed.

Read-back verification covered all 109 issues and 47 planned edits. Owners, statuses, priorities, hierarchy and sprint memberships were preserved. Exactly three dependency links changed type, the link total remains 180 and no cycles were found. See [final snapshot and operation log](snapshots/2026-10-25-epic-timeline-refinement.json) and [decision 0007](../../technical/decisions/0007-epic-timeline-and-handoff-refinement.md).




