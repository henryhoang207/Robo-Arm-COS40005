# STM32H5F5 Simulator Test - Decision Log

## 1. Document Information

- Project: SO-101 Robot Arm
- MCU identifier: STM32H5F5
- Task: Clarify the STM32H5F5 simulator test's complete deliverables
- Primary assignee: Nguyen
- IoT lead: Chung
- Planning handoff deadline: 19 October 2026
- Run-output milestone: 30 November 2026
- Status: Draft - pending confirmation

## 2. Purpose

This document records proposed test-plan decisions, their rationale,
the person or role responsible for approval, and unresolved questions.

The purpose is to agree on the test inputs, expected outputs,
positioning evidence, assessment criteria, and final result artifact
before simulator/MCU implementation.

## 3. Decision Register

| ID | Topic | Current Proposal | Rationale / Evidence | Decision Authority | Status |
|---|---|---|---|---|---|
| D-01 | Test scope | Start with valid commands, joint limits, incomplete inputs, replayed commands, corrupted packets, positioning accuracy, reset/recovery, and timeout handling | Draft test_specification.csv | IoT lead and relevant interface owners | Proposed |
| D-02 | Sample joint targets | Use the six target values in sample_input.json as a logical example | Draft sample_input.json and existing MuJoCo test scenarios | IoT lead; confirm joint names and units | Proposed |
| D-03 | Positioning tolerance | Do not set a numeric threshold until the team approves one | No approved tolerance is recorded in the available task information | IoT lead / project decision authority | Pending |
| D-04 | Command and response interface | Confirm command schema, packet format, units, sequence handling, and state/error response | Interface contract is not yet confirmed in this planning record | IoT and Software Development interface owners | Pending |
| D-05 | Test result artifact | Proposed evidence includes input, response, target-versus-actual positions, absolute errors, logs, and run identification | Required evidence listed in test_specification.csv and expected_output.json | IoT lead / team | Proposed |
| D-06 | Missing deliverable | Check the original meeting notes or confirm with the meeting-note owner/project decision authority. If the source cannot be recovered by handoff, record the unresolved item, confirmation owner, and follow-up action without inventing the missing requirement. | Jira task identifies truncated source wording; the original missing content has not yet been verified. | Meeting-note owner / project decision authority | Unresolved |
| D-07 | Simulator versus physical validation | Label MuJoCo evidence as simulation-only; keep STM32H5F5 and physical-arm validation separate | Existing evidence was produced in MuJoCo, not on the physical MCU or arm | IoT lead and relevant test owners | Proposed |

## 4. Evidence Available

- A draft test specification containing eight test cases.
- A sample logical input for a six-joint command.
- An expected-output draft for TC-01.
- Existing MuJoCo simulation test results may support scenario design.

Important: Existing simulation results do not establish that the STM32H5F5
or physical SO-101 arm has passed the same tests.

## 5. Unresolved Questions

1. What additional deliverable was omitted from the truncated meeting note?
2. What are the approved command and response formats?
3. What units and joint-name mapping must the interface use?
4. What position-error tolerance and measurement method will be accepted?
5. What timeout, replay, reset, and recovery policies should be tested?
6. What format and storage location are required for the final test result artifact?
7. Which cases require simulator testing, physical MCU testing, or physical-arm testing?

## 5.1. Decision and Confirmation Rules

- A proposal is not an approved decision until the relevant decision authority confirms it.
- Record the decision, rationale or source evidence, approver role, and confirmation date when a decision is made.
- If the original meeting-note wording cannot be recovered, record the limitation and follow-up owner; do not infer the missing deliverable.
- Keep unverified interface details, position tolerances, and validation requirements marked as pending.

## 6. Schedule and Scope Impact

- By 19 October 2026: prepare and hand off the proposed test plan, record
  available evidence, and identify unresolved decisions.
- By 30 November 2026: run-output milestone for the STM32H5F5 test work.
- Implementation and hardware validation are not claimed as complete by this
  planning document.
- Any delay caused by unresolved interface definitions or acceptance criteria
  must be recorded when confirmed; no unsupported estimate is assumed.

## 7. Review History

| Date | Change | Owner | Status |
|---|---|---|---|
| 17 October 2026 | Initial decision log drafted from the available Jira task and test-plan files | Nguyen | Pending review |
