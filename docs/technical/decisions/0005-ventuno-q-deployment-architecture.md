# 0002 — VENTUNO Q runtime, precision profiles and resource-test plan (SO101-34)

Date: 2026-10-14
Status: Approved (decision owner Hoan, 2026-10-14, in chat: AP-1, AP-2, AP-3 and DR-1 option a). Board evidence pending.

Amended on 25 October 2026 by [decision 0006](0006-model-roster-baseline-and-profile-allocation.md): the active roster is SmolVLA, Pi0 and X-VLA; ACT and Diffusion Policy are retired from active experiments. Architecture-specific runtime paths, coverage calculations and noise recipes below remain historical findings for the original models and do not prove Pi0/X-VLA compatibility. General evidence/reporting rules and approved compute placement remain in force; replacement-model recipes and native support require their own evidence. Current nine-profile comparison dates are 1–19 November 2026.
Decision: Score all nine cells (SmolVLA, ACT, Diffusion Policy × FP16, INT8, INT4) on the VENTUNO Q Kryo CPU, with one runtime per model across its three precisions (ExecuTorch + XNNPACK primary; vla.cpp and ONNX Runtime CPU fallbacks; SmolVLA dual-track). Use the disclosed mixed-precision profiles in §2, the measurement plan in §3, and 4-bit-Linear + 8-bit-conv for Diffusion Policy INT4. OpenVLA stays a desk-checked reserve.
Rationale: Only the CPU route has documented FP16, INT8 and 4-bit-Linear execution paths that apply to all three architectures on ARM64 Linux [5][6][7]; the NPU route has board-specific gaps [3][4][8]. Details in §4.
Alternatives rejected: NPU-first via QAIRT; vla.cpp only; ONNX Runtime only; PyTorch eager + torchao (§4).
Verified by: Not yet verified. This is approval only. Board verification is pending the E3 probes (15–16 Oct) and the E4 probes (26–29 Oct).

- **Decision owner:** Hoan (SO101-34 assignee). **Technical evidence:** Duc. **Board/MCU support:** Chung.
- **Prepared by:** Claude. Claude advises and does not decide.
- **Condensed report:** `docs/technical/reports/SO101-34_Runtime_Precision_Condensed_Report_2026-10-14.docx`.
- **Calculations:** `research/methodology/calcs/so101-34_param_split.py`.
- **Approved assumptions:** A-001 to A-003 in `docs/technical/assumptions.md`.
- **Evidence labels:**
  - **[V]** Verified: read this session (14 Oct 2026).
  - **[M]** From memory: Hoan must check.
  - **[R]** Reasoning: Claude's own derivation.

---

## 1. Approved items

| ID | Approved content | Confidence |
|---|---|---|
| D1 (AP-1) | **Placement:** all nine scored cells run on the Kryo CPU (Linux side). NPU and GPU runs are exploratory, separately labelled deployment profiles, started only after the nine CPU cells exist. | Medium |
| D2 (AP-1) | **Runtimes:**<br>• **ACT:** ExecuTorch + XNNPACK → vla.cpp → ONNX Runtime CPU.<br>• **DP:** ExecuTorch + XNNPACK → ONNX Runtime CPU. Export the encoders and one U-Net step; run the DDPM loop in host code at FP32.<br>• **SmolVLA:** probe ExecuTorch + XNNPACK and vla.cpp in parallel; keep the one that passes the gate with wider quantized coverage; ONNX Runtime CPU is third.<br>• **Reference:** PyTorch FP32 on the board, used for same-input comparison and not scored. | Medium |
| D3 (AP-2) | **Precision profiles:** see §2. INT8 and INT4 share eligible modules and exceptions. | Medium |
| D4 (DR-1 a) | **DP INT4:** 4-bit Linear weights with 8-bit convolutions, disclosed with its coverage (about 4% of weights at 4 bits). It is never presented as 4-bit convolution. | High (coverage) |
| D5 (AP-3) | **Measurement:** see §3. FP32 export parity is the only hard quality gate; fidelity is reported, not gated. | High (definitions) |
| D6 (finding) | **OpenVLA:** no FP16 profile fits the 16 GB board, so it is not a drop-in fallback for a full model row. | High |

**Runtime gate** (base weights by 16 Oct; frozen checkpoints 26–29 Oct). For each model, all of these must hold, or the failure is recorded as an evidenced blocker:
1. FP32 export matches PyTorch FP32 at atol = rtol = 1e-3 in normalized action space [9].
2. FP16, INT8 and INT4 artifacts load and run on the board, and the delegation or tensor-type report shows native kernels.
3. Latency, memory and size are logged.
4. No NaN or Inf appears.

If every runtime fails for a model, record an evidenced blocker and take a scope decision. No cell is completed on paper [2].

## 2. Precision profiles (AP-2)

| Profile | Linear layers | Convolutions | Exceptions and disclosure |
|---|---|---|---|
| FP16 | FP16 weights and activations | FP16 | Non-delegated ops run on portable kernels in the dtype recorded per op. FP32 islands, such as normalization statistics and sampler/scheduler maths, are listed. The vla.cpp variant is labelled W16A32 [6]. |
| INT8-mixed | 8-bit per-channel symmetric weights; 8-bit dynamic per-token activations | 8-bit per-channel weights; static 8-bit activations calibrated on training/validation frames only | Embeddings, norms, softmax and validation-chosen sensitive layers stay FP16/FP32. The list is identical in INT4. |
| INT4-mixed | 4-bit group-wise (group 32) symmetric weights; 8-bit dynamic activations | 8-bit, as INT8 (declared exception) | As INT8 |

Each cell discloses:
- the parameter share at each bit width;
- the activation dtype per op type;
- the calibration sample IDs;
- the packing format and the dequantization point;
- which ops are delegated and which are portable;
- the artifact SHA-256 [1][2].

### Coverage [R]
Source: `research/methodology/calcs/so101-34_param_split.py`, using LeRobot 0.6.2 module definitions [12].

- **SmolVLA:** 450.0 M parameters [13]. Mostly Linear layers, with a patch-embedding convolution.
- **ACT inference graph:** 34.2 M parameters, of which 66.4% are Linear and 33.4% convolution. The training-only VAE encoder (17.4 M) is excluded.
- **DP**, project shape (2 cameras, 6-D): 277.8 M parameters, of which 4.1% are Linear (11.5 M) and 95.8% convolution (266.2 M).

Checks against Hugging Face counts [13]:
- **PushT DP:** 262,709,026 calculated vs 262,709,062 reported (Δ 36).
- **ALOHA ACT:** 51,613,582 calculated vs 51,685,096 reported (Δ 0.14%).

The ResNet-18 convolution-weight count of 11,166,912 is [M]: the torchvision total of 11,689,512 minus the classifier and norm parameters. The cross-checks support it.

## 3. Measurement and evidence plan (AP-3)

- **Evidence classes.** They never share a table, and E1/E2 never stand in for board results [1]:
  - **E1:** laptop Stage C. smolvla_base, not fine-tuned, on svla_so101_pickplace, i5-1235U, FP32 p50 4.95 s per chunk [14].
  - **E2:** third-party or other-device results.
  - **E3:** board probes on base or random-init weights.
  - **E4:** board probes on frozen trained references.
  - **E5:** scored runs.
- **Golden inputs.** A fixed list of validation-split frames; test frames are never used. Frames are stored raw and as host-preprocessed tensors. SmolVLA flow noise and DP initial and per-step DDPM noise are injected identically; ACT is deterministic.
- **Parity (hard gate).** Two conditions:
  - Board preprocessing equals the host LeRobot tensors: camera order (top, wrist), resize/pad, normalization statistics and tokens.
  - FP32 export matches PyTorch FP32 within 1e-3 [9].
- **Fidelity (reported).** Compare FP16/INT8/INT4 with the board FP32 reference on the same inputs:
  - Per-joint error in joint units (mean, p95, max) over executed steps and the full chunk.
  - Normalized MAE.
  - Flags: NaN/Inf, or actions outside the training-split range.

  Behavioural impact comes from matched simulation (SO101-35).
- **Timing.** Use a monotonic clock with four boundaries: T0 observation in memory, T1 preprocessed, T2 model output, T3 post-processed chunk.
  - Report model latency (T1→T2) and policy latency (T0→T3) as p50, p95 and max over 100 requests after 5 warm-ups [2].
  - Record threads, core affinity, CPU governor and temperatures.
  - MCU, transport and actuation are timed separately (SO101-19/20).
- **Memory and package.**
  - Memory: peak RSS (VmHWM) and the drop in system MemAvailable, separately for load and steady state.
  - Package: bytes and SHA-256 of every deployed file.
  - File size is never reported as runtime memory [2].
- **Queue behaviour.** Board-only replay, with inference in a background thread and a consumer at the SO101-37 contract rate. Log underruns, observation age at execution and chunk overlap. No arm is connected.
- **Sustained run.** Continuous replay with 1 Hz thermal-zone and CPU-frequency logging; report drift and throttling. Inference only, with the supplied cooling fitted [10].
- **Board use.** One workload at a time [2].
- **Agreement with 0001.** The latency, memory and package definitions agree with the SO101-22 draft (0001 §3) [11]. This plan adds the T0–T3 boundaries, load vs steady memory and SHA-256.

## 4. Rationale, alternatives and risks

- **Why the CPU [V]:**
  - ExecuTorch + XNNPACK supports ARM64 Linux with FP16 and FP32, INT8 for linear, conv1d and conv2d, and 4-bit weights for linear layers (8-bit dynamic activations) and weight-only embeddings [5].
  - Sources differ on conv1d: the op table lists dynamic activations, but `gemm_configs.py` accepts dynamic quantization only for 2-D convolutions [5]. Static activations for convolutions avoid the conflict.
- **vla.cpp [V]:**
  - Supports SmolVLA and ACT on the ARM CPU; ACT support is unreleased.
  - The Q8_0/Q4_0 repack leaves convolutions, embeddings, norms and the action expert in float. The vision tower is quantized only with `--vision`.
  - No Diffusion Policy support. The Hexagon backend is verified only on Windows on Arm.
  - Supports OpenVLA-OFT, not OpenVLA [6].
- **ONNX Runtime [V]:** INT8 covers Conv and MatMul; 4-bit is weight-only for MatMul and Gather [7]. The Arm SmolVLA ONNX/INT4 precedent ran on another device: 3.33 s → 2.06 s with normalized MAE 0.153 [9].
- **NPU gaps [V]:**
  - ExecuTorch's Qualcomm backend has no QCS8275/QCS8300 entry [3].
  - AI Hub quantize jobs support INT8 weights only, with no mixed precision [4].
  - On the IQ-8275 EVK (Hexagon v75), Ubuntu NPU use needed FastRPC, QAIRT libraries and two LiteRT-LM patches [8].
  - Version 3 treats NPU acceleration as an investigation [2].
- **Rejected alternatives:**
  - NPU-first via QAIRT: widest precision menu [15][16], but the highest toolchain risk.
  - vla.cpp only: no Diffusion Policy.
  - ONNX Runtime only: FP16 kernel coverage on Arm CPUs is unverified.
  - PyTorch eager + torchao: Arm low-bit kernels would need a source build on the board, because torchao 0.18.0 has no aarch64 binary wheel [17].
- **Residual risk [R]:** GroupNorm, LayerNorm, Mish and SiLU are absent from the XNNPACK operator list [5]. DP and SmolVLA graphs will therefore split into delegated and portable segments. A runtime switch after 18 Oct forces a re-probe.

## 5. OpenVLA desk check [V + R]

- **FP16 does not fit [R].** 7,541,237,184 parameters [13] × 2 B = 15,082,474,368 B ≈ 15.08 GB (14.05 GiB). The board has 16 GB in total [10], before the OS, firmware, runtime, activations and buffers.
- **Lower bounds:** INT8 ≥ 7.54 GB and INT4 ≥ 3.77 GB.
- **Published GPU footprints:** 16.8, 10.2 and 7.0 GB for bf16, int8 and int4 on an A5000, where int8 ran at 1.2 Hz [18].
- **Training:** LoRA needs at least about 27 GB of GPU memory [19]. A 4090 has 24 GB, and the two GPUs do not pool memory [2].
- **Runtime:** vla.cpp supports OpenVLA-OFT [6], a different recipe [20].
- **Outcome:** OpenVLA stays a reserve. Using it requires an explicit scope change for its FP16 cell.

## 6. Gates and schedule effects

- **15 Oct (Day 0), Chung and Duc:** board inventory and pinned revisions.
  - Inventory: OS, kernel, glibc, CPU flags (fp16, dotprod, i8mm, bf16), MemTotal, Python, thermal zones and fan.
  - NPU facts are recorded but not used: FastRPC node, SoC ID and QAIRT/HTP version.
- **15–16 Oct (E3), Duc:** P1 ACT, P2 DP and P3 SmolVLA dual-track with project-shaped inputs (2 × 480 × 640, 6-D). Each must pass the runtime gate (§1) or record an evidenced blocker.
- **16 Oct 17:00, Hoan:** review E3. This feeds SO101-101 (17 Oct) and SO101-102 (18 Oct).
- **26–29 Oct (E4, SO101-59), Duc and Chung:** on frozen checkpoints, run parity, fidelity, queue and sustained tests. Freeze artifacts with SHA-256.
- **30 Oct–11 Nov (E5, SO101-61/62), Duc:** scored runs, with a first pass on 4 Nov.
- **Schedule effects:**
  - Fixed dates are unchanged.
  - G05 gains the Day-0 inventory and the SmolVLA dual track.
  - Queue and sustained tests sit in SO101-59.
  - The SO101-34, -59 and -101 Jira descriptions still need these updates; none were made.

## 7. Open items (no defaults)

1. Queue-test control rate and the number of executed steps. Owned by the SO101-37 contract (Hoan, with Chung and Khanh).
2. Sustained-run duration and thermal stop limits (Hoan with Chung).
3. Any numeric fidelity threshold (Hoan). Revisit it if the SO101-22 validity check (0001 G3) finds that the unquantized references score zero in simulation [11].
4. Day-0 board facts: Ubuntu version and glibc (the vla.cpp prebuilt needs 24.04), fp16 and dotprod flags, MemTotal, Hexagon and QAIRT versions.
5. vla.cpp ACT support is unreleased: pin a commit or wait for a release (Duc).
6. Write a `research/experiments/NNN-name/README.md` per probe before any code is written (CLAUDE.md).

## 8. Dependent work to update

These are proposals only. Nothing has been applied to Jira.

- **SO101-101 / SO101-35:** inherit §3.
- **SO101-102:** model approval uses the E3 gate results.
- **SO101-59:** add the queue and sustained tests on frozen profiles.
- **SO101-18 / SO101-45:** report every cell with the §2 disclosure, including the DP INT4 coverage.
- **SO101-37:** must supply the queue-test rate.

## References

All sources were read on 2026-10-14 [V] unless marked otherwise.

[1] SO101 Jira, "SO101-34: Decide the VENTUNO Q runtime, precision comparison and resource-test plan", adopted timeline v3 description, 2026-10-12. Internal: `docs/project-management/jira/snapshots/2026-10-14.json`.

[2] SO101 team, "SO101 resolved planning decisions and revised schedule", version 3, 2026-10-12. Internal: `docs/project-management/plans/SO101_Timeline_Review_and_Revised_Schedule_2026-10-12_v3.md`.

[3] PyTorch, "Qualcomm AI Engine Backend", ExecuTorch 1.5 docs, https://docs.pytorch.org/executorch/stable/backends-qualcomm.html, and `backends/qualcomm/serialization/qc_schema.py` @ 38e0798 (2026-10-14).

[4] Qualcomm, "Quantization", AI Hub Workbench docs, https://workbench.aihub.qualcomm.com/docs/hub/quantize_examples.html

[5] PyTorch, ExecuTorch XNNPACK overview, quantization, `op-support.csv` and `backends/xnnpack/partition/config/gemm_configs.py` @ 38e0798. https://docs.pytorch.org/executorch/stable/backends/xnnpack/xnnpack-quantization.html

[6] VinRobotics, vla.cpp @ cff0cfb (2026-10-13): README, docs/USAGE.md, docs/MODELS.md, CHANGELOG.md, scripts/quantize_gguf.py, docs/backend/hexagon.md. https://github.com/VinRobotics/vla.cpp

[7] Microsoft, "Quantize ONNX models", ONNX Runtime docs, https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html

[8] Qualcomm, "Gemma LiteRT-LM on IQ8", Dragonwing tutorials, 2026-06-29, https://dragonwingdocs.qualcomm.com/tutorials/gemma-litert-lm-on-iq8

[9] T. Wu, "Export and quantize SmolVLA for ONNX Runtime on Arm", Arm Learning Paths, updated 2026-08-27, https://learn.arm.com/learning-paths/cross-platform/smolvla-onnx-conversion/

[10] Arduino, "Arduino VENTUNO Q User Manual (ABX00181)", modified 2026-10-08, §§2.2.1, 7, 8.1, 12.1, https://docs.arduino.cc/resources/datasheets/ABX00181-datasheet.pdf

[11] Decision record 0001, "Simulation benchmark, reference controller and outcome definitions (SO101-22)", proposed draft, 2026-10-14. Internal: `docs/technical/decisions/0001-simulation-benchmark-and-reference.md`.

[12] Hugging Face, LeRobot v0.6.2 @ 53feaef (2026-10-14): `policies/act`, `policies/diffusion`, `policies/smolvla`. https://github.com/huggingface/lerobot

[13] Hugging Face Hub API, safetensors parameter counts for lerobot/smolvla_base, lerobot/act_aloha_sim_transfer_cube_human, lerobot/diffusion_pusht and openvla/openvla-7b. https://huggingface.co/api/models/lerobot/smolvla_base?expand[]=safetensors

[14] SO101 team, "Stage C: SmolVLA inference on the development laptop CPU", 2026-09-15. Internal: `research/results/stageC-laptop-cpu/README.md`.

[15] Qualcomm, "General tools", QAIRT SDK docs 80-63442-10, https://docs.qualcomm.com/doc/80-63442-10/topic/general_tools.html

[16] Qualcomm, "AI hardware cores/accelerators", 80-63195-1, 2024-05-16, https://docs.qualcomm.com/doc/80-63195-1/topic/AI-hardware-cores-accelerators.html

[17] PyPI release files: executorch 1.5.1, torch 2.14.1, onnxruntime 1.31.0, torchao 0.18.0. https://pypi.org/project/executorch/

[18] M. J. Kim et al., "OpenVLA: An open-source vision-language-action model", arXiv:2406.09246, 2024, §5.4, Table 2.

[19] OpenVLA, `openvla/openvla` README, https://github.com/openvla/openvla

[20] M. J. Kim, C. Finn, P. Liang, "Fine-tuning vision-language-action models: Optimizing speed and success", arXiv:2502.19645, 2025.

Board and CPU facts appear in the condensed report. They come from the Qualcomm QCS8275 data sheet (80-73475-1), https://docs.qualcomm.com/doc/80-73475-1/topic/device-description.html, and the IQ-8275 EVK overview, https://dragonwingdocs.qualcomm.com/Linux/devices/iq8275-evk/device-overview [V].
