# Initial Simulator Selection and Compatibility Rationale

## 1. Decision question

Which simulator should be adopted for the initial development stage of the COS40005 robot-arm project to investigate the integration of a trained robot model with VENTUNO Q and a simulated robot arm?

## 2. Decision status

**Status:** Initial recommendation — pending runnable validation and team confirmation.

**Recommended candidate:** ManiSkill with the SO100 robot model as a simulation reference.

This recommendation supports the initial simulator-selection milestone. It does not establish that the simulator is runnable in the current development environment or that the simulated SO100 is fully equivalent to the project's physical SO-101 arm.

## 3. Options considered

| Option | Potential benefit | Outstanding concern |
|---|---|---|
| ManiSkill with SO100 | Candidate robot model and pick-and-place dataset may support initial investigation of robot actions and observations. | Compatibility with the selected model checkpoint, camera setup and physical SO-101 remains to be verified. |
| Other simulator candidates | May provide alternative robot models or integration workflows. | Comparative evaluation and compatibility evidence are not yet complete. |

## 4. Selection rationale

ManiSkill with SO100 is recommended as the initial candidate because the available SO100 robot documentation and `svla_so100_pickplace` dataset provide a concrete starting point for investigating robot state, action conventions and a bounded pick-and-place task.

The candidate can be evaluated against the project's planned workflow:

1. Obtain and inspect a suitable trained model.
2. Run the model on the intended compute platform, subject to hardware and software compatibility checks.
3. Exchange observations and actions between the model runtime and a computer-hosted simulator.
4. Evaluate whether the simulator exposes the observations and accepts the actions required by the selected model.

The simulator selection remains provisional until a runnable configuration and a compatible observation/action mapping are demonstrated.

## 5. Compatibility assessment

| Area | Current assessment | Required follow-up |
|---|---|---|
| Robot model | SO100 is the initial simulation reference. | Compare its joint configuration and control conventions with the target SO-101 setup. |
| Actions and states | The dataset and robot documentation provide starting points for investigation. | Verify action dimensions, joint ordering, units, ranges and state fields against the selected checkpoint. |
| Cameras | Required camera mapping has not been verified. | Confirm camera names, viewpoints, image dimensions, colour format and preprocessing requirements. |
| Simulation control | Runnable reset/step behaviour has not yet been demonstrated in the project environment. | Build a minimal environment and verify reset, observation retrieval, action submission and step execution. |
| Model and hardware integration | Compatibility with the final checkpoint and VENTUNO Q runtime remains unverified. | Confirm model requirements, dependencies, runtime support and the intended communication interface. |
| Physical SO-101 equivalence | Not established. | Validate joint mapping, limits, action scaling and relevant hardware differences before physical integration. |

## 6. Trade-offs and risks

- **Benefit:** provides a concrete candidate for the initial simulation and model-integration investigation.
- **Trade-off:** the team may need additional mapping or adaptation work before the simulated robot can represent the physical SO-101.
- **Risk:** dataset conventions may not match the selected checkpoint, simulator controller or hardware interface.
- **Mitigation:** record the exact software versions and validate the smallest runnable simulation before proceeding to the benchmark pilot.

## 7. Next steps

1. Confirm the simulator choice with the project team.
2. Record the actual simulator, robot asset and dependency versions used.
3. Implement and run a minimal reset/step test.
4. Verify observation and action mappings for the selected model.
5. Record benchmark inputs, expected outputs, acceptance criteria and evidence separately.

## 8. References

- ManiSkill SO100 robot documentation: https://maniskill.readthedocs.io/en/latest/robots/so100/
- LeRobot SO100 pick-and-place dataset: https://huggingface.co/datasets/lerobot/svla_so100_pickplace
- SO-ARM100/SO-ARM101 simulation resources: https://github.com/TheRobotStudio/SO-ARM100/tree/main/Simulation

## 9. Traceability

- **Related Jira issue:** https://huu-hoan-hoang.atlassian.net/issues?jql=assignee%20%3D%20currentUser()%20AND%20statusCategory%20!%3D%20done%20AND%20due%20%3C%3D%202026-10-14%20AND%20due%20%3E%3D%202026-10-07&atlOrigin=eyJpIjoiMGY2YmFhNzViYzgwNGVmNGI2YzZmOWY1ZmVlYjE4OTkiLCJwIjoicG9zdE9mZmljZSJ9&selectedIssue=SO101-47
- **Current delivery owner:** Chung (sole Project A IoT member, updated 21 October 2026)
- **Interface responsibility:** Chung
- **Last updated:** 21 October 2026
- **Acknowledgment:** Nguyen contributed during the earlier project phase; historical contribution records remain preserved.
