# 03 — Phases 2–3: Teleoperation & Dataset Collection (weeks 2–4)

**This is where reproductions fail.** Not at the model, not at the board — at
the data. Budget real time here.

**Gate (Phase 2):** teleop + 2 camera streams recording in sync; a throwaway
5-episode dataset visualises correctly on the Hub.
**Gate (Phase 3):** 80–100 clean episodes published, no dropped frames.

## Reference

https://huggingface.co/docs/lerobot/il_robots

## 1. Camera rig

Two views, minimum:

| View | Purpose | Placement |
|---|---|---|
| Fixed third-person | Global scene context, where the duck is | Overhead-ish 45°, whole workspace + arm in frame |
| Wrist | Fine alignment during the grasp | On the gripper, looking down the approach axis |

Third-person alone makes grasps imprecise. Wrist alone makes the policy unable
to find the object. You want both.

Settings: 640×480 @ 30 fps is sufficient and keeps bandwidth low. **Disable
autofocus, auto-exposure and auto-white-balance** on both cameras — a policy
trained on auto-exposed frames breaks when the lighting shifts.

## 2. Validate the pipeline before committing to a real dataset

Record 5 throwaway episodes. Then:

- Visualise the dataset (LeRobot's dataset viewer / HF Hub dataset page)
- Confirm both camera streams are present, aligned, and not dropping frames
- Confirm joint states move smoothly with no discontinuities
- Confirm the task string is attached

Only once this round-trips cleanly do you record the real thing. Discovering a
camera desync after 80 episodes costs you the whole batch.

## 3. Dataset design — structure beats volume

HuggingFace's own SmolVLA documentation states ~50 episodes is the **minimum**,
and that **25 episodes proved insufficient** in their testing.

Recommended structure — vary the thing you want the policy to generalise over:

```
5 duck positions × 16 episodes each = 80 episodes
```

Plus, if you want the language conditioning to do anything, vary the target:

```
3 duck colours × 4 positions × 7 episodes = 84 episodes
task string: "pick up the {colour} duck and place it in the bin"
```

**Do not** record 80 repeats of the identical pose. The policy will memorise a
trajectory and fail the moment anything moves — which is exactly the failure the
video's demo is designed to hide.

### Rules while recording

- **Identical task string every episode.** Inference must use the same string.
  A typo splits your dataset.
- One continuous smooth demonstration per episode. No hesitation, no
  corrections mid-episode.
- If you fumble an episode, **delete it**. Bad demos are worse than fewer demos.
- Keep episode length consistent (±20%).
- Take breaks. Operator fatigue shows up as degraded data in the last third of
  a session, and you can't see it until training.
- Re-check lighting between sessions. Record all sessions at the same time of
  day if there's any daylight in the room.

## 4. Recording command

```bash
lerobot-record \
  --robot.type=so101_follower \
  --robot.port=/dev/so101_follower \
  --robot.id=duck_follower \
  --teleop.type=so101_leader \
  --teleop.port=/dev/so101_leader \
  --teleop.id=duck_leader \
  --dataset.repo_id=${HF_USER}/duck_pick_place \
  --dataset.num_episodes=80 \
  --dataset.single_task="pick up the rubber duck and place it in the bin"
```

Camera configuration is passed via `--robot.cameras=...`; check the current
LeRobot docs for the exact syntax, it has changed between versions.

## 5. Publish

Push to the HF Hub. Benefits: free versioned backup, the dataset viewer for QA,
and reproducibility for your writeup. Record the dataset commit hash in
`ROADMAP.md` so you know which data produced which checkpoint.

## 6. Quality checklist before training

- [ ] ≥80 episodes retained after culling
- [ ] Every episode has both camera streams, full length
- [ ] Task string byte-identical across all episodes
- [ ] Positions/variations distributed as designed, not clustered
- [ ] Dataset visualised end-to-end, at least 10 episodes watched by eye
- [ ] Calibration unchanged for the whole recording campaign
- [ ] Rig photographed; camera positions marked

## Budget

Expect 2–3 days of recording, and expect to throw away your first batch. Plan
for it rather than being surprised by it.
