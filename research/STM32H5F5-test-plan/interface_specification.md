# STM32H5F5 Interface Specification - Draft

## 1. Purpose

This document defines the proposed communication and command-processing interface between the AI/application running on the VENTUNO Q's MPU and the STM32H5F5 MCU for the SO-101 robot arm project.

This is a research draft. The actual project implementation and hardware interfaces must be verified before the specification is approved.

## 2. System Architecture

The VENTUNO Q integrates:
- A Qualcomm MPU running Linux for application-level processing.
- An STM32H5F5 MCU for microcontroller-level operations.
- An RPC-based communication mechanism supported by the Arduino Bridge ecosystem.

Proposed logical flow:

AI/application → MPU-side command generation → MPU-to-MCU communication → MCU firmware validation → joint-control interface → robot arm.

The actual motor-control architecture and actuator interface remain to be verified.

## 3. Communication Approach

Official Arduino documentation describes the Arduino_RouterBridge library and RPC communication between the Linux MPU and STM32 MCU.

Research tasks:
- Identify the available MPU-to-MCU communication API and supported data types.
- Inspect official examples for exposing MCU functions and invoking them from the MPU.
- Verify how the project's application will call the MCU interface.
- Determine whether JSON is only an application-level test format or is used directly by the communication layer.
- Record any required message framing, serialization, sequence handling and error reporting.

Do not assume that the project's wire format is JSON. Confirm the actual implementation before finalising the interface.

## 4. Command Data Requirements

The command interface must define:
- Command identifier or operation.
- Target values for the required joints.
- Data types and units.
- Valid joint ranges.
- Command sequence or freshness rules, if required.
- Error and response representation.
- Timeout and reset behaviour.

The exact schema and field names are pending verification.

## 5. MCU Processing Requirements

The MCU-side implementation should be assessed for its ability to:
1. Receive a command through the selected interface.
2. Decode the command according to the agreed format.
3. Validate its structure and values.
4. Reject invalid or out-of-range commands safely.
5. Convert accepted targets into the representation required by the joint-control system.
6. Return or expose status information where supported.

The exact actuator-control method must be confirmed from the project firmware and hardware design.

## 6. Planned Verification

Initial verification should proceed incrementally:
1. Confirm that the VENTUNO Q is recognised and the development environment is working.
2. Run a documented MCU example.
3. Verify MPU-to-MCU communication using a simple non-motion command.
4. Verify valid and invalid command handling.
5. Confirm the actual joint-control interface before attempting robot movement.
6. Test joint targets and position feedback only when the hardware and safety requirements are understood.

Record actual inputs, outputs, logs, configuration and test status.

## 7. Open Questions

- Which MPU-side application or AI component generates the robot commands?
- Which communication API and firmware implementation will be used?
- What is the agreed command schema and data representation?
- What units and joint limits apply?
- How are commands acknowledged and errors reported?
- What timeout, replay and reset policies are required?
- How are target and actual joint positions measured?
- What position tolerance and acceptance criteria have been approved?
- What evidence format and storage location are required?

## 8. References

- Arduino VENTUNO Q: https://docs.arduino.cc/hardware/ventuno-q
- VENTUNO Q Microcontroller Guide: https://docs.arduino.cc/tutorials/ventuno-q/mcu-examples/
- VENTUNO Q Arduino IDE Guide: https://docs.arduino.cc/tutorials/ventuno-q/arduino-ide/

## 9. Status

Status: Draft — pending project implementation and hardware verification.

No physical STM32H5F5 or SO-101 test result is claimed by this document.
