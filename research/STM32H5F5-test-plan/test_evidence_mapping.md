# STM32H5F5 Test Evidence Mapping

## 1. Purpose

This document maps the proposed test cases to potentially relevant existing
MuJoCo simulation scripts and identifies the additional evidence required
for the STM32H5F5 test milestone.

A script-to-test mapping indicates a candidate source of evidence, not proof
that a scenario has passed. Coverage must be verified against the actual
test implementation, execution record, and result artifact.

## 2. Test-to-Evidence Mapping

| Test Case | Candidate Existing Script | Reported Simulation Coverage | Additional Evidence Required |
|---|---|---|---|
| TC-01 Valid six-joint command | `stm32_interface_test.py` | Valid action packet and simulated joint positions are reported in the existing test-plan records | Confirm the script's actual assertions and output; approved interface format; run ID; target-versus-actual values; approved tolerance; target-environment result |
| TC-02 Joint limit violation | `stm32_interface_test.py`; `so101_controller_test.py` | Invalid joint-target rejection is reported in the existing test-plan records | Verify the exact test artifact and rejection behavior; approved fault response; target-environment rejection evidence |
| TC-03 Incomplete target set | `supervision_test.py` | Incomplete target-set rejection is reported in the existing test-plan records | Verify the exact test artifact; approved validation policy and expected response |
| TC-04 Replayed command | `supervision_test.py` | Replayed-sequence rejection is reported in the existing test-plan records | Verify the exact test artifact; approved sequence or duplicate-command policy; target-environment evidence |
| TC-05 Corrupted packet | `end_to_end_test.py` | A corrupted-frame and CRC-error scenario is reported; confirm that both behaviors are actually implemented and exercised | Verify the test implementation and execution artifact; approved packet/integrity specification; target-environment evidence |
| TC-06 Positioning accuracy | `trajectory_test.py`; `stm32_interface_test.py` | Simulated target tracking and joint-position results are reported in the existing test-plan records | Verify the exact test artifact; approved tolerance; measurement method; recorded error for every assessed joint |
| TC-07 Reset and recovery | `reset_step_test.py`; `state_capture_test.py` | Simulation reset, stepping, and state-restoration scenarios are reported | Verify which reset/recovery behavior is tested; approved reset criteria; target-environment recovery evidence |
| TC-08 Timeout or lost response | `supervision_test.py` | A simulated watchdog-timeout scenario is reported; this does not automatically establish communication-timeout coverage | Verify the exact test artifact and timeout mechanism; approved timeout threshold and recovery policy; target-environment evidence |

## 3. Evidence Status

### 3.1 Existing MuJoCo Evidence

The SO101-49 results README reportedly records the following simulation checks:

- Scene loading and camera registration/rendering.
- Six-joint control and invalid joint-target rejection.
- Gripper movement toward target angles.
- `qpos`, `qvel`, and `ctrl` capture/restore checks.

The recorded six-joint maximum position error was approximately
`0.000670 rad`.

This value is a reported result from a simulation run. It is not a
team-approved acceptance threshold and must not be used as one without
explicit approval.

The relevant result files and scripts must be checked before asserting that
a particular test case has been covered or passed.

### 3.2 Evidence Boundaries

- MuJoCo evidence supports only the simulation scenarios actually exercised
  by the corresponding scripts.
- A test script's existence does not, by itself, prove that it ran or passed.
- The SO101-49 results README does not establish physical STM32H5F5 or
  physical SO-101 validation.
- Clean-checkout reproducibility remains pending until the setup is
  reproduced and the relevant scripts are rerun with recorded results.
- A simulated watchdog timeout must not be treated as proof of an actual
  MPU-to-MCU communication timeout unless that behavior is specifically
  exercised and evidenced.
- Physical MCU results must be recorded separately from simulation results.

### 3.3 Pending Evidence and Decisions

- Approved interface and packet specification.
- Confirmed joint names, mapping, and units.
- Team-approved position-error tolerance and assessment criteria.
- Agreed timeout, replay, reset, and fault-response policies.
- Final result artifact format and storage location.
- Identification of the deliverable omitted from the truncated meeting note.
- Verified script execution records and reproducibility evidence for the
  scenarios claimed as covered.

## 4. Required Result Record

For each executed test, record:

- Test ID and unique run ID.
- Date and test environment.
- Software, firmware, model, and configuration version where applicable.
- Relevant repository commit.
- Input command and test configuration.
- Expected and actual command, motion, or system state.
- Target and actual joint positions when available.
- Absolute position error for each applicable joint.
- Fault and error information.
- Evidence file paths or stable artifact references.
- Result: `PASS`, `FAIL`, or `BLOCKED`.
- Rationale for the result, including unmet prerequisites or missing evidence.
- Tester and relevant reviewer, where applicable.

A test must not be marked `PASS` solely because a script exists or a
related simulation scenario has passed.

## 5. Outstanding Decisions

- Confirm the interface contract and joint units.
- Confirm the acceptable position-error threshold and measurement method.
- Confirm timeout, reset, replay, and fault-response policies.
- Confirm the missing deliverable from the truncated meeting note.
- Confirm the final result artifact format and storage location.
- Confirm which test scenarios require MuJoCo, STM32H5F5 execution,
  or physical-arm validation.
- Confirm the evidence required for a reproducible test run and handoff.
