# STM32H5F5 Interface Specification - Draft

## 1. Purpose

This document records the proposed communication architecture, interface
requirements, research findings, and verification plan for the SO-101 robot
arm project using the STM32H5F5 MCU on the VENTUNO Q.

It supports SO101-40 by identifying the information needed to define and
verify the command path from the AI/application running on the MPU to the
MCU and the simulator.

This document is a research draft, not an approved interface contract.
Project-specific implementation details must be verified before use.

## 2. System Architecture

The official VENTUNO Q documentation describes a dual-processor platform
with a Qualcomm MPU running Linux and an STM32H5F5 microcontroller.

The documented Arduino Bridge ecosystem supports RPC-based communication
between the MPU and MCU.

Proposed logical flow:

AI/application
    -> MPU-side command generation
    -> MPU-to-MCU interface
    -> MCU-side command validation and processing
    -> confirmed joint-control interface
    -> SO-101 simulation or robot arm

The exact integration path between the MCU, simulator, and robot arm has
not yet been confirmed.

### 2.1 Confirmed Platform Information

- The VENTUNO Q includes a Qualcomm MPU running Linux.
- The platform includes an STM32H5F5 MCU.
- Arduino documents the Arduino_RouterBridge library for MPU-to-MCU
  communication.
- Official MCU examples cover peripheral functions and communication
  protocols.

These platform capabilities do not prove that the project's SO-101
command interface or simulator integration has already been implemented.

### 2.2 Project-Specific Items Requiring Verification

- Which application or AI component generates the joint commands.
- Which MPU-side API and MCU firmware implementation will be used.
- How the simulator receives commands or MCU results.
- Whether the MCU controls the actuators directly or through another
  controller or interface.
- Whether joint-position feedback is available and where it originates.

## 3. Communication Approach

The Arduino_RouterBridge library and Bridge RPC mechanism are candidate
options for communication between the MPU and MCU.

The selected approach must be confirmed against the project's actual
software architecture and firmware.

Research and verification tasks:

1. Identify the supported MPU-side API and MCU-side API.
2. Inspect official examples for registering MCU functions and invoking
   them from the MPU.
3. Verify how the project's application will invoke the selected interface.
4. Confirm supported argument types, return values, and error handling.
5. Determine whether JSON is used only for test fixtures or is converted
   into another representation before transport.
6. Record any required serialization, message framing, sequence handling,
   timeout, and response semantics.
7. Confirm how the simulator receives commands and reports results.

Do not assume that JSON is the wire format. The actual interface contract
must define the representation used at each boundary.

## 4. Command Data Requirements

Before implementation, the command interface must specify the following
items.

| Item | Required Definition | Status |
|---|---|---|
| Operation | Command name or operation identifier | Pending |
| Joint targets | Required joint names, order, and mapping | Pending |
| Data representation | Supported types, precision, and encoding | Pending |
| Units | Joint-angle units and any duration units | Pending |
| Joint limits | Valid range and authoritative source for each joint | Pending |
| Command identity | Sequence ID, duplicate handling, or freshness rules | Pending |
| Response | Acknowledgement, completion status, and error representation | Pending |
| Timeout | Timeout threshold and response policy | Pending |
| Reset and recovery | Approved state and recovery behaviour | Pending |
| Position feedback | Actual-position source and measurement method | Pending |
| Simulator integration | Command input and result-output interface | Pending |

The existing sample_input.json is a logical test fixture only. Its field
names, example values, sequence ID, and duration are not an approved
transport schema or confirmed robot configuration.

## 5. MCU Processing Requirements

The MCU-side implementation should be assessed for its ability to:

1. Receive a command through the confirmed interface.
2. Decode the command according to the approved representation.
3. Validate command structure, required fields, and data types.
4. Validate joint targets against confirmed limits.
5. Reject invalid commands without unintended execution.
6. Convert accepted targets into the representation required by the
   confirmed joint-control system.
7. Expose or return command status and errors where supported.
8. Handle timeout, duplicate commands, and reset according to approved
   policies.
9. Provide position feedback only where the selected environment and
   implementation support it.

The actual actuator-control method and feedback source must be confirmed
from the project firmware and hardware design.

## 6. Planned Verification

Verification should proceed incrementally. Do not attempt robot movement
until the interface, hardware setup, and relevant safety requirements
have been confirmed.

| Stage | Verification Activity | Expected Evidence | Status |
|---|---|---|---|
| V-01 | Confirm board recognition and development environment | Board identification, environment details, setup log | Planned |
| V-02 | Run a documented MCU example | Example name, build/upload result, observed output | Planned |
| V-03 | Test a simple non-motion MPU-to-MCU call | Request, response, log, and run identifier | Planned |
| V-04 | Test valid and invalid command handling | Inputs, response status, error details, and execution log | Planned |
| V-05 | Confirm the joint-control interface | Firmware/API reference, joint mapping, units, and limits | Planned |
| V-06 | Test joint targets in the selected simulator | Target and actual positions where available, per-joint errors, environment details | Planned |
| V-07 | Assess MCU execution and physical-arm behaviour if required | Separate MCU or hardware run record and relevant measurements | Pending environment and scope confirmation |

### 6.1 Evidence Requirements

For every executed verification, record:

- Test ID and unique run ID.
- Date and execution environment.
- Relevant repository commit and software or firmware version.
- Input command and relevant configuration.
- Expected and actual response.
- Logs and evidence file paths.
- Target and actual joint positions where available.
- Absolute error for each assessed joint where positioning is measured.
- Result: PASS, FAIL, or BLOCKED.
- Rationale for the result and any unresolved issue.

A planned test or an existing script is not evidence that the test passed.

## 7. Relationship to SO101-40 Test Artifacts

This specification must remain consistent with the following files:

- test_specification.csv: proposed test cases and acceptance criteria.
- sample_input.json: logical example input for TC-01.
- expected_output.json: proposed expected outcome and required evidence.
- test_evidence_mapping.md: candidate simulation coverage and evidence boundaries.
- decision_log.md: decisions, rationale, decision authority, and open questions.
- handover_checklist.md: planning and handoff readiness.

Any confirmed change to the command schema, joint mapping, units, tolerance,
timeout policy, or result format must be reflected in the relevant artifacts.

Unconfirmed details must remain explicitly marked as pending.

## 8. Open Questions

1. Which MPU-side application or AI component generates the commands?
2. Which communication API and firmware implementation will be used?
3. What command schema and data representation are supported?
4. What are the approved joint names, mapping, units, and limits?
5. How are commands acknowledged and errors reported?
6. What timeout, duplicate-command, reset, and recovery policies apply?
7. How are target and actual joint positions measured?
8. What position tolerance and acceptance criteria have been approved?
9. Which environment is authoritative for each test: MuJoCo, MCU execution,
   or physical-arm validation?
10. What is the required final result artifact format and storage location?
11. What additional deliverable was omitted from the truncated meeting note?

Record the decision authority, rationale or source evidence, and
confirmation date when each decision is resolved. Do not infer missing
requirements from incomplete meeting notes.

## 9. References

- Arduino VENTUNO Q:
  https://docs.arduino.cc/hardware/ventuno-q
- VENTUNO Q Microcontroller Guide:
  https://docs.arduino.cc/tutorials/ventuno-q/mcu-examples/
- VENTUNO Q Arduino IDE Guide:
  https://docs.arduino.cc/tutorials/ventuno-q/arduino-ide/

These references describe platform capabilities and development examples.
They do not establish that the project-specific SO-101 interface has been
implemented or validated.

## 10. Status

Status: Draft - pending project implementation, interface confirmation,
and required environment verification.

No physical STM32H5F5 test result, simulator pass, or physical SO-101
validation is claimed by this document.
