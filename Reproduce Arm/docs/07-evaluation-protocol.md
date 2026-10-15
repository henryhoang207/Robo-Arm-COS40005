# 07 — Evaluation Protocol

Video demos show the takes that worked. A reproduction is only worth something
if it reports what actually happens.

## Primary metric

**Task success rate** — fraction of trials where the duck ends up in the target
zone, arm returns to a safe pose, no human intervention.

Minimum 20 trials per configuration. 20 trials gives roughly ±11 percentage
points of confidence interval, which is enough to distinguish 40% from 80% but
not 70% from 80%. Say so when you report it.

## Test matrix

Run the same protocol at every rung of Phase 5 so the numbers are comparable.

### A. In-distribution

Duck at each of the training positions, N trials each. This is the number the
video is implicitly showing.

### B. Generalisation — the interesting part

| Test | What it probes |
|---|---|
| Novel position (between training positions) | Spatial interpolation |
| Novel position (outside training envelope) | Extrapolation — expect failure, report it |
| Unseen duck colour | Visual robustness |
| Distractor objects in scene | Attention / grounding |
| Shifted lighting | Overfit to recording conditions |
| Camera nudged 2 cm | Rig sensitivity (this one is sobering) |
| Different language phrasing, same task | Whether the "L" in VLA does anything |

Test B is what separates a real evaluation from a highlight reel. Most
fine-tuned VLAs at this data scale fail most of these. **Report that honestly** —
it's a more interesting finding than a 90% in-distribution number.

### C. Systems metrics (per Phase 5 rung)

| Metric | How |
|---|---|
| Inference latency per chunk | p50 / p95 / p99, not just mean |
| Achievable control rate (Hz) | Measured at the servo write, not at the model |
| Chunk-queue underruns per 100 trials | The number that predicts jerky motion |
| Peak RAM | |
| Board temperature after 30 min continuous | Thermal throttling is real |
| Power draw | Optional, but strengthens the edge-AI argument |

## Failure taxonomy

Don't just count failures — classify them. Categories that will actually occur:

1. **Never grasped** — approach wrong, gripper closed on air
2. **Grasped, dropped** — grip force / angle
3. **Grasped, wrong place** — placement phase failure
4. **Wrong object** — grounding failure (with distractors)
5. **Frozen / no motion** — inference stall, queue underrun
6. **Unsafe motion** — collision, joint limit, needed E-stop
7. **Oscillation** — chunk-blending seam artefact

The distribution across these tells you what to fix. If most failures are type
5 or 7, that's a systems problem and Phase 5 work fixes it. If most are types
1–3, it's a data problem and you need to go back to Phase 3.

## Recording results

Keep `results/` in this repo:

```
results/
  rung1-pytorch-cpu/
    trials.csv          # trial_id, config, position, colour, outcome, failure_type, notes
    latency.csv
    video/              # at least the failures
  rung2-vlacpp-q8/
  rung3-qnn-vision/
```

Log every trial, including the ones you'd rather not. Cherry-picked results are
the thing this project is implicitly critiquing.

## Comparison back to the source

The video reports no numbers at all. So your comparison is necessarily
qualitative on the task, quantitative on the systems side:

- "The source demonstrates the task; we reproduce it at X% success over N
  trials, and additionally report generalisation performance and on-device
  latency, neither of which is available for the original."

That's a fair, defensible framing — and it's a stronger result than matching an
unmeasured demo.
