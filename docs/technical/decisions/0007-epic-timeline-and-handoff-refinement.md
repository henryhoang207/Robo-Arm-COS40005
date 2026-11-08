# 0007 — Refined epic timelines and dependent handoffs

Date: 2026-10-25 (Asia/Bangkok)
Status: Applied working refinement authorized by Hoan's instruction, “Then refine the timeline of each epic”. Exact intermediate dates are assistant scheduling choices within the user's anchors.
Decision owner: Hoan (PM).

## Decision and rationale

Refine the six bounded Project A epics around the new SmolVLA/Pi0/X-VLA baselines, retain the 1–19 November comparison campaign and 6 December final, and retain Project B's provisional Jan–May execution envelope. Update supporting child handoffs so those epic windows correspond to actionable gates.

| Epic | Working start | Working due |
|---|---|---|
| SO101-107 — Benchmark and evaluation protocol | 2026-10-12 | 2026-10-31 |
| SO101-3 — Three-model baseline comparison | 2026-10-12 | 2026-11-01 |
| SO101-4 — VENTUNO Q–MCU–simulator measurement path | 2026-10-12 | 2026-11-20 |
| SO101-108 — Nine-profile precision comparison | 2026-11-01 | 2026-11-19 |
| SO101-2 — Experiment console and integrated demonstration | 2026-10-12 | 2026-12-03 |
| SO101-1 — Project A submission and reproducible handover | 2026-10-12 | 2026-12-06 |
| SO101-81 — Project B provisional roadmap | 2027-01-11 | 2027-05-12 |

The comparison profile Tasks now run 1–16 November; evidence freeze is 17 November; report completion is 18 November; technical review is 19 November. The campaign/Epic remain 1–19 November. Hoan/Duc ownership remains unchanged. Benchmark/protocol readiness targets 31 October, frozen baseline references and early path acceptance target 1 November, complete components target 20 November, integrated acceptance targets 26 November, technical correction/reproduction targets 3 December, final approval is 4 December and submission is 6 December.

The original SO101-52 → SO101-58 dependency could not support a 29 October measurement gate after references moved to 1 November; SO101-58 now targets 1 November. Same-day handoff has no calendar slack. Scored measurements start only after actual acceptance.

The final comparison/report work cannot block a 15 November interim course package when it now finishes 19 November. Replace SO101-18/45/63 → SO101-75 Blocks links with Relates and retain SO101-53's baseline-review blocker. The 15 November course deadline is unchanged.

No owner, workflow state, priority, sprint definition or membership, model selection or technical acceptance threshold changed. No measured throughput/capacity guarantee is introduced. Project B's official deadline remains unknown; 12 May 2027 is an internal reserve. SO101-80 remains earlier pre-semester preparation; no Project B epic split occurred.

## Sources and verification

Sources: Hoan's current instruction and preceding model/date amendment; live Jira parent/child dates and dependency graph; decision 0006. Detailed phases and every changed child date are in [the applied timeline](../../project-management/jira/SO101_Epic_Timeline_Refinement_2026-10-25.md).

Verification: read back all 109 issues; 47 planned issue edits matched; exactly three dependency types changed; all other links and preserved fields remained intact; no cycles found. Dates fit epic bounds except the explicitly documented preparation task. Pre/post snapshots and the operation log are linked from the timeline. This verifies record consistency, not execution or experimental feasibility.

