# STM32H5F5 Test Evidence Mapping

## 1. Purpose

This document maps the proposed test cases to existing MuJoCo simulation
test scripts and identifies the additional evidence needed for the
STM32H5F5 test milestone.

The mappings below identify relevant test coverage, not proof that
the target STM32H5F5 environment has passed the tests.

## 2. Test-to-Evidence Mapping

| Test Case | Relevant Existing Script | Existing Simulation Coverage | Additional Evidence Required |
|---|---|---|---|
| TC-01 Valid six-joint command | `stm32_interface_test.py` | Valid action packet and simulated joint positions | Approved interface format; run ID; target-versus-actual values; accepted tolerance; target-environment result |
| TC-02 Joint limit violation | `stm32_interface_test.py`; `so101_controller_test.py` | Invalid joint target rejection | Approved fault response; target-environment rejection evidence |
| TC-03 Incomplete target set | `supervision_test.py` | Incomplete target set rejected | Confirm expected error code and response policy |
| TC-04 Replayed command | `supervision_test.py` | Replayed sequence rejected | Approved sequence policy and target-environment evidence |
| TC-05 Corrupted packet | `end_to_end_test.py` | Corrupted frame and CRC error scenario | Approved packet/CRC specification and target-environment evidence |
| TC-06 Positioning accuracy | `trajectory_test.py`; `stm32_interface_test.py` | Simulated target tracking and joint-position results | Approved tolerance; measurement method; recorded error for every joint |
| TC-07 Reset and recovery | `reset_step_test.py`; `state_capture_test.py` | Simulation reset, stepping, and state restoration scenarios | Approved reset criteria and target-environment recovery evidence |
| TC-08 Timeout or lost response | `supervision_test.py` | Simulated watchdog timeout scenario | Approved timeout threshold, recovery policy, and target-environment evidence |

## 3. Evidence Status

### Existing MuJoCo Evidence

The SO101-49 results README records the following simulation checks:

- Scene loading and camera registration/rendering.
- Six-joint control and invalid joint-target rejection.
- Gripper movement to target angles.
- qpos, qvel, and ctrl capture/restore checks.

The recorded six-joint maximum position error was approximately 0.000670 rad.
This is a result from the documented simulation run, not a team-approved
acceptance threshold.

### Evidence Boundaries

- Existing MuJoCo evidence supports only the simulation scenarios actually
  exercised by the corresponding scripts.
- The SO101-49 results README does not establish physical STM32H5F5 or
  physical SO-101 validation.
- The existence of a test script does not, by itself, prove that the test
  passed in the current repository checkout.
- Clean-checkout reproducibility remains pending until the setup is reproduced
  and the relevant scripts are rerun.
- Physical MCU results must be recorded separately from simulation results.

### Pending Evidence

- Approved interface and packet specification.
- Team-approved position-error tolerance and assessment criteria.
- Agreed timeout, replay, reset, and fault-response policies.
- Final result artifact format and storage location.
- Identification of the deliverable omitted from the truncated meeting note.

## 4. Required Result Record

For each executed test, record:

- Test ID and run ID
- Date and test environment
- Software/model version or commit
- Input command and relevant configuration
- Expected and actual state
- Target and actual joint positions
- Absolute position error for every applicable joint
- Fault/error information
- Evidence file paths
- PASS/FAIL/BLOCKED result and rationale
- Tester and any relevant reviewer

## 5. Outstanding Decisions

- Confirm the interface contract and joint units.
- Confirm the acceptable position-error threshold.
- Confirm timeout, reset, replay, and fault-response policies.
- Confirm the missing deliverable from the truncated meeting note.
- Confirm the final result artifact format and storage location.

