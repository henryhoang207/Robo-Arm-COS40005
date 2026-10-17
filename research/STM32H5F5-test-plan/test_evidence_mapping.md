# STM32H5F5 Test Evidence Mapping

## 1. Purpose

This document maps the eight proposed SO101-40 test cases to the
simulation evidence reported in SO101-49.

It distinguishes reported simulation results from verified test artifacts,
STM32H5F5 execution, and physical SO-101 validation.

The mappings identify potentially relevant evidence. They do not establish
that an SO101-40 test has passed its approved acceptance criteria.

## 2. Test-to-Evidence Mapping

| Test Case | Related SO101-49 Evidence | Current Evidence Assessment | Additional Evidence Required |
|---|---|---|---|
| TC-01 Valid six-joint command | Six-joint control; maximum reported position error approximately 0.000670 rad | Relevant MuJoCo result reported; exact test-to-artifact mapping still needs verification | Actual input and output; run ID; target and actual positions; approved interface contract and tolerance; target-environment result |
| TC-02 Joint limit violation | Shoulder-pan target of 10 rad rejected as outside joint limits | Relevant MuJoCo result reported | Exact execution artifact; configured joint-limit source; rejection response; STM32H5F5 result if required |
| TC-03 Incomplete target set | No specific result identified in the supplied SO101-49 README | Not verified by this README | Test implementation, actual execution output, expected validation policy, and result artifact |
| TC-04 Replayed command | No specific result identified in the supplied SO101-49 README | Not verified by this README | Confirmed sequence or duplicate-command policy, test implementation, execution output, and result artifact |
| TC-05 Corrupted packet | No specific result identified in the supplied SO101-49 README | Not verified by this README | Confirmed message format and integrity rules, test implementation, execution output, and result artifact |
| TC-06 Positioning accuracy | Six-joint control result with reported maximum error of approximately 0.000670 rad | Preliminary simulation evidence; not proof of compliance with a team-approved tolerance | Exact test artifact; target and actual positions; measurement method; approved tolerance; required target-environment evidence |
| TC-07 Reset and recovery | qpos, qvel, and ctrl capture/restore checks reported as passed locally | Partial evidence for simulation-state restoration; not proof of complete reset or recovery behaviour | Exact test output; agreed reset/recovery criteria; additional state and fault evidence where required |
| TC-08 Timeout or lost response | No specific communication-timeout result identified in the supplied SO101-49 README | Not verified by this README | Confirmed timeout policy, test implementation, actual execution output, recovery evidence, and result artifact |

## 3. Existing Simulation Evidence

The supplied SO101-49 README reports the following local MuJoCo results:

- Scene loading passed.
- Two camera views were detected.
- Top-camera and wrist-camera renders were saved and uploaded.
- Six-joint control passed with a reported maximum position error of
  approximately 0.000670 rad.
- An invalid shoulder-pan target of 10 rad was rejected.
- Gripper movement reached two target angles with reported errors around
  0.000003 rad or less.
- qpos, qvel, and ctrl capture/restore checks passed locally.

These are reported results from computer-based simulation. The exact
execution artifacts and repository state must be verified before claiming
reproducible coverage for an individual SO101-40 test case.

## 4. Evidence Boundaries

- MuJoCo results establish simulation behaviour only for the scenarios
  actually executed.
- The existence of a test script does not prove that it ran or passed.
- The supplied README does not establish physical STM32H5F5 validation
  or physical SO-101 validation.
- Camera images are simulation renders, not physical camera feeds.
- Gripper movement does not establish grasp force or successful object
  holding.
- qpos, qvel, and ctrl restoration does not establish restoration of every
  internal simulator state.
- The reported 0.000670 rad error is an observed simulation result, not
  an approved acceptance threshold.
- The controller's 0.01 rad test-code threshold is provisional and has
  not been approved by the team.
- Clean-checkout reproducibility remains unconfirmed until the documented
  setup is reproduced and the relevant scripts are rerun.

## 5. Required Result Record

For every executed test, record:

- Test ID and unique run ID.
- Date and execution environment.
- Repository commit and relevant software, firmware, model, or
  configuration version.
- Input command and test configuration.
- Expected and actual response or system state.
- Target and actual joint positions when available.
- Absolute error for each assessed joint when applicable.
- Fault and error information.
- Evidence file paths or stable artifact references.
- Result: PASS, FAIL, or BLOCKED.
- Rationale for the result and any unmet prerequisites.
- Tester and reviewer, where applicable.

A test must not be marked PASS solely because a related script exists or
a simulation result has been reported.

## 6. Outstanding Decisions and Actions

- Verify the exact SO101-49 test scripts, outputs, and evidence paths.
- Reproduce relevant simulation tests from a repository checkout if
  reproducibility is required for handoff.
- Confirm the interface contract, joint mapping, and units.
- Obtain approval for the position-error tolerance and measurement method.
- Confirm timeout, replay, reset, and fault-response policies.
- Confirm the final result artifact format and storage location.
- Identify the additional deliverable omitted from the truncated
  meeting note.
- Confirm which checks require MuJoCo, STM32H5F5 execution, or physical-arm
  validation.

## 7. Source

Source: research/results/SO101-49/README.md.

The evidence assessments above are limited to the results reported in
that README. No additional test execution or hardware validation is
claimed by this mapping.
