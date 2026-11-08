# 0008 — Final Project Plan choices: simulator, command form and report dates

Date: 2026-10-25 (Asia/Bangkok)
Status: Approved by Hoan in chat on 2026-10-25.
Decision owner: Hoan (PM).

## Decision

These choices are stated as confirmed in the Team and Project Plan (Google Doc, version 3.0, 25 October 2026; Appendix D.1) and are recorded here so the plan can cite a decision record.

1. **Simulator: MuJoCo.** MuJoCo replaces ManiSkill as the working simulator for the cube-to-box task. Decision 0001 (Proposed) and the ManiSkill working route remain historical rationale. The earlier simulator tasks marked Done (SO101-21, SO101-47, SO101-49) do not show that a MuJoCo scene works; the MuJoCo scene, SO-arm assets, cameras, reset and success detector still need their own evidence (SO101-100).
2. **Dataset:** `lerobot/svla_so100_pickplace` (unchanged). The exact revision and project splits still need to be pinned.
3. **Console command form: fixed form, no language-model request parser.** The operator selects the predefined request "Pick the cube and put it into the box". There is no free-text chat. This **supersedes decision 0005** (bounded chat interface). The fixed task text may still be passed to the VLA policy as an input. Backend validation of the submitted form remains required.
4. **Models and deployment roles:** SmolVLA, Pi0 and X-VLA (decision 0006). Hoan is deployment primary responder and Duc secondary (decision 0006 amendment).
5. **Conversion report dates (plan question D1, option a).** The nine-profile conversion report is completed on **18 November** and technically reviewed on **19 November**, following decisions 0006 and 0007 and Jira (SO101-45, SO101-63). The earlier 14 November date was an intentionally early internal target, not a university deadline; it is shown as superseded. The 15 November Sprint 1 course package carries interim comparison evidence and limitations only.
6. **Trieu's role (plan question D2, option a).** The plan keeps Trieu's software role (requirements, backend functions, logging and console integration). Matching Jira work: on Hoan's approval (25 October 2026), SO101-56 (minimal experiment runner and result logger, due 30 October) was reassigned from Khanh to Trieu, with Khanh reviewing as software lead (Jira comment 10005). Dates and status are unchanged.

## Rationale

Align the submitted plan, the decision log and Jira. Source: the plan's D.1 statement and Hoan's chat answers on 2026-10-25 (D1: a, D2: a, D3: a). No external technical claim is made by this record; MuJoCo suitability for the SO-arm task is still an open evidence item.

## Alternatives rejected

- D1 (b): return to 14 November, which would move SO101-45, 62, 63 and the profile tasks earlier.
- D2 (b): narrow Trieu's role in the plan to match Jira, leaving no scheduled work.
- D3 (b): leave the local records describing ManiSkill and a bounded chat interface.

## Verified by

Pending Hoan's review.
