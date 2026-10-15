# 01 — Bill of Materials & Budget

## Long-lead items — order these first

| Item | Why urgent |
|---|---|
| **Arduino Ventuno Q** | Recent release, pre-order pricing, shipping time unknown. Order on day 0. |
| **Feetech STS3215 servos ×12** | Frequently backordered; specific gear ratios needed for the leader arm |
| **3D printed parts** | If outsourcing, 1–2 week turnaround. If self-printing, ~40–60 h of print time |

Everything in Phases 1–4 can proceed **without the Ventuno Q**, so board delay
is not a schedule blocker if you order it immediately.

## Compute

| Item | Spec | Cost |
|---|---|---|
| Arduino Ventuno Q | Dragonwing IQ8 / QCS8275, 40 TOPS NPU, 16 GB LPDDR5, 64 GB eMMC, STM32H5 co-MCU, Wi-Fi 6, 2.5 GbE, 3× MIPI CSI | €299 (~$325) |
| microSD / NVMe (optional) | M.2 NVMe Gen4 slot available; useful for model storage | $30 |

Source: https://store.arduino.cc/products/ventuno-q

## Arm — SO-101 (leader + follower)

Reference BOM: https://github.com/TheRobotStudio/SO-ARM100

### Servos — note the gear ratios, they differ per arm

**Follower arm** — 6× STS3215, all **1/345** gear ratio.

**Leader arm** — variable gearing so it self-supports and stays low-force:

| Joint | Motor ID | Gear ratio |
|---|---|---|
| Shoulder pan | 1 | 1/191 |
| Shoulder lift | 2 | 1/345 |
| Elbow flex | 3 | 1/191 |
| Wrist flex | 4 | 1/147 |
| Wrist roll | 5 | 1/147 |
| Gripper | 6 | 1/147 |

Ordering the wrong ratios is the single most common and most expensive BOM
mistake. Double-check before checkout.

| Item | Qty | Cost |
|---|---|---|
| STS3215 servos (correct ratios, 12 V variant) | 12 | $180–300 |
| Waveshare / Feetech serial bus servo driver board (USB-TTL) | 2 | $20 |
| 3D printed structural parts (PLA/PETG), both arms | 1 set | $80–150 outsourced, ~$25 filament self-printed |
| Fasteners / bearings kit | 1 | $20 |

Pre-built kits (ThinkRobotics, Seeed, OpenELAB, Amazon) run $250–450 for the
pair and remove the ratio-mistake risk. Worth it if your time is tight.

## Vision

| Item | Notes | Cost |
|---|---|---|
| USB UVC webcam — fixed overhead/side view | 720p @ 30 fps is plenty; low latency > resolution | $20–30 |
| USB UVC webcam — wrist cam | Small form factor, needs a printed mount | $20–30 |
| (optional) MIPI CSI camera | Native to the board, lower latency, but LeRobot's OpenCVCamera path is USB-first | $25 |

**Start with USB.** LeRobot's `OpenCVCamera` speaks UVC out of the box. Move to
CSI only if you measure a latency problem.

## Power & safety

| Item | Notes | Cost |
|---|---|---|
| 12 V ≥5 A regulated PSU | **Dedicated to the servo bus**, not shared with the board | $20 |
| Inline current meter / fuse | Catches stalls before they cook a servo | $10 |
| Physical E-stop / power kill switch | Non-negotiable once a learned policy is driving | $10 |

Shared power between servos and compute causes brownouts on stall current
spikes, which present as random USB disconnects. Budget the separate rail.

## Compute for training

| Item | Notes | Cost |
|---|---|---|
| Rented A100 (RunPod / Lightning / Vast) | ~4 h per 20k-step run, expect 3–5 runs | $30–60 total |
| Alternative: Colab Pro | Slower, session timeouts, workable | $10/mo |

Do **not** plan to train locally unless you have ≥24 GB VRAM.

## Miscellaneous

Cables (USB-A/C, servo daisy-chain), bench mounting plate or clamps, rubber
ducks (≥5, varied colours for generalisation testing), matte backdrop,
consistent lighting (2× cheap LED panels) — ~$50–70.

Consistent lighting is not optional. It is the cheapest thing you can buy that
materially improves policy success rate.

## Total

| Line | Low | High |
|---|---|---|
| Ventuno Q | $325 | $355 |
| Arm (kit or parts) | $250 | $450 |
| Cameras | $40 | $60 |
| Power & safety | $40 | $40 |
| GPU rental | $30 | $60 |
| Misc + lighting | $50 | $70 |
| **Total** | **~$735** | **~$1,035** |
