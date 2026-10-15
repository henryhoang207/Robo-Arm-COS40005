# 05 — Phase 5: Deployment on Arduino Ventuno Q (weeks 5–8)

**The hard part. There is no public code for this.** The video's creator has
not released his inference plugin and says it will be CPU-only when he does.

Approach it as a ladder. Each rung is independently a result worth reporting.

**Gate:** the policy runs on-board and closes the loop on the arm at a usable
control rate.

## The board

| | |
|---|---|
| MPU | Qualcomm Dragonwing IQ8 / QCS8275 — octa-core Kryo Gen 6, Adreno 623 GPU, Hexagon Tensor NPU |
| NPU | up to 40 dense TOPS |
| Memory | 16 GB LPDDR5 · 64 GB eMMC · M.2 NVMe Gen4 |
| MCU | STM32H5, real-time co-processor ("dual brain") |
| I/O | 3× MIPI CSI, 2× USB 3.0 A, USB-C w/ video, Wi-Fi 6, BT 5.3, 2.5 GbE |
| OS | Ubuntu (Debian promised) |
| Software | Arduino App Lab preloaded, Docker, curated models (Qwen, Gemma, Whisper, detectors) |

16 GB of RAM means a 450M model in fp16 (~900 MB) is not remotely memory-bound.
This is a compute and latency problem, not a capacity problem.

## Rung 1 — PyTorch CPU on the board

**Goal: prove the loop closes at any speed.** Ugly is fine.

- Install LeRobot + PyTorch (ARM64 CPU build) on the Ubuntu image
- Connect follower arm via the USB servo adapter, cameras via USB
- Run `lerobot-rollout` with `--policy.device=cpu`
- **Measure and record: inference latency per chunk, achievable Hz, RAM, thermals**

Likely outcome: something in the 0.5–3 Hz range. Probably too slow for smooth
motion, but with action chunking + RTC it may already be usable. Either way you
now have a baseline number, which every later rung is measured against.

Deliverable: a latency table. This alone is publishable information that does
not currently exist.

## Rung 2 — vla.cpp, GGUF, ARM CPU

**This is the realistic target.**

https://github.com/VinRobotics/vla.cpp — a C++ inference engine built on
llama.cpp that runs VLA policies as self-contained GGUF files, no Python or
PyTorch at inference time. Supports SmolVLA. Backends include CPU on **ARM**.

Steps:

1. Convert your fine-tuned SmolVLA checkpoint to GGUF using the repo's
   conversion scripts
2. Cross-compile or natively build `vla.cpp` on the board's ARM64 Ubuntu
3. Benchmark: fp16 vs Q8_0 vs Q4_K_M quantisation — latency vs. task success
   rate. **Quantisation that helps latency but tanks success rate is not a win**,
   and you should report both axes.
4. Write the bridge: `vla.cpp` inference → chunk buffer → LeRobot's Feetech
   servo bus driver. This is the glue the creator called "spaghetti."

Expect a meaningful speedup over Rung 1 — llama.cpp's ARM NEON kernels are well
optimised. This is where the project most likely lands.

## Rung 3 — Qualcomm NPU offload (stretch goal)

`vla.cpp` has **no QNN backend**. Nothing off the shelf does this.

Realistic scoping — do not try to offload the whole model:

**3a. Vision encoder first.** SigLIP is a plain ViT: static shapes, no
autoregressive loop, largest single FLOP contributor. It is by far the most
tractable QNN target.

- Export SigLIP to ONNX
- Convert via Qualcomm AI Hub / QNN SDK to a context binary
- Run vision on the NPU, language + action expert on CPU
- Measure the split

**3b. Language backbone.** Harder — KV cache and dynamic sequence length fight
the static-shape NPU model. Possible, not week-8 work.

**3c. Action expert.** Flow-matching involves an iterative denoising loop.
Hardest. Do not start here.

Alternative middle path: **ONNX Runtime with the QNN execution provider**, which
falls back to CPU for unsupported ops. Less performance ceiling, far less work,
and it will tell you quickly which ops the NPU actually accepts.

**Honest framing:** if you get 3a working and can report "vision encoder on NPU
gave Nx speedup on that stage, end-to-end control rate went from A to B Hz,"
that is a genuine, novel, publishable contribution. If you don't get it working,
report the specific ops that blocked you — that's useful too.

## The dual-brain question

Where does the servo bus driver live?

| Option | Pros | Cons |
|---|---|---|
| **USB servo adapter → Linux side** | What LeRobot supports today. Zero new code. | Linux scheduler jitter in the 30 Hz playback loop |
| STM32H5 UART → servo bus | Hard real-time playback, jitter-free | Must write MCU firmware + a Linux↔MCU chunk-transfer protocol |

**Start with USB.** Only move to the STM32H5 if you *measure* jitter that
degrades task success. If you do move, the design is clean: Linux computes
chunks and ships them over the internal bridge; the STM32H5 owns interpolation
and the 30 Hz servo write loop. That's also a nice thing to write about.

## Control-loop architecture to aim for

```
 cameras ─┐
          ├─> [ inference thread, 3-10 Hz ] ──> chunk queue ──┐
 joint  ──┘                                                   │
 states                                                       v
                                    [ playback loop, 30 Hz, RTC blending ]
                                                              │
                                                              v
                                                    Feetech STS3215 bus
```

Non-negotiables:
- Inference must be **asynchronous**. Never block playback on the model.
- Watchdog: if the chunk queue underruns for >N ms, hold position or zero torque.
  Do not let the arm continue on a stale chunk.
- Log every chunk's latency. You need the distribution, not just the mean.

## What to record throughout

Keep a table in this repo:

| Rung | Backend | Quant | Latency/chunk | Control Hz | Success rate | RAM | Notes |
|---|---|---|---|---|---|---|---|
| 1 | PyTorch CPU | fp32 | | | | | |
| 2 | vla.cpp CPU | fp16 | | | | | |
| 2 | vla.cpp CPU | Q8_0 | | | | | |
| 2 | vla.cpp CPU | Q4_K_M | | | | | |
| 3a | QNN vision + CPU rest | | | | | | |

**Success rate must be in this table.** A latency-only comparison is how people
accidentally ship a fast policy that doesn't work.
