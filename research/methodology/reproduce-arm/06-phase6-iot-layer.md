# 06 — Phase 6: IoT Layer (weeks 8–10)

The video ignores connectivity entirely. The Ventuno Q has Wi-Fi 6, Bluetooth
5.3 and 2.5 GbE sitting completely idle.

**This is where the project stops being a re-shoot and becomes yours.** For a
Capsule Project it is also the part most legible as engineering contribution
rather than tutorial-following.

## What to build

### 1. Telemetry over MQTT

Publish from the board, subscribe from anywhere.

| Topic | Payload | Rate |
|---|---|---|
| `arm/state/joints` | 6 joint positions + velocities | 10 Hz (downsampled from 30) |
| `arm/inference/latency` | per-chunk ms, backend, quant level | per chunk |
| `arm/inference/health` | queue depth, underrun count, thermals | 1 Hz |
| `arm/episode/result` | success/fail, duration, task string, trial id | per episode |
| `arm/status` | online/offline (MQTT LWT) | on change |

Use QoS 0 for high-rate state, QoS 1 for episode results. Set a Last Will and
Testament so a crashed board shows as offline rather than silently stale.

Broker: Mosquitto on the board itself for a self-contained demo, or a
cloud/LAN broker if you want off-site monitoring.

### 2. Dashboard

A single page showing:

- Live joint positions (small multiples, one sparkline per joint)
- Inference latency **distribution**, not just the mean — the tail is what
  causes underruns
- Rolling success rate over the last N trials
- Chunk-queue depth over time (the clearest early-warning signal for stalls)
- Board thermals / CPU / NPU utilisation
- Live camera stream (WebRTC or MJPEG; MJPEG is fine and much simpler)

Keep it honest: show failures as prominently as successes.

### 3. OTA model update — the strongest feature

Push a new policy without touching the board:

1. New checkpoint trained → converted to GGUF → uploaded to a model registry
   (HF Hub works fine as the registry)
2. Board polls or receives an MQTT command with a version + checksum
3. Downloads to a staging path, verifies checksum
4. **Hot-swap:** load the new model, run a smoke inference, atomically switch
   the pointer used by the inference thread, keep the old model in memory
5. Automatic rollback if the smoke test fails or success rate drops below a
   threshold over the next N trials

16 GB of RAM makes holding two 450M models simultaneously trivial, so
zero-downtime swap is genuinely achievable. This is a real MLOps story on an
edge device, and almost nobody in the hobby-robotics space actually does it.

### 4. Remote operation

- Remote teleoperation over the network (leader arm on one machine, follower on
  the board) — tests latency tolerance and is a good demo
- Remote episode trigger: publish a task string, board runs one autonomous trial
  and reports the result
- Remote E-stop over MQTT — **with the hard-wired physical E-stop still in
  place.** A network kill switch is a convenience, never a safety device.

### 5. Data flywheel (nice-to-have)

Failed autonomous episodes are the most valuable training data you can get.

- On failure, upload the episode (frames + states) to storage
- Periodically review, correct via teleop, append to the dataset
- Retrain, push OTA, measure

If you get this loop closed even once end-to-end, that's the headline result of
the whole project.

## Safety — read before wiring any of this

| Layer | Mechanism |
|---|---|
| Mechanical | Physical E-stop in the 12 V servo rail, always reachable |
| Firmware | Software joint limits + torque caps, set conservatively |
| Control | Watchdog on chunk-queue underrun → hold position or zero torque |
| Network | Remote commands **authenticated**; MQTT over TLS if off-LAN |
| Policy | Confidence/anomaly check — refuse to execute wildly out-of-distribution chunks |

A learned policy has never seen your bench edge and will drive into it happily.
Never rely on the network path for safety.

## Suggested stack

- **MQTT:** Mosquitto (broker) + paho-mqtt (Python) or Eclipse Paho C
- **Metrics:** Prometheus + Grafana if you want it off the shelf; a small
  FastAPI + WebSocket + plain-JS page if you want it self-contained and fast
- **Video:** MJPEG over HTTP to start. WebRTC only if you need sub-200 ms.
- **OTA:** HF Hub as registry + a systemd-managed updater service
- **Config:** everything in one TOML/YAML file, versioned in this repo

## Scoping note

This whole doc is optional relative to reproducing the video. Pick the two items
with the best effort-to-story ratio and do them properly rather than doing all
five badly. If forced to choose: **telemetry + OTA**. They're the two that
demonstrate systems engineering rather than integration.
