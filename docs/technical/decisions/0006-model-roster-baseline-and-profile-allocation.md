# 0006 — Model roster, baseline ownership and nine-profile comparison schedule

Date: 2026-10-25 (Asia/Bangkok)
Status: Approved by Hoan in this chat for the roster, baseline allocation/completion and date windows. The specific four/five profile split below is the assistant's implementation of Hoan's instruction to split ownership between Hoan and Duc.
Decision owner: Hoan (PM).
Amended: 2026-10-25 — campaign coordination ownership moved to Hoan; see *Amendment — deployment lead* below. The four/five profile split is unchanged.

Later timeline refinement: [decision 0007](0007-epic-timeline-and-handoff-refinement.md) retains the overall 1–19 November comparison window and the ownership split, while refining individual profile execution to 1–16 November, evidence freeze to 17 November, report completion to 18 November and final technical review to 19 November. The uniform child windows below are the initial allocation record; the linked refinement is the current dated schedule.

## User-authorized change

- Active models: **SmolVLA, Pi0 and X-VLA**. ACT and Diffusion Policy are removed from the active experiment matrix. Retain existing issue keys/history; replace their model scope instead of deleting issues.
- SO101-109: Duc owns SmolVLA baseline work, supported by Hoan. User reports it complete, performed **13–24 October 2026**. Record Done from that user report; no new experimental metrics are claimed.
- SO101-110: replace ACT with Pi0. Duc owns it, supported by Hoan; **23 October–1 November 2026**.
- SO101-111: replace Diffusion Policy with X-VLA. Duc owns it, supported by Hoan; **23 October–1 November 2026**.
- The nine-profile epic SO101-108, its direct Tasks (SO101-18, SO101-112–120) and SO101-18's subtasks (SO101-45, SO101-59–63) use **1–19 November 2026**, inclusive.
- The nine-profile matrix is three current models × FP16 / INT8-mixed / INT4-mixed. Model names identify scope; exact checkpoint revisions and native runtime support are not established by renaming.

## Profile ownership applied within the authorized split

| Model | FP16 | INT8-mixed | INT4-mixed |
|---|---|---|---|
| SmolVLA | Hoan — SO101-112 | Hoan — SO101-113 | Hoan — SO101-114 |
| Pi0 | Hoan — SO101-115 | Duc — SO101-116 | Duc — SO101-117 |
| X-VLA | Duc — SO101-118 | Duc — SO101-119 | Duc — SO101-120 |

Hoan owns four profiles; Duc owns five. Each supports and reviews the other's work. This is a count-based allocation, not a claim of equal effort or measured capacity. ~~Duc remains the AI/campaign lead and assignee of SO101-108/18.~~ *(Superseded by the amendment below.)* Hoan owns report writing (SO101-45), first-run/blocker matrix review (SO101-60) and rerun/evidence-freeze verification (SO101-62); Duc owns cross-profile conversion/calibration verification (SO101-59), matched-campaign acceptance (SO101-61) and technical report review (SO101-63).

## Amendment — deployment lead (25 October 2026)

Decision: Hoan is the deployment primary responder, as stated in the Team and Project Plan (Google Doc version 3.0, Tables 2, 10 and 15). Hoan is now assignee of the nine-profile epic SO101-108 and campaign-coordination task SO101-18. Duc is the deployment secondary responder (support) and remains AI lead for training and baselines.

Unchanged: the four/five profile split above (Hoan SO101-112–115; Duc SO101-116–120); Duc's verification/review gates SO101-59, SO101-61 and SO101-63; Hoan's SO101-45, SO101-60 and SO101-62; all dates, statuses, hierarchy and sprint memberships.

Rationale: align Jira with the submitted plan's deployment roles. Option rejected: moving all nine profile tasks to Hoan (higher November load on Hoan; would remove the split Hoan asked for earlier on 25 October).

Source: Hoan's chat instruction on 25 October 2026 ("Use option B"). Jira changes applied the same day: assignee of SO101-108 and SO101-18 changed from Duc to Hoan; a support comment was added to each (comment IDs 10003 and 10004). Read-back confirmed both assignees, both comments, unchanged To Do status and an unchanged 4/5 split. The issue descriptions still contain earlier "Primary assignee: Duc" wording; the comments record that it is superseded.

Verified by: pending Hoan's review.

## Consistency work

- Update current Jira model descriptions and training-reference dependencies without replacing any issue key or removing issue links.
- Align the baseline consolidation/reference-freeze/report/review working handoffs to **1 November**, when the two replacement model baselines are planned to finish. These are tracking dates derived from the user-authorized baseline window; they are not a claim of a university deadline extension.
- Preserve existing sprint memberships, priorities, issue hierarchy and all statuses except SO101-109's explicitly reported completion.
- No baseline completion is inferred for Pi0/X-VLA. Existing Done records for earlier model-selection/method decisions remain historical decisions; they do not establish executed compatibility or training for replacement models.
- Decision 0002 and assumptions A-001/A-002 retain their dated evidence for ACT/Diffusion Policy. Their architecture-specific runtime paths, quantized coverage and noise recipes do **not** automatically transfer to Pi0/X-VLA. Verify these in SO101-34 and the replacement baseline/profile tasks. Retain general evidence/reporting requirements and the approved compute placement unless changed by a later decision.
- Historical issue description content is retained in a clearly marked collapsed superseded-planning section; the new current scope/dates/ownership appear first.

## Schedule conflicts to retain visibly

The new comparison/report window ending 19 November supersedes the earlier 14 November working target in the affected Jira work. The **15 November Sprint 1 course package** and **6 December Project A final** deadlines are not moved. A package due 15 November cannot be described as containing final 19 November results; record available interim evidence/limitations and deliver the completed comparison by the revised target.

The previous 24 October full baseline-report target cannot represent a complete Pi0/X-VLA comparison when those baselines now end 1 November. Preserve the original target as history and record the current working handoff; do not claim an official extension.

## Source and verification

Source: Hoan's chat instruction on 25 October 2026. No external performance or model-compatibility research is asserted. Exact Pi0/X-VLA checkpoint revisions, recipes, runtime compatibility and measured precision coverage remain to be evidenced.

Verification: read back all affected Jira fields after edits, compare unchanged hierarchy/sprints/priorities and links, and confirm all 17 nine-profile items use 1–19 November. Save pre/post snapshots and an edit log.

