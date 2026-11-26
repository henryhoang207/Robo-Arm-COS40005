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

## Run the X-VLA web demo

The demo is a web page where you type a request, such as "put the bowl on the stove", and watch a simulated robot arm do it. The model is X-VLA (LIBERO, W8A16), and it runs on the VENTUNO Q board's NPU. The LIBERO simulation runs on the laptop. The page shows both cameras, the Franka Panda's joints, the board's timing and whether the request succeeded.

```text
Browser ──▶ Web backend (robo-arm-app-main, :8001) ──▶ Demo bridge (demo_bridge, :8002) ──▶ VENTUNO Q board (:8766)
            LIBERO mode                                  runs the LIBERO simulation          X-VLA on the NPU
```

Details: [`demo_bridge/README.md`](demo_bridge/README.md) (bridge API, what to expect) and the "X-VLA LIBERO" section of [`robo-arm-app-main/backend/README.md`](robo-arm-app-main/backend/README.md).

### One-time setup (demo laptop: Windows with WSL2 Ubuntu)

1. **Board.** The **X-VLA LIBERO NPU** app (`user:xvla-libero-npu`) is installed in Arduino App Lab on the board. Its package (913 MB, models included) is kept outside this repo.
2. **Clone this repo inside WSL**, on the Linux filesystem rather than `/mnt/c`, because the backend's SQLite database needs it:

   ```bash
   git clone https://github.com/henryhoang207/Robo-Arm-COS40005.git ~/Robo-Arm-COS40005
   ```

3. **Python environment for the bridge**, `~/libero`: LeRobot 0.6.1 with LIBERO (see LeRobot's LIBERO install guide), plus the web server:

   ```bash
   ~/libero/bin/pip install fastapi==0.165.0 "uvicorn[standard]==0.54.0"
   ```

4. **Python environment for the web backend:**

   ```bash
   python3 -m venv ~/.venvs/robo-be
   ~/.venvs/robo-be/bin/pip install -r ~/Robo-Arm-COS40005/robo-arm-app-main/backend/requirements.txt
   ```

5. **Build the web page** on Windows (Node 20 or later; WSL has no Node), in a checkout of `main`, for example `C:\RobotArm`:

   ```powershell
   cd C:\RobotArm\robo-arm-app-main
   npm ci
   npm run build
   ```

   Rebuild after pulling frontend changes.

### Every demo

1. **Start the board app.** In App Lab, start **X-VLA LIBERO NPU**. Then check that it answers; this should show `"mode": "full-onboard-stage1+stage2"`:

   ```bash
   curl http://10.1.0.119:8080/api/status
   ```

   The board's IP address has changed before; if it has, use the new one in step 2.

2. **WSL terminal 1: the bridge.** Wait until the log shows `scene libero_goal/8 ready`. That takes 1 to 2 minutes, because the bridge prepares the demo scene before the first request.

   ```bash
   cd ~/Robo-Arm-COS40005 && git pull
   MUJOCO_GL=egl GALLIUM_DRIVER=d3d12 ~/libero/bin/python -m demo_bridge.app --board-host 10.1.0.119
   ```

3. **WSL terminal 2: the web backend** in LIBERO mode. Use `libero.env.example` as it is: its timings let runs ride out the bridge's 1–3 s pause after each run. The last line points at the page built in setup step 5.

   ```bash
   cd ~/Robo-Arm-COS40005/robo-arm-app-main/backend
   cp libero.env.example .env
   echo "SO101_FE_DIST_DIR=/mnt/c/RobotArm/robo-arm-app-main/dist" >> .env
   ~/.venvs/robo-be/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 1 --timeout-graceful-shutdown 3
   ```

4. **Open `http://localhost:8001`** in Chrome or Edge. The page opens in Vietnamese; **EN** at the top right switches to English. You should see a prompt box, both cameras showing the table, and the Franka Panda joint table.

### Running it

1. In **AI profile**, choose **X-VLA (LIBERO) · W8A16**.
2. Type a request, or pick one from the suggestions. The line under the box shows what will be checked, for example "Will check: put the bowl on the stove".
3. Press **Send command**. The arm moves in bursts: 30 steps, then a pause of about 0.5–1 s while the board computes the next 30. A run takes about 15–60 s.
4. **STOP** halts the run at once; press **Ready** before the next request.

Which requests to use (recorded 26 Nov 2026, one try each; [`demo_bridge/recordings/2026-11-26`](demo_bridge/recordings/2026-11-26/README.md)):

| Use for the demo (10/10 succeeded) | Experimental (0/3 succeeded) |
| --- | --- |
| put the bowl on the plate · put the bowl on the stove · turn on the stove · open the middle drawer of the cabinet · put the wine bottle on the rack · put the wine bottle on top of the cabinet · put the cream cheese in the bowl · push the plate to the front of the stove · put the bowl on top of the cabinet · open the top drawer and put the bowl inside | New combinations, such as "put the cream cheese on the plate": the arm usually carries the object over but doesn't let go, and the run fails after about 2 minutes. Requests the bridge can't parse run unscored until you press STOP |

### If something goes wrong

| What you see | What to do |
| --- | --- |
| A board warning in the status bar, or a banner saying the board lost its link | The App Lab app has stopped; it stopped by itself several times on 26 Nov. Restart it in App Lab. If the board's IP changed, restart the bridge with `--board-host <new IP>` |
| The page shows the SO-101 command form instead of the prompt box | The backend was not up yet. The page retries every 2 s; if it doesn't switch, reload |
| A run ends with `sim_offline` or `telemetry_stale` | The backend is not using `libero.env.example`'s timings. Copy it to `.env` again and restart the backend |
| The cameras say "No picture yet" | The bridge has not finished preparing the scene. Wait for `scene libero_goal/8 ready` |
| "address already in use" on 8001 or 8002 | An old backend or bridge is still running: `pkill -f "uvicorn app.main:app"` or `pkill -f demo_bridge.app` |

To stop: Ctrl+C in both WSL terminals. The board app can stay running.

## Start here

| Guide | Purpose |
| --- | --- |
| [Run the X-VLA web demo](#run-the-x-vla-web-demo) | Step-by-step demo runbook: board, bridge, web backend, page |
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
