# 0005 — Bounded chat interface for the experiment console

Date: 2026-10-21 (Asia/Bangkok; scope change as stated in the master plan, version 2)
Recorded: 2026-10-22, on Hoan's instruction in chat.
Status: Superseded by [0008](0008-final-plan-choices-and-report-dates.md) on 2026-10-25 — the console uses a fixed command form with no language-model request parser. Originally: Approved by Hoan (scope inclusion only). The interface details listed under "Open values" are not decided.
Decision owner: Hoan (PM).

## Decision

The Project A experiment console includes a bounded chat interface. Operators can request console actions in typed free text instead of only through the closed command set (create run, start, abort, export).

This partially supersedes decision 0003, which placed free-text commands outside the current core. The amendment applies to the console's chat interface only. Speech commands, multiple object classes, MQTT, OTA update/rollback and Cartesian controls remain outside the current core. The retired F06 parser targets (text parser 196/200, reject 50/50) are not revived; no acceptance threshold is set by this decision.

Decision 0003's console rules stay in force until the open values below are settled: parameters are validated against frozen catalogues, invalid input is rejected with a reason and logged, nothing starts on a rejected request, and abort remains available.

## Open values (not decided by this record)

1. Which requests the chat accepts, and whether each maps onto the four existing console commands or extends the command set (master-plan review comment on the Scope section's closed-command-set paragraph; Khanh with Hoan).
2. How unsupported or ambiguous requests are answered.
3. Whether a language model interprets the text and, if so, where it runs and how its output is validated before any console action. The master plan's own sentence on this point was unfinished; the wording here is the recording assistant's completion and must be confirmed by Hoan.
4. Acceptance tests for valid, ambiguous and out-of-bounds chat requests, and the corresponding change to requirement F5 (master-plan review comments on requirement F5 in the requirements table).
5. Chat-interface skills and support in the KOST analysis, and hosting (review comments on the solution-components and KOST tables).

## Rationale

Hoan made this scope change on 21 October 2026 and recorded it in the master plan's Scope section; on 22 October 2026 Hoan instructed that it be recorded as decision 0005. Review comments in the master plan (Scope section, investigation table and completion-items table) flag that the change conflicts with decision 0003 until recorded. No literature or experimental evidence is claimed for this choice; it is a scope preference of the decision owner.

## Alternatives rejected

- Keep decision 0003 unchanged and remove the chat text from the master plan (closed command set only).

## Jira disposition

The 21 October 2026 Jira snapshot contains no item that records the chat interface. Which items to update (for example SO101-42 console workflow, SO101-99 console workflow approval, SO101-5/SO101-6 interface and frontend, SO101-8 backend) is Hoan's decision; no Jira change was made.

Verified by: Not applicable to a scope decision. Hoan to confirm this record, including open value 3's wording.
