# SO101 Robotics delivery backlog

Created and verified on 8 October 2026. [Open Jira backlog](https://huu-hoan-hoang.atlassian.net/jira/software/projects/ROBO/boards/1/backlog). [Open Timeline](https://huu-hoan-hoang.atlassian.net/jira/software/projects/ROBO/boards/1/timeline).

7 epics and 31 tasks (ROBO-1 through ROBO-38), with real parent epics. The original 28 task dependency links were verified; the three deadline tasks are calendar markers under ROBO-7. All work is To Do and unassigned. No sprint has been started.

Confirmed project start: 13 September 2026. Semester 2 starts 11 January 2027. Project Plan is due 25 October 2026; Sprint 1 review/submission is due 15 November; Sprint 2 review/submission is due 6 December. Phase and review windows are estimated; overall finish is estimated as 12 May 2027 from the eight-month duration. See [timeline and date assumptions](jira-timeline.md). Detailed task dates, named assignees, estimates and numeric acceptance targets remain TBD.

Semester 1: trained-model reuse, VENTUNO Q conversion, a live board/simulator observation-action loop, and mobile-app integration. Semester 2: SO-101 readiness, physical adaptation and evaluation, final trials and handover, subject to hardware availability.

This file is a reference snapshot; Jira holds current delivery status. The adjacent draft CSV was not imported and must not be imported into ROBO as a second copy.

Source: [Eight-month project plan](https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI).

## [ROBO-1](https://huu-hoan-hoang.atlassian.net/browse/ROBO-1): Plan, acceptance and shared interfaces

Goal
Agree one task, measurable acceptance criteria, scope boundaries, ownership and a versioned shared interface. Named assignees remain TBD until agreed.

Planning period: Months 1-8 (relative; detailed task dates TBD).
Owner role: PM with AI, IoT, SoftDev and supervisor; named assignee TBD.
Completion: linked tasks have the agreed evidence and reviewed limitations.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

Timeline planning basis (updated 8 October 2026)
Confirmed by PM: project started 13 September 2026; Semester 2 starts 11 January 2027. Confirmed submission/review deadlines: Project Plan 25 October 2026, Sprint 1 15 November 2026, Sprint 2 6 December 2026.
Estimated phase/review window: 09/13/2026 to 05/12/2027 (MM/DD/YYYY). Overall planning and interfaces.
The 12 May 2027 overall finish is derived from the eight-month duration and remains an estimated target. Phase boundaries are planning estimates, not confirmed assessment deadlines or effort estimates. Detailed task dates, owners, capacity and hardware arrival remain TBD. Hardware-dependent work must be reviewed when the SO-101 becomes available.

### [ROBO-8](https://huu-hoan-hoang.atlassian.net/browse/ROBO-8): Agree the task, scope and semester acceptance criteria

Parent: ROBO-1.

Purpose
Define the intended user, object, destination and user problem/value measure. Set required, conditional and deferred features. Agree what Semester 1 must demonstrate and the separate Semester 2 physical targets.

Planning period: Month 1 (relative; actual dates TBD).
Owner role: PM and supervisor; named assignee TBD.

Acceptance checks
1. Record the task and feature boundaries in a reviewed scope decision.
2. Agree conversion, runtime, simulation, physical task and app targets with test conditions and trial allocation; leave unresolved values visibly TBD.
3. Keep user value, simulation behavior and physical success as separate claims.

Dependencies: None.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

### [ROBO-9](https://huu-hoan-hoang.atlassian.net/browse/ROBO-9): Confirm owners, semester calendar and board/lab access

Parent: ROBO-1.

Purpose
Map the eight relative months to actual teaching weeks, breaks, assessments and hardware access. Confirm component responsibilities and named owners.

Planning period: Month 1 (relative; actual dates TBD).
Owner role: PM; named assignee TBD.

Acceptance checks
1. Record the semester boundaries and submission/review dates when confirmed.
2. Confirm VENTUNO Q access and the simulator host; link the arm procurement work item.
3. Record PM, AI, IoT/hardware, SoftDev, integration and supervisor owners; actual Jira assignees remain unassigned until confirmed.

Dependencies: None.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

### [ROBO-10](https://huu-hoan-hoang.atlassian.net/browse/ROBO-10): Agree the versioned AI/IoT/app command interface

Parent: ROBO-1.

Purpose
Agree the shared command and observation contracts before substantial integration.

Planning period: Month 1 (relative; actual dates TBD).
Owner role: AI, IoT, SoftDev and integration leads; named assignee TBD.

Acceptance checks
1. Document image/state/action fields, task inputs, units, ranges, preprocessing and action scaling.
2. Agree transport, statuses/errors, timestamps/timeouts, manual-versus-AI priority, stop/reset and access/security rules.
3. Define sent, accepted, completed and failed feedback; sending alone must not imply completion. Record unsupported feedback explicitly.

Dependencies: ROBO-8.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

### [ROBO-11](https://huu-hoan-hoang.atlassian.net/browse/ROBO-11): Record hardware-delay and integration fallback decisions

Parent: ROBO-1.

Purpose
Track late board/arm access, model/simulator mismatch, slow runtime and interface drift. Maintain decisions and evidence for the agreed fallback.

Planning period: Month 1; review monthly and in Month 4 (relative; actual dates TBD).
Owner role: PM and supervisor; named assignee TBD.

Acceptance checks
1. Record risk owners, dependencies and monthly hardware checkpoints.
2. If the board is delayed, retain a computer reference and mark board validation outstanding.
3. At the Semester 2 planning review, agree revised assessed scope if the arm is unavailable; preserve the distinction between simulation and physical evidence.

Dependencies: ROBO-9.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

## [ROBO-2](https://huu-hoan-hoang.atlassian.net/browse/ROBO-2): Trained model and VENTUNO Q deployment

Goal
Select a task-compatible trained checkpoint, establish a computer reference, convert/replay it on the board, and measure conversion differences and runtime limits. Acceleration remains optional until verified.

Planning period: Semester 1, Months 1-4 (relative; detailed task dates TBD).
Owner role: AI lead; named assignee TBD.
Completion: linked tasks have the agreed evidence and reviewed limitations.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

Timeline planning basis (updated 8 October 2026)
Confirmed by PM: project started 13 September 2026; Semester 2 starts 11 January 2027. Confirmed submission/review deadlines: Project Plan 25 October 2026, Sprint 1 15 November 2026, Sprint 2 6 December 2026.
Estimated phase/review window: 09/13/2026 to 01/10/2027 (MM/DD/YYYY). Semester 1 model and board deployment.
The 12 May 2027 overall finish is derived from the eight-month duration and remains an estimated target. Phase boundaries are planning estimates, not confirmed assessment deadlines or effort estimates. Detailed task dates, owners, capacity and hardware arrival remain TBD. Hardware-dependent work must be reviewed when the SO-101 becomes available.

### [ROBO-12](https://huu-hoan-hoang.atlassian.net/browse/ROBO-12): Review and select a compatible trained checkpoint

Parent: ROBO-2.

Purpose
Review existing task-trained checkpoints using primary model cards, papers and original repositories. SmolVLA and LeRobot are candidates, not a confirmed working controller.

Planning period: Month 1 (relative; actual dates TBD).
Owner role: AI lead; named assignee TBD.

Acceptance checks
1. Compare robot, camera/state/action conventions, task coverage and existing task evidence.
2. Record licence/reuse conditions, exact checkpoint/version and provider.
3. Close [TBD LIT compatible checkpoint task evidence and licence] or document the remaining gap; loading a base model is only a deployment check.

Dependencies: ROBO-8.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

### [ROBO-13](https://huu-hoan-hoang.atlassian.net/browse/ROBO-13): Establish the original-model computer reference

Parent: ROBO-2.

Purpose
Run the selected original model on saved inputs before conversion.

Planning period: Month 2 (relative; actual dates TBD).
Owner role: AI lead; named assignee TBD.

Acceptance checks
1. Version inputs, checkpoint, dependencies, preprocessing and controlled random settings.
2. Save every reference action field and restored action scaling.
3. Record a reproducible run and its limits without claiming board or physical success.

Dependencies: ROBO-12, ROBO-10.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

### [ROBO-14](https://huu-hoan-hoang.atlassian.net/browse/ROBO-14): Convert the checkpoint and replay inputs on VENTUNO Q

Parent: ROBO-2.

Purpose
Use a compatible existing conversion/runtime path where possible. Feed the board known images and arm state; save predicted actions.

Planning period: Month 2 (relative; actual dates TBD).
Owner role: AI lead; named assignee TBD.

Acceptance checks
1. Record conversion/runtime versions, settings and the board configuration.
2. Demonstrate model loading and repeat inference on the saved input set, or record the precise blocker and outputs.
3. Keep NPU/Hexagon acceleration optional until the selected board/runtime path is locally verified.

Dependencies: ROBO-13, ROBO-9.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

### [ROBO-15](https://huu-hoan-hoang.atlassian.net/browse/ROBO-15): Compare conversion outputs and measure board runtime

Parent: ROBO-2.

Purpose
Compare original and converted results on identical inputs, then profile board operation separately from simulation rendering.

Planning period: Months 2-4 (relative; actual dates TBD).
Owner role: AI lead; named assignee TBD.

Acceptance checks
1. Compare every action field against the agreed tolerance and preserve failures.
2. Measure loading/startup, steady prediction time, memory, errors and sustained run behavior.
3. Report versions, cases, number of runs and limits; [TBD TEAM board timing memory duration and action-difference targets].

Dependencies: ROBO-14, ROBO-8.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

## [ROBO-3](https://huu-hoan-hoang.atlassian.net/browse/ROBO-3): Board-to-simulation feedback loop

Goal
Select compatible robot/camera assets, verify action mapping, connect new simulated observations to the board, and record repeated task behavior. Replay alone does not prove closed-loop control or physical task success.

Planning period: Semester 1, Months 1-4 (relative; detailed task dates TBD).
Owner role: Simulation and integration lead; named assignee TBD.
Completion: linked tasks have the agreed evidence and reviewed limitations.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

Timeline planning basis (updated 8 October 2026)
Confirmed by PM: project started 13 September 2026; Semester 2 starts 11 January 2027. Confirmed submission/review deadlines: Project Plan 25 October 2026, Sprint 1 15 November 2026, Sprint 2 6 December 2026.
Estimated phase/review window: 09/13/2026 to 01/10/2027 (MM/DD/YYYY). Semester 1 board-to-simulation loop.
The 12 May 2027 overall finish is derived from the eight-month duration and remains an estimated target. Phase boundaries are planning estimates, not confirmed assessment deadlines or effort estimates. Detailed task dates, owners, capacity and hardware arrival remain TBD. Hardware-dependent work must be reviewed when the SO-101 becomes available.

### [ROBO-16](https://huu-hoan-hoang.atlassian.net/browse/ROBO-16): Review and select simulator, SO-101 assets and cameras

Parent: ROBO-3.

Purpose
Select the checkpoint and simulator together, using existing simulation tooling and compatible robot assets where available.

Planning period: Month 1 (relative; actual dates TBD).
Owner role: Simulation and integration lead; named assignee TBD.

Acceptance checks
1. Document robot joints/gripper, camera views, state fields and control support.
2. Justify compatibility or the adaptation required for the selected checkpoint.
3. Close [TBD LIT simulator robot assets cameras and control support]; confirm the simulator host and board connection.

Dependencies: ROBO-8, ROBO-12.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

### [ROBO-17](https://huu-hoan-hoang.atlassian.net/browse/ROBO-17): Verify action mapping with known virtual-arm commands

Parent: ROBO-3.

Purpose
Test mapping before claiming that model predictions control the virtual arm.

Planning period: Months 2-3 (relative; actual dates TBD).
Owner role: Simulation and integration lead; named assignee TBD.

Acceptance checks
1. Verify fields, units, direction, joint/gripper ranges and limits using known actions.
2. Restore model action scaling before translation; record mapping checks and failures.
3. Only then send board predictions through the verified mapping.

Dependencies: ROBO-16, ROBO-10.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

### [ROBO-18](https://huu-hoan-hoang.atlassian.net/browse/ROBO-18): Connect the live board/simulator observation-action loop

Parent: ROBO-3.

Purpose
Send rendered images and current state to the board, execute predicted actions in simulation, and send the next observations after movement.

Planning period: Month 3 (relative; actual dates TBD).
Owner role: Simulation and integration lead; named assignee TBD.

Acceptance checks
1. Demonstrate repeated observation-prediction-execution feedback, or document a blocker with results.
2. Test resets, timestamps, missing/stale messages and the agreed timeout policy.
3. Keep rendering on the computer and label any slowed simulation; report wall-clock time separately.

Dependencies: ROBO-14, ROBO-17.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

### [ROBO-19](https://huu-hoan-hoang.atlassian.net/browse/ROBO-19): Evaluate repeated simulated task trials and failures

Parent: ROBO-3.

Purpose
Evaluate simulated task behavior after compatibility and mapping are checked.

Planning period: Month 4 (relative; actual dates TBD).
Owner role: AI and integration leads; named assignee TBD.

Acceptance checks
1. Use agreed initial conditions and trial allocation; record all attempts, completions, completion time, resets and failure causes.
2. Investigate rendered-versus-real image differences and task coverage when mapping is correct but task behavior fails.
3. Report achieved simulation results and limits; do not infer physical task success.

Dependencies: ROBO-18, ROBO-8.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

## [ROBO-4](https://huu-hoan-hoang.atlassian.net/browse/ROBO-4): Mobile app and AI/IoT integration

Goal
Build the main mobile interface, start with mocks, integrate agreed endpoints, and verify supported controls, connection/status/errors and usability. Gripper, XYZ, camera and stop features depend on system support; recording and speech need scope decisions.

Planning period: Semesters 1-2, Months 1-7 (relative; detailed task dates TBD).
Owner role: SoftDev lead; named assignee TBD.
Completion: linked tasks have the agreed evidence and reviewed limitations.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

Timeline planning basis (updated 8 October 2026)
Confirmed by PM: project started 13 September 2026; Semester 2 starts 11 January 2027. Confirmed submission/review deadlines: Project Plan 25 October 2026, Sprint 1 15 November 2026, Sprint 2 6 December 2026.
Estimated phase/review window: 09/13/2026 to 04/10/2027 (MM/DD/YYYY). App development and integration through Month 7.
The 12 May 2027 overall finish is derived from the eight-month duration and remains an estimated target. Phase boundaries are planning estimates, not confirmed assessment deadlines or effort estimates. Detailed task dates, owners, capacity and hardware arrival remain TBD. Hardware-dependent work must be reviewed when the SO-101 becomes available.

### [ROBO-20](https://huu-hoan-hoang.atlassian.net/browse/ROBO-20): Freeze app features and map SoftDev AC01-AC12

Parent: ROBO-4.

Purpose
Use the supplied SoftDev acceptance criteria, scope and constraints to agree the app checklist.

Planning period: Month 1 (relative; actual dates TBD).
Owner role: SoftDev lead with AI and IoT; named assignee TBD.

Acceptance checks
1. Choose the target mobile OS/device, communication method and supported command/status/camera endpoints.
2. Mark required, conditional and deferred features per semester; gripper, XYZ, camera and stop depend on control support.
3. Keep recording optional and speech separate; agree missing numerical responsiveness/usability targets and any dedicated AI-flow checks.

Dependencies: ROBO-8, ROBO-10.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

### [ROBO-21](https://huu-hoan-hoang.atlassian.net/browse/ROBO-21): Build mobile controls and feedback using mocks

Parent: ROBO-4.

Purpose
Develop app screens and navigation in parallel with board/model work, using labelled mock data and simulated AI responses.

Planning period: Month 2 (relative; actual dates TBD).
Owner role: SoftDev lead; named assignee TBD.

Acceptance checks
1. Implement clear labels, consistent target-device layout and easy access to a supported stop control.
2. Show connected, disconnected and failed connection states; test reconnect and unavailable-robot command feedback.
3. Demonstrate supported control/status/error flows with mock outcomes labelled as mocks.

Dependencies: ROBO-20.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

### [ROBO-22](https://huu-hoan-hoang.atlassian.net/browse/ROBO-22): Integrate app requests and feedback with board/simulation

Parent: ROBO-4.

Purpose
Connect the app to the agreed AI/IoT endpoints while model outputs pass through the control layer.

Planning period: Month 3 (relative; actual dates TBD).
Owner role: SoftDev and IoT/integration leads; named assignee TBD.

Acceptance checks
1. Verify agreed request formats, limits, statuses/errors and connection loss/reconnect.
2. Display sent/accepted/completed/failed only as supported by actual feedback; no false success after a reported failure.
3. Check manual-versus-AI control priority and unsupported endpoint feedback.

Dependencies: ROBO-21, ROBO-10, ROBO-18.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

### [ROBO-23](https://huu-hoan-hoang.atlassian.net/browse/ROBO-23): Verify supported controls, errors and app usability

Parent: ROBO-4.

Purpose
Run the agreed AC01-AC12 checklist on the chosen device with integration evidence separate from earlier mocks.

Planning period: Months 3-4 (relative; actual dates TBD).
Owner role: SoftDev lead; named assignee TBD.

Acceptance checks
1. Verify supported joints, gripper, speed and XYZ inputs/ranges; invalid or unavailable commands have clear feedback.
2. Verify incoming status updates, available camera stream/unavailable feedback and supported stop request/result feedback.
3. Test retries where appropriate, clear labels, accessible controls and consistent layout; record response/usability results against agreed targets.

Dependencies: ROBO-22, ROBO-20.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

### [ROBO-24](https://huu-hoan-hoang.atlassian.net/browse/ROBO-24): Validate app behavior with the physical SO-101

Parent: ROBO-4.

Purpose
Repeat agreed app checks using physical endpoints and the real arm when available.

Planning period: Months 5-7 (relative; actual dates TBD).
Owner role: SoftDev with IoT and integration; named assignee TBD.

Acceptance checks
1. Verify supported physical controls, camera/status updates, errors and manual/AI handover.
2. Record the app stop request, controller/arm actually stopping, and returned state as separate observations.
3. Record device/app/controller versions, failures and outstanding checks; do not substitute simulation results.

Dependencies: ROBO-26, ROBO-23, ROBO-27.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

## [ROBO-5](https://huu-hoan-hoang.atlassian.net/browse/ROBO-5): SO-101 hardware and controller readiness

Goal
Confirm arm access, assemble/calibrate the available arm, and verify controller, cameras, limits and supervised stop behavior before model-driven physical motion. Preserve the simulation route while hardware is delayed.

Planning period: Procurement Months 1-4; physical checks Month 5 (relative; detailed task dates TBD).
Owner role: IoT and hardware lead; named assignee TBD.
Completion: linked tasks have the agreed evidence and reviewed limitations.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

Timeline planning basis (updated 8 October 2026)
Confirmed by PM: project started 13 September 2026; Semester 2 starts 11 January 2027. Confirmed submission/review deadlines: Project Plan 25 October 2026, Sprint 1 15 November 2026, Sprint 2 6 December 2026.
Estimated phase/review window: 09/13/2026 to 02/10/2027 (MM/DD/YYYY). Procurement in Semester 1; physical readiness early Semester 2, subject to availability.
The 12 May 2027 overall finish is derived from the eight-month duration and remains an estimated target. Phase boundaries are planning estimates, not confirmed assessment deadlines or effort estimates. Detailed task dates, owners, capacity and hardware arrival remain TBD. Hardware-dependent work must be reviewed when the SO-101 becomes available.

### [ROBO-25](https://huu-hoan-hoang.atlassian.net/browse/ROBO-25): Confirm SO-101 procurement, delivery and access checkpoints

Parent: ROBO-5.

Purpose
Confirm purchase or loan options and realistic access to the physical SO-101.

Planning period: Months 1-4 (relative; actual dates TBD).
Owner role: PM and IoT/hardware lead; named assignee TBD.

Acceptance checks
1. Record the route, accountable owner, expected access date when confirmed and required parts.
2. Review availability monthly and link delay/fallback decisions.
3. Confirm Semester 2 lab access without making an unapproved purchase or inventing a delivery commitment.

Dependencies: ROBO-9.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

### [ROBO-26](https://huu-hoan-hoang.atlassian.net/browse/ROBO-26): Assemble, calibrate and verify the physical controller

Parent: ROBO-5.

Purpose
Establish basic physical control before model-driven motion, using the agreed lab procedure.

Planning period: Month 5, subject to arm availability (relative; actual dates TBD).
Owner role: IoT and hardware lead; named assignee TBD.

Acceptance checks
1. Record assembly/calibration, cameras/state inputs, controller path and operating limits.
2. Verify basic supervised movement, limits, stop/reset and camera/status endpoints.
3. Record the readiness gate and failures before permitting model-driven physical motion.

Dependencies: ROBO-25, ROBO-10.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

## [ROBO-6](https://huu-hoan-hoang.atlassian.net/browse/ROBO-6): Physical adaptation and evaluation

Goal
Establish a physical task reference, adapt with aligned local demonstrations if evidence requires it, and evaluate task completion, timing, app feedback and permitted faults under agreed conditions.

Planning period: Semester 2, Months 6-7 (relative; detailed task dates TBD).
Owner role: AI lead with IoT, SoftDev and integration; named assignee TBD.
Completion: linked tasks have the agreed evidence and reviewed limitations.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

Timeline planning basis (updated 8 October 2026)
Confirmed by PM: project started 13 September 2026; Semester 2 starts 11 January 2027. Confirmed submission/review deadlines: Project Plan 25 October 2026, Sprint 1 15 November 2026, Sprint 2 6 December 2026.
Estimated phase/review window: 02/11/2027 to 04/10/2027 (MM/DD/YYYY). Physical adaptation and evaluation, subject to hardware readiness.
The 12 May 2027 overall finish is derived from the eight-month duration and remains an estimated target. Phase boundaries are planning estimates, not confirmed assessment deadlines or effort estimates. Detailed task dates, owners, capacity and hardware arrival remain TBD. Hardware-dependent work must be reviewed when the SO-101 becomes available.

### [ROBO-27](https://huu-hoan-hoang.atlassian.net/browse/ROBO-27): Establish a trained-model physical task reference

Parent: ROBO-6.

Purpose
Replace simulated observations with real camera/state inputs and route actions through the selected controller.

Planning period: Month 6 (relative; actual dates TBD).
Owner role: AI with IoT/integration; named assignee TBD.

Acceptance checks
1. Verify real inputs, calibration, data format and action mapping in the physical path.
2. Run the agreed baseline task and record successes, failures and interventions.
3. Version the reference and retain a failure log for deciding whether adaptation is needed.

Dependencies: ROBO-26, ROBO-15, ROBO-17.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

### [ROBO-28](https://huu-hoan-hoang.atlassian.net/browse/ROBO-28): Collect aligned demonstrations and adapt only if needed

Parent: ROBO-6.

Purpose
Investigate calibration, task coverage and image/domain differences before changing the model.

Planning period: Month 6, conditional on observed need (relative; actual dates TBD).
Owner role: AI lead with IoT/hardware; named assignee TBD.

Acceptance checks
1. Agree and record synchronized camera/state/action demonstrations; app command logs alone are not training data.
2. Version collected data and any model adaptation settings.
3. Compare adapted and reference behavior under the same conditions, or document why adaptation was unnecessary/deferred.

Dependencies: ROBO-27.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

### [ROBO-29](https://huu-hoan-hoang.atlassian.net/browse/ROBO-29): Measure physical timing and improve the proven bottleneck

Parent: ROBO-6.

Purpose
Measure end-to-end physical timing before selecting an improvement.

Planning period: Month 7 (relative; actual dates TBD).
Owner role: AI and IoT/integration leads; named assignee TBD.

Acceptance checks
1. Measure board prediction, message delay, executed actions and pauses during actual movement.
2. Compare with agreed operating/timing limits and identify the measured bottleneck.
3. Change one relevant factor at a time and compare under the same conditions; acceleration stays optional until verified.

Dependencies: ROBO-27, ROBO-8.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

### [ROBO-30](https://huu-hoan-hoang.atlassian.net/browse/ROBO-30): Test supervised physical faults, stop and recovery

Parent: ROBO-6.

Purpose
Run only the agreed permitted fault cases under the lab procedure.

Planning period: Month 7 (relative; actual dates TBD).
Owner role: IoT with SoftDev and integration; named assignee TBD.

Acceptance checks
1. Test connection loss, stale/invalid commands, stop/reset and manual/AI handover.
2. Verify the app request, controller/arm stop and resulting feedback separately.
3. Record recovery behavior, supervision, versions and failures against [TBD TEAM permitted fault tests and recovery criteria].

Dependencies: ROBO-26, ROBO-24, ROBO-10.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

### [ROBO-31](https://huu-hoan-hoang.atlassian.net/browse/ROBO-31): Run agreed physical task trials and report uncertainty

Parent: ROBO-6.

Purpose
Evaluate the physical task using the agreed objects, destination, initial conditions and trial allocation.

Planning period: Month 7 (relative; actual dates TBD).
Owner role: AI and integration leads; named assignee TBD.

Acceptance checks
1. Count all attempts, correct completions, completion time and manual interventions.
2. Report failures, exclusions, resets, uncertainty and operating conditions.
3. Use supervisor-agreed targets; earlier draft numbers remain candidates, not confirmed requirements.

Dependencies: ROBO-27, ROBO-8.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

## [ROBO-7](https://huu-hoan-hoang.atlassian.net/browse/ROBO-7): Semester reviews, evidence and handover

Goal
Maintain traceability and official AI records, demonstrate achieved Semester 1 scope, agree the Semester 2 checkpoint, and deliver repeatable final system/app results and handover.

Planning period: Months 1-8; reviews Months 4 and 8 (relative; detailed task dates TBD).
Owner role: PM and component leads; named assignee TBD.
Completion: linked tasks have the agreed evidence and reviewed limitations.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

Timeline planning basis (updated 8 October 2026)
Confirmed by PM: project started 13 September 2026; Semester 2 starts 11 January 2027. Confirmed submission/review deadlines: Project Plan 25 October 2026, Sprint 1 15 November 2026, Sprint 2 6 December 2026.
Estimated phase/review window: 09/13/2026 to 05/12/2027 (MM/DD/YYYY). Reviews, evidence and handover throughout the project.
The 12 May 2027 overall finish is derived from the eight-month duration and remains an estimated target. Phase boundaries are planning estimates, not confirmed assessment deadlines or effort estimates. Detailed task dates, owners, capacity and hardware arrival remain TBD. Hardware-dependent work must be reviewed when the SO-101 becomes available.

### [ROBO-32](https://huu-hoan-hoang.atlassian.net/browse/ROBO-32): Deliver the Semester 1 board, simulation and app review

Parent: ROBO-7.

Purpose
Demonstrate the achieved Semester 1 scope and submit the agreed report evidence.

Planning period: Month 4 (relative; detailed task dates TBD).
Owner role: PM and component leads; named assignee TBD.

Acceptance checks
1. Provide a repeatable board/simulation/app package with frozen relevant versions and setup steps.
2. Keep mock, board runtime, live feedback and simulated task results distinct; record blockers and unsupported features.
3. Review whether the agreed minimum and task targets were achieved with the supervisor.

Dependencies: ROBO-15, ROBO-19, ROBO-23.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

Timeline planning basis (updated 8 October 2026)
Confirmed by PM: project started 13 September 2026; Semester 2 starts 11 January 2027. Confirmed submission/review deadlines: Project Plan 25 October 2026, Sprint 1 15 November 2026, Sprint 2 6 December 2026.
Estimated phase/review window: 12/13/2026 to 01/03/2027 (MM/DD/YYYY). Estimated Semester 1 final review window.
The 12 May 2027 overall finish is derived from the eight-month duration and remains an estimated target. Phase boundaries are planning estimates, not confirmed assessment deadlines or effort estimates. Detailed task dates, owners, capacity and hardware arrival remain TBD. Hardware-dependent work must be reviewed when the SO-101 becomes available.

### [ROBO-33](https://huu-hoan-hoang.atlassian.net/browse/ROBO-33): Review the Semester 2 scope and hardware fallback

Parent: ROBO-7.

Purpose
Freeze the next semester's assessed scope using Semester 1 evidence and confirmed physical access.

Planning period: Month 4 (relative; detailed task dates TBD).
Owner role: PM and supervisor; named assignee TBD.

Acceptance checks
1. Record the required Semester 2 outcomes, conditional features, owners and deadlines when agreed.
2. If the arm is unavailable, obtain a revised assessed scope with a documented fallback.
3. Update backlog dependencies and keep unperformed physical checks outstanding.

Dependencies: ROBO-32, ROBO-25, ROBO-11.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

Timeline planning basis (updated 8 October 2026)
Confirmed by PM: project started 13 September 2026; Semester 2 starts 11 January 2027. Confirmed submission/review deadlines: Project Plan 25 October 2026, Sprint 1 15 November 2026, Sprint 2 6 December 2026.
Estimated phase/review window: 01/04/2027 to 01/10/2027 (MM/DD/YYYY). Estimated Semester 2 scope review window, after the Semester 1 review.
The 12 May 2027 overall finish is derived from the eight-month duration and remains an estimated target. Phase boundaries are planning estimates, not confirmed assessment deadlines or effort estimates. Detailed task dates, owners, capacity and hardware arrival remain TBD. Hardware-dependent work must be reviewed when the SO-101 becomes available.

### [ROBO-34](https://huu-hoan-hoang.atlassian.net/browse/ROBO-34): Maintain issue-to-evidence traceability and AI records

Parent: ROBO-7.

Purpose
Maintain technical evidence indexes in GitHub and formal reports/the official AI Usage Log in Drive.

Planning period: Months 1-8 (relative; actual dates TBD).
Owner role: PM and all contributors; named assignee TBD.

Acceptance checks
1. Link Jira work items to relevant commits/PRs, experiment records, evidence and formal reports.
2. Record methods, versions, actual results, failures, limitations and attributable contributions.
3. Keep official Drive links and individual IC-SR/STAR references current; [TBD TEAM AI Usage Log and report locations].

Dependencies: None.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

### [ROBO-35](https://huu-hoan-hoang.atlassian.net/browse/ROBO-35): Complete final system/app trials and repeatable handover

Parent: ROBO-7.

Purpose
Prepare the final demonstration, report and handover, with time for repairs and revision.

Planning period: Month 8 (relative; detailed task dates TBD).
Owner role: PM and component leads; named assignee TBD.

Acceptance checks
1. Freeze app/model/data/controller/simulator versions and include calibration, interface/setup and deployment instructions.
2. Provide final results including failures, known issues, future work and a repeated demonstration.
3. Meet [TBD TEAM final acceptance and submission checklist] with the supervisor; keep formal reports in Drive.

Dependencies: ROBO-24, ROBO-29, ROBO-30, ROBO-31, ROBO-33, ROBO-34.
Evidence: link the relevant GitHub artifact/PR and Drive report.
Source plan: https://docs.google.com/document/d/1xUfMJJlBsaF_yxX0kdeXg7yiOIvMeznC8Z6g25WLXUI

Timeline planning basis (updated 8 October 2026)
Confirmed by PM: project started 13 September 2026; Semester 2 starts 11 January 2027. Confirmed submission/review deadlines: Project Plan 25 October 2026, Sprint 1 15 November 2026, Sprint 2 6 December 2026.
Estimated phase/review window: 04/11/2027 to 05/12/2027 (MM/DD/YYYY). Estimated final evaluation and handover window.
The 12 May 2027 overall finish is derived from the eight-month duration and remains an estimated target. Phase boundaries are planning estimates, not confirmed assessment deadlines or effort estimates. Detailed task dates, owners, capacity and hardware arrival remain TBD. Hardware-dependent work must be reviewed when the SO-101 becomes available.

### [ROBO-36](https://huu-hoan-hoang.atlassian.net/browse/ROBO-36): Submit the Project Plan - deadline 25 October 2026

Parent: ROBO-7. Start and due date: 10/25/2026 (MM/DD/YYYY). Label: confirmed-deadline.

Confirmed submission/review deadline: 25 October 2026 (PM, 8 October 2026).

Prepare and submit the Project Plan covering the problem, success definition, scope, stakeholders, constraints, known and unknown technical decisions, two-semester execution plan, risks and evidence links. Coordinate the planning work in ROBO-8, ROBO-9, ROBO-10 and ROBO-11.

Acceptance: the required plan is submitted and the submission receipt/review evidence is linked. [TBD TEAM: official rubric, submission location, submission time and named owner].

Schedule: start and due dates are the same day to represent a deadline marker in Jira Timeline, not one day of work. Preparation is managed through the linked planning tasks. Project start: 13 September 2026. Semester 2 starts 11 January 2027. Formal report stays in Google Drive.

### [ROBO-37](https://huu-hoan-hoang.atlassian.net/browse/ROBO-37): Submit and review Sprint 1 - deadline 15 November 2026

Parent: ROBO-7. Start and due date: 11/15/2026 (MM/DD/YYYY). Label: confirmed-deadline.

Confirmed submission/review deadline: 15 November 2026 (PM, 8 October 2026). This is a review/submission deadline, not a sprint start date.

Prepare the required Sprint 1 submission and demonstrate the work actually completed against the agreed sprint scope. Link Jira issues to GitHub code/results and the formal Drive report. Record blockers, failures, unverified assumptions and next steps.

Acceptance: the required submission/review is completed and the evidence is linked. [TBD TEAM: official rubric, committed work items, submission location/time and named owner]. Performance thresholds and exact deliverables remain TBD until agreed.

Schedule: start and due dates are the same day to represent a deadline marker in Jira Timeline, not one day of work. Jira sprint duration, start and capacity remain unconfirmed; no sprint is started automatically.

### [ROBO-38](https://huu-hoan-hoang.atlassian.net/browse/ROBO-38): Submit and review Sprint 2 - deadline 6 December 2026

Parent: ROBO-7. Start and due date: 12/06/2026 (MM/DD/YYYY). Label: confirmed-deadline.

Confirmed submission/review deadline: 6 December 2026 (PM, 8 October 2026). This is a review/submission deadline, not a sprint start date.

Prepare the required Sprint 2 submission and demonstrate the work actually completed against the agreed sprint scope. Link Jira issues to GitHub code/results and the formal Drive report. Record integration progress, blockers, failures and next steps for the Semester 1 final review (ROBO-32).

Acceptance: the required submission/review is completed and the evidence is linked. [TBD TEAM: official rubric, committed work items, submission location/time and named owner]. Keep mock demonstrations, board inference, closed-loop simulation and physical results clearly identified.

Schedule: start and due dates are the same day to represent a deadline marker in Jira Timeline, not one day of work. Jira sprint duration, start and capacity remain unconfirmed; no sprint is started automatically.
