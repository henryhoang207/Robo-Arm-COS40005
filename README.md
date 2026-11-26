# Robo-Arm_sedoitensau

AI robotics project for COS40005: investigate running a trained robot model on VENTUNO Q, first with simulation and later with a physical SO-101.

**GitHub is the technical source of truth.** Code, tests, research execution, evidence indexes and handover live here. Google Drive holds the formal reports and official AI Usage Log; the uploaded report copies are filed below for repository access.

Repository structure: **SCAF GitHub Repository Template v1.1**, adapted for this project.

## Current project direction

- **Duration:** eight months across two semesters; actual teaching dates remain to be agreed.
- **Semester 1:** obtain a suitable trained model, convert/run it on the board, and exchange observations/actions with a simulator on a computer. Build the mobile app in parallel, starting with mock responses.
- **Semester 2:** integrate and evaluate the physical SO-101 and app when the arm is available.
- **Team boundary:** AI owns the model and vision; IoT owns embedded control; SoftDev owns the mobile interface and app-side AI/IoT integration.
- **Open decisions:** checkpoint, simulator, task, shared interface, target mobile device/OS, transport and acceptance thresholds.

These are planned outcomes, not claims that deployment or physical task success has been demonstrated.

## Start here

| Guide | Purpose |
| --- | --- |
| [Folder guide](FOLDER_GUIDE.md) | Where each kind of work belongs |
| [Google Drive index](GOOGLE_DRIVE_INDEX.md) | Formal plans, reports and official logs |
| [Contributing](CONTRIBUTING.md) | Issues, branches, pull requests and review |
| [Evidence policy](EVIDENCE_POLICY.md) | How to record and link evidence |
| [GitHub setup checklist](GITHUB_SETUP_CHECKLIST.md) | Repository settings to configure |
| [Handover](handover/README.md) | Setup, deployment, issues and future work |
| [Project plans and Jira records](docs/project-management/README.md) | Uploaded plans, schedules, templates and backlog exports |
| [Technical records](docs/technical/README.md) | Requirements, decisions, assumptions and condensed reports |
| [Experiments](research/experiments/README.md) and [results](research/results/README.md) | Runnable research and recorded measurements |
| [Literature](research/literature/README.md) | References and earlier source notes |

## Repository layout

```text
Robo-Arm_sedoitensau/
├── README.md
├── FOLDER_GUIDE.md
├── GOOGLE_DRIVE_INDEX.md
├── CONTRIBUTING.md
├── EVIDENCE_POLICY.md
├── GITHUB_SETUP_CHECKLIST.md
├── CLAUDE.md
├── .gitignore
├── .github/
│   ├── ISSUE_TEMPLATE/
│   ├── pull_request_template.md
│   └── workflows/
├── src/
├── tests/
├── research/
│   ├── literature/
│   ├── methodology/
│   ├── experiments/
│   └── results/
├── docs/
│   ├── technical/
│   │   ├── decisions/
│   │   ├── reports/
│   │   ├── requirements/
│   │   └── source-archives/
│   └── project-management/
│       ├── jira/
│       ├── plans/
│       ├── reproduce-arm/
│       └── templates/
├── evidence/
│   ├── product/
│   ├── research/
│   ├── process/
│   └── individual/
├── data/
├── handover/
└── SO-ARM100-main/       # imported source bundle; internal layout preserved
```

Folder READMEs link to the current records and retain templates for future work. The imported SO-ARM100 bundle stays together so its model, mesh and documentation paths remain valid.

## Folder purposes

| Folder | Use |
| --- | --- |
| [src](src/README.md) and [tests](tests/README.md) | Implementation, testing and validation code |
| [research](research/methodology/README.md) | Literature, methods, experiments, notebooks and results |
| [docs/technical](docs/technical/README.md) | Requirements, architecture, interfaces and technical decisions |
| [docs/project-management](docs/project-management/README.md) | Working plans, decisions, risks and actions |
| [evidence](EVIDENCE_POLICY.md) | Product, research, process and individual evidence indexes |
| [data](data/README.md) | Data and model descriptions, versions and external storage links |
| [handover](handover/README.md) | Setup, deployment, known issues and future work |

## Using the template

1. Add the missing document links and owners in [the Google Drive index](GOOGLE_DRIVE_INDEX.md).
2. Follow [the GitHub setup checklist](GITHUB_SETUP_CHECKLIST.md) to agree access, review rules and repository settings.
3. Start work with a [task](.github/ISSUE_TEMPLATE/task.yml), [bug report](.github/ISSUE_TEMPLATE/bug_report.yml) or [research experiment](.github/ISSUE_TEMPLATE/research_experiment.yml). Link the assigned Jira issue when available.
4. Add code, tests or research records in the appropriate folder and link the resulting evidence from its evidence index.
5. Submit changes using [the pull request template](.github/pull_request_template.md), recording the checks actually performed and any AI assistance.
6. Update the handover guides with verified instructions as the project becomes runnable.

Starter entries marked TBD need team input or measured results. Replace them when the supporting information is available.

## Existing work

[Reproduce Arm](research/methodology/reproduce-arm/README.md) indexes the earlier methodology, [exploratory scripts](research/experiments/reproduce-arm/README.md), [CPU profiling results](research/results/stageC-laptop-cpu/README.md), and planning notes. Consult the current project plan before using its earlier schedule or scope assumptions. The [imported SO-ARM100 source](SO-ARM100-main/README.md) contains the mechanical and simulation resources; the standalone [MuJoCo smoke-test scene](tests/simulation/basic_test.xml) is under tests.

## Traceability

Jira issue → commit/PR with issue ID → evidence → Drive report → individual IC-SR reflection using STAR.

**Setup status:** the folder scaffold and issue/PR templates are present. Build tooling, automated workflows and GitHub repository settings still need team decisions.
