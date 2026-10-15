# 02 — Phase 1: Hardware Build (weeks 1–2)

**Gate:** both arms move under teleoperation, calibration values agree between
leader and follower at matching physical poses.

## References

- Mechanical BOM, print files, assembly: https://github.com/TheRobotStudio/SO-ARM100
- LeRobot SO-101 setup: https://huggingface.co/docs/lerobot/so101

## 1. Print / assemble

Print in PLA or PETG. PETG if your workspace runs warm. Key points:

- Print orientation matters for the shoulder and elbow links — follow upstream
  orientation notes, layer adhesion is the failure mode under load.
- Ream servo horn holes to a snug fit; slop here becomes backlash, and backlash
  becomes noisy training data.
- Assemble the **follower first**. It's the one that must be mechanically sound.

## 2. Install LeRobot with Feetech support

```bash
git clone https://github.com/huggingface/lerobot.git
cd lerobot
pip install -e ".[feetech]"
```

## 3. Identify USB ports

```bash
lerobot-find-port
```

Run once per arm, disconnecting when prompted. Record both port paths — on
Linux they look like `/dev/ttyACM0`, on Windows `COM3`, on macOS
`/dev/tty.usbmodem*`.

**Tip:** create a udev rule pinning each adapter to a stable symlink
(`/dev/so101_leader`, `/dev/so101_follower`) by USB serial number. Port
enumeration order changes between reboots and will silently swap your arms.

## 4. Set motor IDs and baud rates

Motors ship with identical IDs. They must be configured **one at a time**,
connected alone to the bus.

```bash
# Follower
lerobot-setup-motors \
    --robot.type=so101_follower \
    --robot.port=/dev/so101_follower

# Leader
lerobot-setup-motors \
    --teleop.type=so101_leader \
    --teleop.port=/dev/so101_leader
```

## 5. Calibrate

```bash
lerobot-calibrate \
    --robot.type=so101_follower \
    --robot.port=/dev/so101_follower \
    --robot.id=duck_follower

lerobot-calibrate \
    --teleop.type=so101_leader \
    --teleop.port=/dev/so101_leader \
    --teleop.id=duck_leader
```

Calibration makes the two arms report identical joint values at identical
physical positions. This is what makes the recorded data meaningful — if
calibration drifts, your dataset is quietly corrupted and training will
mysteriously underperform.

**Back up the calibration files** (`~/.cache/huggingface/lerobot/calibration/`
or equivalent) into this repo under `calibration/`. Re-calibrate and re-back-up
after any mechanical disassembly.

## 6. Power and safety wiring

- 12 V rail feeds **only** the servo bus. Board/PC power is separate.
- Put the E-stop in the 12 V line, physically reachable without leaning over
  the arm's workspace.
- Set conservative software torque limits before the first autonomous run.

## 7. Bench fixture

The arm base, the cameras, and the task area must be **rigidly fixed relative
to each other** and stay that way from first recording through final evaluation.

If the camera moves 2 cm between data collection and deployment, the policy
degrades and you will waste a week blaming the model.

- Bolt or clamp the arm base to a plate
- Mark the duck-placement positions on the surface with tape
- Mark the camera tripod feet
- Photograph the whole rig as a reference for rebuilding it

## Common failures at this phase

| Symptom | Cause |
|---|---|
| Random servo dropouts | Shared power rail; stall current browning out USB |
| Leader/follower joint mismatch | Calibration not redone after disassembly |
| Gripper won't hold | Wrong gear ratio on motor 6, or over-tight printed jaw |
| Jerky follower motion | Baud rate mismatch, or daisy-chain cable too long |
| Sagging leader arm | Wrong gear ratios ordered (1/345 everywhere instead of variable) |
