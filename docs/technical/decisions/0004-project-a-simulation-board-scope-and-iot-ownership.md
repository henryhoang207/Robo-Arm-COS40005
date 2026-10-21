# 0004 — Project A simulation/board scope and sole IoT ownership

Date: 2026-10-21 (Asia/Bangkok)
Status: Approved by Hoan, in the current chat.
Decision owner: Hoan (PM).

## Decision

Project A removes the printed-arm production branch. Its remaining deliverables are the bounded pick-and-place simulation benchmark, three trained model references, nine VENTUNO Q model/precision profiles, reports and minimum experiment console.

Remove work confined to printed-part approval, fallback BOM/orders, component receipt, mechanical assembly, powered arm calibration and physical positioning trials. The 30 November printed-arm availability/fallback checkpoint is superseded. Retain shared GPU/board access, simulator, AI/MCU communication, command validation, bench/simulator fault tests, integration and reproducibility work. Existing report/course dates and the sprint membership/status of retained tasks stay in force.

Chung is the sole Project A IoT member and owns all retained IoT work, including the simulator tasks previously assigned to Nguyen. AI remains Duc and Hoan; software remains Khanh and Trieu; Hoan owns PM, integration and reporting. This gives five active Project A members. Reassess Chung's task load and handoff conflicts; no capacity estimate is implied by reassignment.

## Acknowledgment

The team acknowledges Nguyen for contributions during the earlier project phase. Nguyen is removed from active project-plan ownership and roster entries. Historical activity, authorship and contribution records remain intact. No unverified contribution details are added.

## Jira disposition

- SO101-13 (printing) was already absent when this change was inspected.
- Remove SO101-14, SO101-15 and SO101-64–69 from active work. These are the eight remaining tasks confined to the printed-arm branch.
- Retain and narrow SO101-25 to GPU/board access and SO101-38 to board/simulator transport, command validation and fault procedures, with SO101-48 and SO101-54 retained.
- Transfer SO101-21, SO101-40, SO101-47 and SO101-49 to Chung; their existing workflow states do not prove new work or acceptance.
- Retain core integration/retest/evidence tasks, including SO101-46, SO101-58 and SO101-70–72.
- Commercial-arm Project B tasks SO101-88–90 remain conditional and are independent of printing. Remove Nguyen's assignment from SO101-88; confirm its future owner at the Project B rebaseline. Project B staffing and its university deadline remain unresolved.

## Rationale and evidence

The user states that printing work has been removed, requests removal of associated work that is irrelevant to retained tasks, and confirms Chung as the only Project A IoT member. A 21 October Jira dependency review distinguishes the isolated printed-arm branch from the shared simulator, board, interface and reporting path.

This decision partially supersedes decision 0003's conditional printed-arm target and the physical-production portions of timeline version 3. It does not approve benchmark decision 0001, claim that runtime decision 0002 is verified, or establish physical performance from simulation.

## Remaining questions

Complete benchmark/protocol and action/state contract acceptance, approve risk rankings and review ownership, confirm member profile details, reconcile existing Jira evidence discrepancies and confirm Project B commercial-arm ownership at rebaseline. Technical thresholds and physical parameters are not invented by this scope change.

## Application evidence

Applied on 21 October 2026: seven obsolete issues were archived (SO101-14, SO101-15, SO101-65–69), SO101-64 was deleted, and the five obsolete links from retained tasks were removed. The active project contains 95 issues; none is assigned to Nguyen. All retained Project A IoT tasks are assigned to Chung. Retained workflow states are unchanged. See the dated Jira snapshot and AI usage record for the captured change evidence.
