# Master plan readability revision — 22 October 2026

## Human direction

Hoan asked for the readability issues an external reviewer would meet in the master plan, chose which fixes to apply, and asked that the chat-interface scope change be recorded as decision 0005. Hoan asked for the review comments to be kept because they still need resolving, and for the header and footer to be removed.

## Assistant work

- Tool/model and date: Claude (Claude Code desktop), 22 October 2026.
- Added a contents page and a front-matter table of abbreviations, labels and identifiers. The table includes a Jira cross-reference of the 89 SO101 work items cited in the plan, with titles, owners and statuses from the 21 October 2026 Jira snapshot.
- Renamed risks R1–R8 to K1–K8. Renumbered references [1]–[11] in order of first citation; [11] (COS40005 unit page) is not cited in the body.
- Wrote SO101- prefixes on bare Jira numbers outside Table 13; Table 13 keeps bare numbers with an explanatory note.
- Replaced "user-confirmed" with "confirmed by Hoan (PM) on 12 October 2026", sourced from the version 3 timeline. Removed the references to unseen earlier documents.
- Moved the Jira-versus-decision discrepancies into one "Status discrepancies at 21 October 2026" box in Appendix A (Section A.2) and replaced the scattered copies with pointers.
- Removed the header (including its "Internal" marking) and footer. As a consequence, page numbers no longer show on pages, and the section no longer starts numbering at 0.
- Set Heading 1 for front matter, Parts and appendices and Heading 2 for numbered sections, all in sentence case. Removed the partial automatic list numbering that headings carried, added an Objectives heading and removed the Navigation paragraph.
- Captioned Tables 1–20 and referred to each table in the running text.
- Recorded decision 0005, added a supersession note to decision 0003, and updated both CLAUDE.md files and the planning indices.
- No Jira, Drive or Google Doc change was made.

## Checks performed

- A scripted comparison of the original and revised text found changes only where intended.
- All 50 review comments are present with unchanged text. Each comment is anchored to the same passage; seven anchored passages carry the intended edits (caption colon, risk IDs, SO101 prefix).
- External hyperlinks are unchanged, and highlighted text is kept.
- Word opened, rebuilt the table of contents, saved and exported the file. All 36 rendered pages were produced, and key pages were visually checked.

## Human review still required

- Hoan to confirm decision 0005's wording, including the completed sentence "and, if so, where it runs".
- Hoan to check the definitions of standard abbreviations, which were written from general knowledge.
- Hoan to decide whether the plan needs a page-number footer.
- The Nguyen acknowledgment named in Appendix C is still absent from the plan.

## Evidence

- [Revised master plan](../docs/project-management/plans/SO101%20Master%20Team%20and%20Project%20Plan%20%282026-10-22%29.docx)
- [Decision 0005](../docs/technical/decisions/0005-console-bounded-chat-interface.md)
- [21 October Jira snapshot](../docs/project-management/jira/snapshots/2026-10-21.json)
