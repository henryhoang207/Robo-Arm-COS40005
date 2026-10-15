# Reproduce Arm — SmolVLA on SO-101 + Arduino Ventuno Q

Earlier reproduction notes, reorganized by purpose. The current [project plans](../../../docs/project-management/plans/README.md) and [technical decisions](../../../docs/technical/README.md) should be consulted before reusing this earlier scope or schedule. The originally referenced `SCOPE.md` was not present in the uploaded repository.

Reproduction of **"Teaching a Robot to Kidnap Rubber Ducks with AI"**
(Hardware.ai × Arduino, 1 Sep 2026) — a SO-101 robot arm performing a
pick-and-place task driven by a fine-tuned SmolVLA vision-language-action
model, with inference running on-device on an Arduino Ventuno Q.

- Source video: https://www.youtube.com/watch?v=T0frBNASr3M (CC-BY, reuse allowed)
- Scope decided: **faithful reproduction, on-device inference on Ventuno Q**
- Target duration: ~10 weeks · Budget: ~$800–1,000 USD

## Documents

| File | What's in it |
|---|---|
| [00-source-analysis.md](00-source-analysis.md) | What the video actually does; what is public vs. what you must write yourself |
| [01-bom-and-budget.md](01-bom-and-budget.md) | Bill of materials, sourcing, costs, long-lead items |
| [02-phase1-hardware-build.md](02-phase1-hardware-build.md) | SO-101 assembly, motor setup, calibration |
| [03-phase2-3-data-collection.md](03-phase2-3-data-collection.md) | Teleoperation, camera rig, dataset design and recording |
| [04-phase4-training-smolvla.md](04-phase4-training-smolvla.md) | Fine-tuning SmolVLA, GPU rental, tethered closed-loop test |
| [05-phase5-deployment-ventuno-q.md](05-phase5-deployment-ventuno-q.md) | Porting to the board: CPU → vla.cpp → QNN NPU |
| [06-phase6-iot-layer.md](06-phase6-iot-layer.md) | MQTT telemetry, dashboard, OTA model updates — the original contribution |
| [07-evaluation-protocol.md](07-evaluation-protocol.md) | How to measure success honestly |
| [ROADMAP.md](../../../docs/project-management/reproduce-arm/ROADMAP.md) | Week-by-week schedule with gates |
| [RISKS.md](../../../docs/project-management/reproduce-arm/RISKS.md) | Ranked risks and mitigations |
| [SOURCES.md](../../literature/reproduce-arm-sources.md) | Every link, in one place |
| [Exploratory scripts](../../experiments/reproduce-arm/README.md) | Dataset review and CPU profiling |
| [Laptop CPU profiling results](../../results/stageC-laptop-cpu/README.md) | Original measurements and reproduction command |

## The one thing to internalise

The video's headline — a 450M-parameter VLA running on a 40 TOPS NPU — has
**no public implementation**. The creator states his inference plugin is
unreleased and will be CPU-only when it lands. Everything up to and including
Phase 4 rests on well-documented open-source tooling. Phase 5 is original work.

Plan accordingly: **Phase 4 (policy works, tethered to a PC) is the milestone
that makes this a project.** Phase 5 is what makes it a contribution.

## Status

- [ ] Phase 0 — Parts ordered
- [ ] Phase 1 — Arms built and calibrated
- [ ] Phase 2 — Teleop + cameras working end-to-end
- [ ] Phase 3 — Dataset recorded and published
- [ ] Phase 4 — Policy closes the loop from PC
- [ ] Phase 5 — Policy runs on Ventuno Q
- [ ] Phase 6 — IoT layer, evaluation, writeup
