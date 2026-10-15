# Risks

Ranked by expected cost to the project.

## 1. No published inference code for the board — HIGH

The video's creator has not released the `lerobot-vla.cpp` plugin, describes it
as unpublishable in its current state, and says the first release will be
**CPU-only**. There is no reference implementation for running SmolVLA on
Dragonwing hardware, and `vla.cpp` has no Qualcomm QNN backend.

**Impact:** Phase 5 is original engineering, not integration. Could consume the
entire remaining schedule.

**Mitigation**
- Define success as **Rung 2 (vla.cpp on ARM CPU)**, not NPU offload
- Treat QNN as an explicit stretch goal with its own go/no-go at week 7
- Publish the latency table even if only Rung 1 works — that data doesn't exist
  publicly today
- Watch the creator's repo; if the plugin lands mid-project, use it and pivot
  your contribution to the IoT layer + evaluation

## 2. Dataset quality — HIGH

The most common cause of failed imitation-learning reproductions. HF's own docs
report 25 episodes was insufficient; 50 is a floor, not a target. Bad
demonstrations are worse than fewer demonstrations, and the damage is invisible
until training.

**Impact:** a full re-record cycle, ~1 week.

**Mitigation**
- Validate the pipeline on 5 throwaway episodes before recording 80
- Record 80–100 so you can cull aggressively and still have enough
- Vary positions/colours deliberately; never repeat one pose 80 times
- Watch ≥10 episodes back before training
- Fix the rig physically and photograph it

## 3. Ventuno Q software maturity and lead time — MEDIUM-HIGH

The board is recent. Thin documentation, unstable toolchain, small community,
and unknown shipping time are all plausible.

**Impact:** weeks of yak-shaving on ARM64 PyTorch builds, camera drivers, or
QNN SDK setup.

**Mitigation**
- Order on day 0 so lead time overlaps Phases 1–4
- Budget a full week for "get the board into a usable Linux state" before any
  ML work
- Prefer Docker (preloaded on the board) to fighting the host environment
- Keep the PC-tethered path working as a permanent fallback demo

## 4. Mechanical: backlash and calibration drift — MEDIUM

Printed joints develop slop. Calibration drifts after any disassembly. Both
degrade data quality silently and are easy to misdiagnose as model problems.

**Mitigation**
- Ream horn holes for snug fits during assembly
- Back up calibration files into the repo; re-calibrate and re-back-up after
  any mechanical work
- Re-verify calibration between recording sessions
- If success rate drops unexpectedly, check mechanics *before* touching the model

## 5. Rig fragility — MEDIUM

Moving a camera 2 cm between data collection and deployment measurably degrades
policy performance. Very easy to do accidentally.

**Mitigation:** rigid mounting, taped floor marks for tripods and duck
positions, photograph the rig, include a "camera nudged" test in evaluation so
you at least quantify the sensitivity.

## 6. Wrong servo gear ratios ordered — MEDIUM (but cheap to avoid)

The leader arm uses **variable** gearing (1/191, 1/345, 1/191, 1/147, 1/147,
1/147); the follower is all 1/345. Ordering 12× 1/345 gives you a leader arm
that sags and is exhausting to teleoperate — and it ruins your data.

**Mitigation:** triple-check before checkout, or buy a matched kit.

## 7. Power brownouts — LOW-MEDIUM

Servo stall current on a shared rail causes USB disconnects that look like
software bugs.

**Mitigation:** dedicated 12 V ≥5 A rail for servos from the start. $20 and one
hour saves a lost day.

## 8. Schedule compression from a stalled SmolVLA run — LOW-MEDIUM

**Mitigation:** hard decision point at end of week 5 — switch to ACT if the
policy hasn't converged. Same dataset, working demo, schedule preserved.

## Go/no-go checkpoints

| Week | Decision |
|---|---|
| 5 | SmolVLA converged? If no → switch to ACT |
| 6 | Board in usable state? If no → escalate, consider PC-tethered as final scope |
| 7 | Rung 2 (vla.cpp CPU) working? If no → drop Rung 3 entirely, spend time on IoT + evaluation |
| 8 | Attempt QNN vision offload only if Rung 2 is solid and ≥2 weeks remain |
