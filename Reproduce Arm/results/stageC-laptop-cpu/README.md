# Stage C — SmolVLA inference on the development laptop CPU

Measured 2026-09-15 with `scripts/profile_smolvla.py`. This is **not** the Ventuno Q: it is the baseline
every later rung (board CPU, vla.cpp, QNN) is compared against.

## Setup

| | |
|---|---|
| CPU | Intel i5-1235U (2 P-cores + 8 E-cores, 12 threads), AVX2 + AVX-VNNI, **no AVX512_BF16 / AMX** |
| Environment | WSL2 Ubuntu 24.04, 7.6 GB visible RAM, PyTorch 2.11.0+cpu (MKL, AVX2) |
| LeRobot | 0.6.2, commit `89236ea0f4f81a81ca566081e20dd1ff5f823cbe` |
| Policy | `lerobot/smolvla_base` (450M params), **not fine-tuned** — latency is valid, actions are not |
| Inputs | `lerobot/svla_so101_pickplace`, 2 cameras renamed `up→camera1`, `side→camera2`, 6-D state |
| Model config | chunk 50 actions, 10 denoising steps, images resized/padded to 512×512, 16 VLM layers |
| Protocol | 2 warm-up + 5 timed chunks, samples spread across the dataset, p50/p95 over the 5 |

## Results (one action chunk, end to end)

| Weights | Threads | p50 | p95 | Vision (2 cams) | VLM prefix | Expert (10 steps) | Peak RSS |
|---|---|---|---|---|---|---|---|
| bfloat16 (checkpoint default) | 6 | 19.75 s | 20.27 s | 13.60 s | 2.03 s | 4.14 s | 3.4 GB |
| float32 | 4 | 6.25 s | 6.64 s | 3.96 s | 0.56 s | 1.57 s | 3.4 GB |
| float32 | 6 | 6.11 s | 7.43 s | 4.10 s | 0.55 s | 1.47 s | 3.4 GB |
| **float32** | **10** | **4.95 s** | **5.95 s** | **2.93 s (59%)** | **0.46 s (9%)** | **1.41 s (29%)** | 3.4 GB |

Pre/post-processing and image resizing are negligible (under 5 ms). Raw data: `profile_*.json`.

## Findings

1. **bfloat16 is 3.2× slower than float32 on this CPU**, because it has no bfloat16 instructions. The
   checkpoint loads in bfloat16 by default; cast to float32 (`--dtype float32`). Predicted actions matched
   between the two dtypes to within 0.3 units. Measure both dtypes again on the Ventuno Q's ARM cores.
2. **The vision encoder is the largest stage** (59–69%, about 1.5–2 s per camera at 512×512). This supports
   doc 05's choice of vision as the first NPU offload target.
3. **The action expert is second (24–29%), not the language backbone (9%).** Doc 05 ranks the backbone as the
   next offload target and the expert as hardest; by cost, the expert's 10 denoising steps matter more.
4. **Threads scale poorly**: 4 → 10 threads is only 1.26× faster, likely memory bandwidth and slow E-cores.
5. **Not usable for closed-loop control at this speed.** One chunk is 50 actions = 1.67 s of motion at 30 Hz;
   at 4.95 s per chunk the arm would wait about 3.3 s for every 1.67 s of motion. Asynchronous chunking only
   removes stalls once end-to-end latency is below the chunk duration, and blending (RTC) needs margin below
   that. The on-board target is therefore **well under 1.67 s per chunk: at least 3× faster than this laptop**.
   Doc 05's Rung 1 guess of "0.5–3 Hz" is optimistic by this measurement (this laptop: 0.2 Hz).

## Levers to evaluate on the board

- Quantisation (vla.cpp Q8_0 / Q4_K_M) — report task success alongside latency
- Vision encoder on the NPU (largest stage)
- Fewer denoising steps (`num_steps`) — trades accuracy for expert time
- Camera count (vision cost is per camera)

## Caveats

Laptop under WSL with no CPU pinning, so p95 varies with thermals and background load; 5 timed runs only.
Image resolution is fixed by the pretrained model and was not varied.

## Reproduce

```bash
source ~/venvs/lerobot/bin/activate
python scripts/profile_smolvla.py --dtype float32 --threads 10 --runs 5 --warmup 2 --out results/stageC-laptop-cpu/profile_float32_threads10.json
```
