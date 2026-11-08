# Initial Simulator Selection and Compatibility Rationale

## 1. Decision question

Which simulator should be used for the initial development and validation of the SO-101 robot-arm project, including investigation of robot control, model integration and the intended VENTUNO Q/STM32H5F5 workflow?

## 2. Decision status

**Status:** MuJoCo selected by the project team as the initial simulator; compatibility and integration validation remain ongoing.

**Selected simulator:** MuJoCo 3.15.0.

**Robot model:** SO-101 model from the project's simulation resources.

**Initial recommendation:** ManiSkill with the SO100 robot model was recommended in the original selection assessment. The project subsequently proceeded with MuJoCo for the initial runnable simulation and software validation work.

This decision records the current simulator choice. It does not establish full SO100/SO101 equivalence, successful integration of the final trained AI model, or execution on physical STM32H5F5 hardware.

## 3. Candidates and selection rationale

| Candidate | Potential benefit | Current assessment and outstanding concerns |
|---|---|---|
| ManiSkill with SO100 | Candidate robot model and `svla_so100_pickplace` dataset provide a starting point for investigating robot actions and observations. | The project's required model, action/state conventions, camera mapping and runnable configuration have not been verified by the tests recorded in this report. |
| MuJoCo with SO-101 | Provides a runnable environment for inspecting the SO-101 model and testing joint control, trajectory tracking and software-level communication behaviour. | A local environment using MuJoCo 3.15.0 was launched, and software simulation tests were executed. This does not prove physical hardware integration or complete equivalence with the physical arm. |

The project proceeded with MuJoCo because a runnable SO-101 simulation was available for initial software validation. This provides a practical starting point for examining joint configuration, command handling and simulated motion before hardware integration.

The available evidence supports the feasibility of the tested MuJoCo workflow. It is not a comprehensive benchmark comparing MuJoCo against ManiSkill, and it does not establish that MuJoCo is superior for every project requirement.

## 4. Compatibility assessment

| Area | Current evidence and assessment | Outstanding work |
|---|---|---|
| Simulator runtime | MuJoCo 3.15.0 installed in the `so101_sim` Conda environment using Python 3.11.17. The SO-101 scene was launched successfully. | Record any additional relevant package and model asset revisions needed for full reproducibility. |
| Robot model | The SO-101 model loaded in MuJoCo. Inspection identified six joints and six actuators. | Verify model configuration and calibration against the intended physical SO-101 hardware. |
| Joint control | Software tests exercised six-joint control and rejected an out-of-range shoulder-pan target. | Confirm controller behaviour and command scaling against the actual target hardware interface. |
| Trajectory tracking | A synchronized four-second, six-joint trajectory test passed in simulation. | Define project-approved acceptance thresholds and validate against further representative trajectories. |
| Action and state interface | Prototype binary ActionPacket and StatePacket round-trip tests passed; CRC corruption and unsupported protocol versions were rejected. | Confirm the interface with the actual AI runtime and STM32H5F5 firmware implementation. |
| Fault and sequence handling | Simulation tests exercised stale/replayed sequences, incomplete targets, joint-limit rejection and watchdog timeout behaviour. | Confirm that the intended firmware uses the same rules and fault semantics. |
| Cameras and observations | The current software validation does not establish compatibility with the ManiSkill dataset's top/wrist camera conventions or a final AI checkpoint. | Specify required camera views, image dimensions, colour format, preprocessing and observation mapping when the model is selected. |
| Reset/step and task workflow | The MuJoCo scene was launched and scripted joint-control tests ran. This report does not establish full compatibility with the ManiSkill `svla_so100_pickplace` workflow. | Verify the reset, observation, action and step sequence required by the chosen application. |
| VENTUNO Q / STM32H5F5 | The current end-to-end evidence uses software mocks and a simulated STM32 component. | Verify the actual communication transport, firmware implementation, runtime constraints and board execution. |
| Physical SO-101 equivalence | Not established. | Compare joint order, limits, calibration, gripper conventions and action scaling before physical integration. |

## 5. Validation evidence

The related simulation validation report and test scripts are maintained separately:

- Validation report: [`research/results/SO101-47-simulation-validation/SO101-47-simulation-validation.md`](../../research/results/SO101-47-simulation-validation/SO101-47-simulation-validation.md)
- Test scripts: [`tests/simulation/`](../../tests/simulation/)

The recorded software tests cover model inspection, joint control, trajectory tracking, supervision, binary protocol handling, simulated end-to-end communication and the prototype STM32 interface.

These results support the use of MuJoCo for the tested initial software-validation activities. They must not be interpreted as evidence that the physical STM32H5F5 or physical robot arm has passed testing.

## 6. Trade-offs and risks

- **Practicality:** MuJoCo provides a runnable environment for the project's initial SO-101 software tests.
- **Model compatibility:** The simulation model may differ from the physical arm in calibration, joint limits or gripper conventions.
- **AI integration:** The final checkpoint's action and observation requirements remain to be verified.
- **Hardware integration:** Software mocks and a simulated MCU cannot establish successful board-level communication.
- **Benchmark comparability:** No completed benchmark comparing MuJoCo and ManiSkill is claimed.

Mitigation is to keep simulator validation, AI/model integration and physical-hardware testing as separate evidence stages, with explicit acceptance criteria for each.

## 7. Next steps

1. Preserve the initial ManiSkill SO100 recommendation as part of the decision history.
2. Record the team's MuJoCo selection and the rationale for proceeding with the runnable SO-101 simulation.
3. Keep the current software validation report and scripts linked to this decision.
4. Record the exact robot asset revision and any additional dependencies required to reproduce the environment.
5. Define and verify the selected AI model's action, state and camera mappings.
6. Validate the actual STM32H5F5/VENTUNO Q interface when hardware access is available.
7. Treat benchmark results and physical-arm results as separate deliverables.

## 8. References

- ManiSkill SO100 robot documentation: https://maniskill.readthedocs.io/en/latest/robots/so100/
- LeRobot SO100 pick-and-place dataset: https://huggingface.co/datasets/lerobot/svla_so100_pickplace
- SO-ARM100/SO-ARM101 simulation resources: https://github.com/TheRobotStudio/SO-ARM100/tree/main/Simulation
- MuJoCo documentation: https://mujoco.readthedocs.io/

## 9. Traceability

- **Related Jira issue:** SO101-47
- **Decision owner:** Nguyen
- **Interface support:** Chung
- **Initial assessment date:** 14 October 2026
- **Decision update:** 15 October 2026

This document records the current project direction and the evidence available at the time of update. Any further change to the simulator decision should be documented with its rationale and supporting evidence.
