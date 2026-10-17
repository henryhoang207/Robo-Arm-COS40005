# STM32H5F5 Simulator Test Plan

## 1. Purpose

This folder contains the proposed test specification and planning records
for the STM32H5F5 simulator test work.

The objective is to agree on test inputs, expected outputs, positioning
evidence, acceptance criteria, and the final result artifact before
implementation and validation.

## 2. Files

| File | Purpose |
|---|---|
| `test_specification.csv` | Defines the proposed test cases, inputs, expected outputs, evidence, and acceptance criteria |
| `sample_input.json` | Provides an example logical input for a six-joint command |
| `expected_output.json` | Defines the proposed expected result and evidence for TC-01 |
| `decision_log.md` | Records proposed decisions, rationale, decision authority, and unresolved questions |

## 3. Current Test Scope

The proposed test cases cover:

1. Valid six-joint command
2. Joint limit violation
3. Incomplete target set
4. Replayed command
5. Corrupted packet
6. Positioning accuracy
7. Reset and recovery
8. Timeout or lost response

These cases are proposals pending confirmation of the interface contract
and acceptance criteria.

## 4. Positioning Evidence

For positioning tests, the proposed evidence includes:

- Test/run identifier
- Requested target angle for each joint
- Actual reported or measured angle for each joint
- Absolute position error for each joint
- Completion state and fault code
- Timestamp and relevant run log

For joint i:

absolute position error = |actual angle - target angle|

The acceptable error threshold and measurement method must be approved
before the test can be formally assessed.

## 5. Evidence and Validation Boundaries

Existing MuJoCo tests can support simulator test design and provide
simulation evidence for the scenarios they actually cover.

MuJoCo results must not be reported as proof that the STM32H5F5 MCU or
physical SO-101 robot arm has passed the same tests.

Record the environment used for each test result:

- MuJoCo simulation
- STM32H5F5 simulator or execution environment, once confirmed
- Physical MCU or robot arm, if applicable

## 6. Outstanding Items

- Confirm the missing deliverable from the truncated meeting note.
- Confirm command and response formats, joint mapping, and units.
- Agree on joint-position tolerance and assessment criteria.
- Agree on timeout, replay, reset, and recovery behavior.
- Confirm the final result artifact format and storage location.
- Identify which tests require simulation, MCU, or physical-arm validation.

## 7. Planning Dates

- 19 October 2026: planning handoff deadline
- 30 November 2026: run-output milestone

These dates do not imply that implementation or hardware validation
has already been completed.

## 8. Status

Planning documents are in draft status. Unconfirmed requirements must
remain clearly marked as pending until supported by an agreed decision
or documented source.
