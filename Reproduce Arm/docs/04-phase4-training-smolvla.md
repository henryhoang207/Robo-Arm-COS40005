# 04 — Phase 4: Fine-tuning SmolVLA (weeks 4–5)

**This is the milestone that makes the project real.** If the policy closes the
loop with the arm tethered to your PC, you have a working result regardless of
how the board port goes.

**Gate:** the arm picks up the duck autonomously, ≥60% success over 20 trials,
running from your PC.

## Reference

https://huggingface.co/docs/lerobot/smolvla

## What SmolVLA is

A 450M-parameter vision-language-action foundation model from HuggingFace.
Inputs: multiple camera views + robot sensorimotor state + a natural-language
instruction. Output: a *chunk* of future actions (~50 steps), not a single step.

Base checkpoint: `lerobot/smolvla_base`

Architecture, roughly: a SigLIP vision encoder + a SmolLM2 language backbone +
a flow-matching action expert. Knowing this split matters later — see doc 05,
where the vision encoder is the natural first candidate for NPU offload.

## Training command

```bash
cd lerobot && lerobot-train \
  --policy.path=lerobot/smolvla_base \
  --dataset.repo_id=${HF_USER}/duck_pick_place \
  --batch_size=64 \
  --steps=20000 \
  --output_dir=outputs/train/duck_smolvla \
  --job_name=duck_smolvla \
  --policy.device=cuda \
  --wandb.enable=true
```

- ~4 hours on a single A100 for 20k steps at batch 64
- On a 24 GB consumer card: drop `--batch_size` to 16–24 and use gradient
  accumulation. Expect 3–4× the wall time.
- **Enable W&B.** You need the loss curves when you're debugging why run 3 is
  worse than run 2.

## Where to rent

| Option | Notes |
|---|---|
| RunPod / Vast.ai | Cheapest per A100-hour, spot interruptions possible — checkpoint often |
| Lightning AI | Easier UX, slightly pricier |
| Colab Pro | Works, but session timeouts vs. a 4 h run is a fight |

Budget $30–60 total across 3–5 runs.

## Evaluating on the real arm — tethered

```bash
lerobot-rollout \
  --strategy.type=base \
  --robot.type=so101_follower \
  --robot.port=/dev/so101_follower \
  --robot.id=duck_follower \
  --policy.path=${HF_USER}/duck_smolvla
```

**The task string at inference must exactly match the training string.**

Run this on your PC with the arm connected by USB. Do not go near the Ventuno Q
until this works.

## Action chunking — understand this before Phase 5

SmolVLA does not emit one action per inference. It emits a **chunk** of ~50
future actions. The control loop plays the chunk back at ~30 Hz while the next
chunk is computed asynchronously.

This is the reason edge inference is viable at all. If inference takes 250 ms
but produces 50 actions covering ~1.7 s of motion, the arm never stalls.

LeRobot supports **Real-Time Chunking (RTC)** specifically for low-power
hardware — it blends the tail of the current chunk with the head of the next so
the seam isn't visible as a jerk. You will need this on the Ventuno Q. Get
familiar with it here, on hardware you can debug easily.

```
inference (async, 3-5 Hz) ──> chunk buffer ──> playback (30 Hz) ──> servo bus
```

## Fallback: ACT

If SmolVLA underperforms or you run out of runway, **ACT** is the pragmatic
fallback — smaller, faster, trains reliably on the same LeRobot dataset. It has
no language conditioning, so you lose the "V-L-A" framing, but you keep a
working demo. Same dataset, different `--policy.path`.

Decide by end of week 5. Don't let a stalled SmolVLA run eat Phase 5's time.

## If it doesn't work

Diagnose in this order — it's ordered by how often each is actually the cause:

1. **Data.** Watch 10 episodes. Are they actually good demonstrations?
2. **Task string mismatch** between training and inference.
3. **Camera drift** — did the rig move since recording?
4. **Calibration drift** — re-run `lerobot-calibrate`, compare to your backup.
5. **Not enough / badly distributed data.** Record more, varying positions.
6. **Undertrained.** Check the loss curve; extend steps.
7. Model/hyperparameters. Almost never the real cause at this stage.

Record what you tried in `ROADMAP.md`. The writeup needs it and you will forget.
