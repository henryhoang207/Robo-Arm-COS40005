# Tests and validation

Keep implementation tests and repeatable validation procedures here.

| Stage | What to verify |
| --- | --- |
| Mocks | App connection/status/error handling, supported control inputs and UI |
| Computer reference | Model inputs, preprocessing and reference outputs |
| Board | Conversion comparison, prediction time, memory and sustained operation |
| Simulation | Action mapping, observation feedback, resets and communication faults |
| Physical SO-101 | Calibration, task execution, timing, stop/reset and recovery |

Record expected behavior, setup, actual outcome and evidence. Agreed test commands, cases and numerical targets: **[TBD TEAM]**.

A passed mock or simulation test does not prove physical-arm behavior.
