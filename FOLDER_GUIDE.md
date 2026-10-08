# Folder guide

This structure follows the supplied SCAF GitHub Repository Template v1.1.

| Location | What belongs here |
| --- | --- |
| `src/` | Implementation code for the agreed AI, IoT/control, simulation and app components |
| `tests/` | Implementation tests, integration checks and validation procedures |
| `research/literature/` | Source notes, citations, related work and research gaps |
| `research/methodology/` | Methods, evaluation protocols and agreed test conditions |
| `research/experiments/` | Experiment plans, notebooks and reproducible execution records |
| `research/results/` | Measured results, analysis and limitations |
| `docs/technical/` | Requirements, architecture, interfaces and technical decisions |
| `docs/project-management/` | Working decisions, risks, dependencies and meeting/action notes |
| `evidence/product/` | Index of implementation and demonstration evidence |
| `evidence/research/` | Index of research and evaluation evidence |
| `evidence/process/` | Index of planning, review and collaboration evidence |
| `evidence/individual/` | Index of each member's contribution evidence |
| `ai-usage/` | AI assistance notes linked to code and PRs |
| `data/` | Dataset descriptions, schemas, versions, licences and storage pointers |
| `handover/` | Setup, deployment, known issues and future work |
| `.github/ISSUE_TEMPLATE/` | GitHub issue forms |
| `.github/workflows/` | Automated checks once the stack and commands are agreed |

## Choosing a location

- Put an experiment's runnable materials in `research/experiments/`; put its outcome in `research/results/`.
- Put tests that check implementation behavior in `tests/`.
- Put the explanation of an interface in `docs/technical/`; its implementation belongs in `src/`.
- Evidence folders index the original artifact using a path, commit, PR or Drive link. Avoid duplicating the same artifact in several folders.
- Store formal reports in Drive and add their links to [GOOGLE_DRIVE_INDEX.md](GOOGLE_DRIVE_INDEX.md).
- Keep large recordings, datasets and model weights in agreed external storage; record their location and version in `data/`.

## Naming

Use short descriptive names, such as `command-interface.md`, `conversion-comparison.md` or `experiment-001.md`. Include a Jira issue ID when one has been assigned. Keep unknown decisions as `[TBD TEAM ...]`, research gaps as `[TBD LIT ...]`, and unmeasured results as `[TBD TEST ...]`.
