# Roadmap

Target: ~10 weeks. Scope: faithful reproduction with on-device inference.

## Phases and gates

| Phase | Weeks | Work | Gate — do not proceed until |
|---|---|---|---|
| **0** | now | Order Ventuno Q **today**. Order arm kit / servos / start prints in parallel. | Parts ordered, lead times recorded |
| **1** | 1–2 | Assemble leader + follower. Motor IDs, calibration, bench fixture, power rail, E-stop. | Both arms teleoperate; calibration values agree |
| **2** | 2–3 | LeRobot on PC. Two cameras. Record 5 throwaway episodes and visualise them. | Full record→visualise pipeline round-trips cleanly |
| **3** | 3–4 | Record 80–100 real episodes across 5 positions. Cull. Push to HF Hub. | Dataset published, 10 episodes reviewed by eye |
| **4** | 4–5 | Fine-tune SmolVLA on rented A100. Closed-loop rollout **from PC**. | Arm picks up the duck autonomously, ≥60% / 20 trials |
| **5** | 5–8 | Port to Ventuno Q: Rung 1 PyTorch CPU → Rung 2 vla.cpp GGUF → Rung 3 QNN vision offload. | Policy runs on-board at usable control rate |
| **6** | 8–10 | MQTT telemetry + dashboard + OTA. Full evaluation matrix. Writeup / video. | Results table complete, including failures |

## Critical path notes

- **Ventuno Q lead time is the only thing that can't be compressed.** Order it
  on day 0. Nothing in Phases 1–4 needs it.
- **Phase 4 is the real milestone.** If the policy works tethered, you have a
  project. Phase 5 upgrades it to a contribution.
- **Do not start Phase 5 before Phase 4 passes.** Debugging a policy and an
  unproven runtime simultaneously is how weeks disappear.
- **Decide on the ACT fallback by end of week 5.** If SmolVLA hasn't converged
  by then, switch — same dataset, working demo, keep the schedule.
- Phase 6 is scoped to be cuttable. If time runs short, ship telemetry + OTA
  and drop the rest.

## Decision log

Record decisions here as you make them — the writeup needs them and you will
forget the reasoning within two weeks.

| Date | Decision | Reasoning |
|---|---|---|
| 2026-09-06 | Ventuno Q fixed, not substituted | Faithful reproduction; the board is the novel element |
| 2026-09-06 | Full on-device scope, not PC-tethered | On-device inference is the point of the video |
| 2026-09-16 | Scope consolidated into `SCOPE.md` (historical reference; file absent from the uploaded repository); deliverables split into minimum / target / stretch | Scope was spread across README, this file and docs 00/05/06, with no stated floor and no out-of-scope list |
| 2026-09-16 | Latency budget adopted as an explicit scope gate: Rung 2 must reach **<1.67 s per chunk** | Stage C measured 4.95 s/chunk (float32, 10 threads) on the dev laptop — 3x over the 50-action chunk duration, on cores unlikely to be slower than the board's Kryo. The 09-06 on-device decision predates this measurement, so the week-7 gate now tests the number, not just "does it run" |
| | | |

## Artefact log

Track what produced what. Essential once you have several checkpoints.

| Date | Artefact | Source | Notes |
|---|---|---|---|
| 2026-09-15 | Stage C laptop CPU latency profile | `lerobot/smolvla_base`, LeRobot 0.6.2 @ `89236ea` | `research/results/stageC-laptop-cpu/` — baseline only, not fine-tuned |
| | dataset commit hash | | |
| | checkpoint / W&B run | trained from dataset ___ | |
| | GGUF conversion | from checkpoint ___ | quant level |
| | | | |

## Weekly log

Keep this short. One entry per week: what moved, what's blocked, what changed.

### Week 0
- [ ] Ventuno Q ordered — lead time: ___
- [ ] Arm parts ordered / prints started
- [ ] LeRobot installed on PC, repo cloned
