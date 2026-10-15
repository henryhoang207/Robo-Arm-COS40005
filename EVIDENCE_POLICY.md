# Evidence policy

Evidence should let another person understand what was done, which version was used and what the result establishes.

## Minimum record

| Field | Record |
| --- | --- |
| Work item | Jira issue or [TBD TEAM issue ID] |
| Claim or question | What the artifact supports |
| Artifact | Repository path, commit/PR or authorised Drive link |
| Setup | Hardware/software/model/data versions and relevant conditions |
| Method | Steps, inputs, number of attempts and agreed checks |
| Result | Actual observations, including failures and exclusions |
| Limits | What remains untested or uncertain |
| Contributor/reviewer | Who produced and checked it |

## Evidence categories

- **Product:** implementation, tests, integration and demonstrations.
- **Research:** literature synthesis, methods, experiments and measured results.
- **Process:** decisions, planning, issue tracking, reviews and coordination.
- **Individual:** attributable contributions and links used for IC-SR reflections.

Use the README in the relevant `evidence/` folder as its index. Link to the original artifact rather than duplicating it.

## Project-specific rules

- Label mock, computer, board, simulation and physical-arm evidence separately.
- Distinguish a command sent, accepted, completed and failed when feedback is available.
- An app stop request and the controller/arm actually stopping need separate evidence.
- Report all attempts and failures for a task trial; identify resets and manual interventions.
- Record preprocessing, action mapping, checkpoint and conversion settings for model comparisons.
- App command logs are not automatically aligned robot-training demonstrations.
- Keep agreed thresholds as TBD until the team sets them; never replace missing measurements with expected results.

## Storage and reporting

Keep source code and small reviewed artifacts in Git. Store large recordings, model weights, datasets and formal reports in agreed external storage. Include version identifiers or checksums where useful for reproducing a result.

The official AI Usage Log and formal reports remain in Drive. Technical AI assistance notes and evidence indexes live here.

The user-requested repository copies of plans and reports are filed under `docs/project-management/plans/` and `docs/technical/reports/`. Their presence is an archive copy, not evidence of formal submission or technical validation.
