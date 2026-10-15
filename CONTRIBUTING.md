# Contributing

## Before starting

1. Find or create the work item and record its Jira issue ID when assigned.
2. Confirm the intended outcome, owner and acceptance checks.
3. Use the [folder guide](FOLDER_GUIDE.md) to choose a location.
4. Identify changes to shared AI/IoT/app interfaces before implementation.

Jira project key and repository roles: **[TBD TEAM]**. Do not invent issue IDs; mark an unassigned link as TBD.

## Branches and commits

- Branch: `<JIRA-ID>-short-description` once the issue ID exists.
- Commit: `<JIRA-ID>: describe the change`.
- Keep each change focused and preserve unrelated work.

## Pull requests

Use the [PR template](.github/pull_request_template.md). Describe the problem, resulting behavior, validation performed and remaining limits. Link the issue and evidence. Request review from the responsible component owner.

Record what was actually tested: mock, computer reference, board, simulation or physical arm. Do not infer physical success from a mock or simulation test.

## Completion

A work item is complete when its agreed checks have evidence, the relevant documentation is updated and the reviewer accepts the result. Record failures and outstanding checks explicitly.

AI-assisted work needs a concise note in `ai-usage/` or the PR, with a reference to the official Drive log when available. See [EVIDENCE_POLICY.md](EVIDENCE_POLICY.md).

## Shared changes

Review command formats, units/ranges, feedback, timeouts, manual/AI priority and stop/reset behavior with the affected teams. Update the interface document and its version when the agreement changes.
