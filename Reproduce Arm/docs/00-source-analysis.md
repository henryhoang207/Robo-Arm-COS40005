# 00 — Source Analysis

## The video

| | |
|---|---|
| Title | Teaching a Robot to Kidnap Rubber Ducks with AI |
| Channel | Hardware.ai (17.4K subs), in collaboration with Arduino |
| Published | 1 September 2026 · 8:02 · ~2.9K views |
| Licence | Creative Commons Attribution — reuse allowed |
| URL | https://www.youtube.com/watch?v=T0frBNASr3M |

## Stated approach (from the creator's own description)

> "I fine-tune HuggingFace SmolVLA on the pick and place dataset I created
> myself. Then I run the inference on Arduino Ventuno Q — a Qualcomm QCS8275
> board with 40 TOPS NPU — connected to SO-101 robotic arm."

Three layers:

1. **Arm** — SO-101, the LeRobot open-source 6-DOF arm (leader + follower pair,
   Feetech STS3215 serial bus servos).
2. **Policy** — SmolVLA, 450M parameters, fine-tuned on ~50 self-recorded
   pick-and-place demonstrations.
3. **Compute** — Arduino Ventuno Q. Qualcomm Dragonwing IQ8 / QCS8275, octa-core
   Kryo Gen 6, Adreno 623 GPU, Hexagon NPU rated up to 40 dense TOPS, 16 GB
   LPDDR5, 64 GB eMMC, Ubuntu, plus an STM32H5 real-time MCU ("dual brain").

## What is public and what is not

### Public and well-documented — low risk
- SO-101 mechanical design, BOM and print files (TheRobotStudio/SO-ARM100)
- LeRobot: motor setup, calibration, teleoperation, dataset recording, HF Hub
  dataset format, `lerobot-train`, `lerobot-rollout`
- SmolVLA base weights (`lerobot/smolvla_base`) and the documented fine-tune
  recipe
- Ventuno Q hardware specs, Ubuntu image, Arduino App Lab

### NOT public — this is the gap
The creator explicitly writes:

> "Most of inference/lerobot-vla.cpp plugin code is in spaghetti state: I need
> some time and effort to make it publishable, **initially CPU inference**."

Two consequences:

1. **There is no released code for running SmolVLA on this board.** The
   Arduino App Lab plugin that appears in the video does not exist as a
   downloadable artefact at time of writing.
2. **Even his own future release will be CPU-only.** The 40 TOPS NPU is not
   demonstrably being used for the VLA policy. Treat the "40 TOPS" framing as
   marketing context for the board, not as a proven inference path.

### The nearest public substitute

`vla.cpp` — https://github.com/VinRobotics/vla.cpp — a llama.cpp-derived C++
inference engine that runs VLA policies from self-contained GGUF files with no
Python or PyTorch at inference time.

- Supports SmolVLA, π0, π0.5, BitVLA, Evo-1, GR00T, VLA-Adapter, OpenVLA-OFT,
  VLA-JEPA
- Backends: CPU (x86-64 **and ARM**), CUDA, SYCL, Metal
- **No Qualcomm QNN/NPU backend today**

So: ARM CPU inference on the Ventuno Q via `vla.cpp` is a credible, supported
path. NPU offload is not — it would have to be built.

## Implications for your plan

| Claim in the video | Reproducibility | Your move |
|---|---|---|
| SO-101 arm build | High — fully documented | Follow upstream |
| ~50 demos is enough | Medium — HF says 50 is the floor, 25 failed | Record 80–100, subsample |
| SmolVLA fine-tune | High — documented recipe | Follow upstream |
| Runs on Ventuno Q | **Low — no code released** | Ladder: PyTorch CPU → vla.cpp GGUF → QNN |
| Uses 40 TOPS NPU | **Unproven** | Stretch goal; report honestly either way |

## Where the original contribution lies

1. A working, **published** SmolVLA inference path on Qualcomm Dragonwing —
   even CPU-only, this is more than currently exists.
2. Any QNN offload, starting with the SigLIP vision encoder.
3. The networked/IoT layer the video ignores entirely (see doc 06).
