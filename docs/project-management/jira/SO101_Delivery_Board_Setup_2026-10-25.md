# SO101 delivery board setup — prepared 25 October 2026

Status: Prepared; no Jira board, filter, space or sprint changes have been made. Awaiting the board-location choice.

## Verified site constraints

The SO101 space is team-managed (style next-gen) and already owns native board 2, named SO101 board. Its existing columns are To Do, In Progress, In Review and Done. The createJiraBoard connector operation cannot create a second board inside a team-managed space and requires a company-managed project location. The site's only visible spaces are SO101 and My discovery project; neither is a suitable company-managed software location.

The native SO101 board currently displays “Plan and start a sprint to see work items here.” No sprint has been started, ended or reassigned by this task.

## Choice 1 — configure the existing board

- Retain the existing board URL and the four current workflow columns.
- Add delivery filters for Project A, Hoan, Duc, comparison, review, overdue work and governance.
- Group by assignee for daily coordination; use the epic grouping for outcome review.
- Show useful card fields such as assignee, due date, epic/parent and priority where supported.
- Retain existing course-sprint membership and states. Configuring filters alone will not populate the active board while no sprint is active. Starting a course sprint or changing sprint mode needs an explicit choice rather than being assumed.
- Keep provisional Project B work accessible through a separate filter/backlog view.

## Choice 2 — separate delivery board in a new company-managed space

Only create the new location if Hoan selects this option. Do not create a new space automatically.

- Proposed space name: SO101 Delivery.
- Proposed board name: SO101 Project A Delivery.
- Board type: Kanban, showing the existing SO101 issues through a saved filter.
- Proposed board filter: project = SO101 AND labels = project-a AND issuetype != Epic ORDER BY Rank ASC.
- The new location hosts the board; issues remain in SO101. No issues are copied/moved, no sprint memberships change and no current sprint is started.
- Map the existing To Do, In Progress, In Review and Done statuses to four columns.
- Add the filters and grouping below where supported.
- Preserve existing access boundaries. Do not make the board public or grant broader project/site access.

## Proposed filters

| Filter | Query clause |
|---|---|
| Project A | labels = project-a |
| My work | assignee = currentUser() |
| Hoan | assignee = "712020:45dd4796-359d-42de-8c27-f89e6449dec0" |
| Duc | assignee = "712020:c4d9a4d2-796d-44e4-a27d-3bf94e3373d2" |
| Nine-profile comparison | parent = SO101-108 OR parent = SO101-18 |
| Needs review | status = "In Review" |
| Overdue | duedate < startOfDay() AND statusCategory != Done |
| Governance | labels = governance |
| AI | labels = ai |
| IoT | labels = iot |
| SoftDev | labels in (softdev, web) |
| Integration | labels = integration |
| Project B (existing board/backlog) | labels = project-b |

These are proposed clauses for a board-scoped query. Validate each against Jira before saving. The separate Project A board's base filter excludes Project B, so a Project B filter belongs on the original project/backlog view rather than that board.

## Verification after the selected setup is authorized

Read back the board configuration; check column/status mapping, saved filters and actual visible issue coverage; verify SO101 issue identities, ownership, dates, statuses and sprint membership remain intact; capture the result and provide the board link.

No implementation has been executed. The user has been asked to choose configuring the existing board or creating a new company-managed location and separate board.

