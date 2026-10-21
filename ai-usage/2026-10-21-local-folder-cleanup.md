# Local folder cleanup — 21 October 2026

- Jira issue: [TBD TEAM issue ID]; no issue assigned for this housekeeping task.
- Tool and date: Claude (claude.ai session linked to Hoan's computer), 21 October 2026.
- User request: identify files in the outer COS40005 workspace that can be retired or deleted, then carry out the approved plan.
- Human approval: Hoan approved the plan in chat: delete regenerable renders and duplicate copies, move unique history into this repository, and keep the build scripts in `tmp/` until the 25 October submission.

## Moved into the repository

SHA-256 was checked after each move.

| From (outer workspace) | To | SHA-256 prefix |
| --- | --- | --- |
| `tmp/master-plan-2026-10-20/jira-current.json` | [`jira/snapshots/2026-10-20.json`](../docs/project-management/jira/snapshots/2026-10-20.json) | `77d19af9f12a` |
| `tmp/scope-change-2026-10-21/jira-before.json` | [`jira/snapshots/2026-10-21-before-scope-change.json`](../docs/project-management/jira/snapshots/2026-10-21-before-scope-change.json) | `551ca513b10c` |
| `tmp/scope-change-2026-10-21/jira-changes.json` | [`jira/snapshots/2026-10-21-scope-change-edits.json`](../docs/project-management/jira/snapshots/2026-10-21-scope-change-edits.json) | `02502c3e211e` |
| `tmp/scope-change-2026-10-21/master-before.docx` | [`planning-before-2026-10-21/master-plan-v1-2026-10-20.docx`](../docs/technical/source-archives/planning-before-2026-10-21/master-plan-v1-2026-10-20.docx) | `333d22080d2d` |

The pre-change capture is the task-local "before" snapshot mentioned in the [21 October scope note](2026-10-21-scope-and-iot-ownership-update.md); it holds the last recorded description of the deleted SO101-64.

The outer copy of `SO101-22_Benchmark_Condensed_Report_2026-10-14.docx` replaced the copy in `docs/technical/reports/`. Both had identical words; the outer copy had newer heading and table formatting. The earlier version remains in Git history (commit 02c9c0c).

The Jira records index and the planning-archive README list the new files.

## Deleted from the outer workspace

316 files (34.45 MB) and 20 emptied folders:

- Page renders, contact sheets and PDF renders in `tmp/master-plan-2026-10-20/render-v1` to `render-v3` and `template-render`, `tmp/scope-change-2026-10-21/render-*`, `tmp/pdfs/`, and `.so101_report_2026-10-14/` (page images, text dump, test document and QA count file).
- The build output `tmp/master-plan-2026-10-20/authored.docx` and four JSON text extracts of documents archived in this repository.
- Byte-identical copies of repository files: the outer course template and plan companions, `robot_model_review/main2.pdf`, the outer `docs/` reports, calculation script and decision 0004, experiment 001 data, results and environment pins, and the 14 October report PDF and Jira snapshot.
- Pre-reorganisation copies that differed only in file paths: outer decisions 0001 to 0003, the assumption register, experiment 001 and 002 READMEs and scripts, and the outer timeline version 3.
- The empty `Edge Deployment` folder.

## Kept

- The 24 build-kit files in `tmp/master-plan-2026-10-20/`, `tmp/scope-change-2026-10-21/` and `.so101_report_2026-10-14/`, until the 25 October submission. `build_master.py` regenerates the master plan from code and would overwrite edits made directly in Word.
- The outer `CLAUDE.md` and everything in this repository.

## Checks performed

- SHA-256 comparison of every outer-workspace file against this repository before deletion.
- Line diffs confirming that the path-only variants differed only in file paths or blank lines.
- SHA-256 check of each moved file, a post-cleanup listing and `git status`.

## Limits

Deletions from the local folder are permanent; they bypass the Recycle Bin. No decision, plan content, research result or measurement was changed. The plan was approved in chat; the outcome has not been independently reviewed.

Official Drive AI Usage Log reference: [TBD TEAM official log link].
