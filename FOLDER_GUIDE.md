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
- Keep the report copies uploaded to this repository in `docs/technical/reports/`, and plan/schedule copies in `docs/project-management/plans/`. Drive remains the formal-report location; these copies do not establish which version was submitted.
- Keep large recordings, datasets and model weights in agreed external storage; record their location and version in `data/`.

## Naming

Use short descriptive names, such as `command-interface.md`, `conversion-comparison.md` or `experiment-001.md`. Include a Jira issue ID when one has been assigned. Keep unknown decisions as `[TBD TEAM ...]`, research gaps as `[TBD LIT ...]`, and unmeasured results as `[TBD TEST ...]`.

## Current subfolders

| Location | Current contents |
| --- | --- |
| `docs/technical/decisions/` and `docs/technical/assumptions.md` | Numbered technical decisions and assumption register |
| `docs/technical/requirements/` | SoftDev acceptance criteria, scope and constraints |
| `docs/technical/source-archives/` | Original AI, IoT and SoftDev document ZIP archives |
| `docs/project-management/jira/` | Backlog exports, delivery notes, timeline and dated source snapshots |
| `docs/project-management/templates/` | Supplied course report and team-plan templates |
| `docs/project-management/reproduce-arm/` | Earlier reproduction roadmap and risk register |
| `research/literature/references/` | Reference PDFs and robot model review |
| `research/methodology/calcs/` | Supporting parameter calculations |
| `research/methodology/reproduce-arm/` | Earlier reproduction procedures and evaluation protocol |
| `research/experiments/001-dataset-sim-joint-convention-check/` | Experiment plan, input samples, environment pins and FK scripts |
| `research/results/001-dataset-sim-joint-convention-check/` | Recorded FK CSV outputs |
| `research/experiments/reproduce-arm/` | Exploratory dataset review and profiling scripts |
| `research/results/stageC-laptop-cpu/` | Recorded laptop CPU profiling measurements |
| `tests/simulation/` | Standalone MuJoCo smoke-test scene |

`SO-ARM100-main/` is an imported source bundle and keeps its internal layout, licence and attribution files. Do not split its documentation from its mesh and model assets during routine document filing. Root guides and `CLAUDE.md` remain at the repository root.
