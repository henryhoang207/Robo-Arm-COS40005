# Setup — episode-230 ball-into-bowl sim + SmolVLA (for teammates)

This reproduces Hoan's setup of 2026-11-17 on Windows, with an optional Colab GPU. After setup, read [FAILURE_LOG.md](FAILURE_LOG.md) and [HANDOVER.md](HANDOVER.md).

Simulation only: nothing here commands hardware.

## 1. Clone into an ASCII path

MuJoCo cannot open files under paths with non-ASCII characters, such as a Vietnamese "Documents" folder name (FAILURE_LOG C1). The analysis scripts in `scripts/` assume **`C:\RobotArm`**.

```powershell
git clone https://github.com/henryhoang207/Robo-Arm_sedoitensau.git C:\RobotArm
cd C:\RobotArm
git switch sim/episode-230-ball-bowl
```

## 2. Python environment (Python 3.13, CPU)

```powershell
py -3.13 -m venv so101sim\.venv
.\so101sim\.venv\Scripts\python.exe -m pip install -r so101sim\requirements.txt
.\so101sim\.venv\Scripts\python.exe -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.8.0 torchvision==0.23.0
.\so101sim\.venv\Scripts\python.exe -m pip install "lerobot[smolvla]==0.7.0" av scipy pandas pyarrow
```

- **Wait until every pip command has finished** before running anything (FAILURE_LOG C2, C3).
- Expected versions: mujoco 3.17.0, torch 2.8.0+cpu, lerobot 0.7.0, numpy 2.2.x.
- If you have an NVIDIA GPU, install the CUDA build of torch instead and pass `--device cuda`.

## 3. Check the scene (no model needed)

```powershell
cd C:\RobotArm\so101sim
.\.venv\Scripts\python.exe self_test.py
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

- `self_test.py` should print two `PASS` lines.
- The unit tests: 9 pass. `test_board_mode` fails because the `so101arm/` folder is not in the repo; this is expected.

## 4. Episode-230 data (about 22 MB from Hugging Face)

```powershell
cd C:\RobotArm
.\so101sim\.venv\Scripts\python.exe research\experiments\003-smolvla-grasp-closing-diagnosis\scripts\get_ep230.py C:\RobotArm\data\raw\hf\project-ira C:\RobotArm\data\raw\desk_cleanup_episode_230.npz
.\so101sim\.venv\Scripts\python.exe so101sim\replay_desk_cleanup.py --viewer
```

- `data/raw/` is gitignored.
- **The replay must print a 14.03 cm lift, a 4.33 s hold, and `Ball resting inside bowl at end: True`.** If it does not, the scene differs from Hoan's; stop and compare `git diff`.
- For the camera-comparison scripts you also need the two episode videos, about 350 MB, from the same dataset revision: `videos/observation.images.desk_view/chunk-000/file-002.mp4` and `videos/observation.images.wrist_left/chunk-000/file-004.mp4`. Download them with `huggingface_hub.hf_hub_download` into `C:\RobotArm\data\raw\hf\project-ira`.

## 5. SmolVLA checkpoint (865 MB, not in git)

- Use `smolvla_so101/selected_100000/pretrained_model`: trained on Project-IRA at revision `bf6f568`, 7 files.
- It is on the team Google Drive. **Ask Hoan for the folder link**; it is not published in this public repo.
- Put it at `C:\dev\robot-arm-conversion\staging\results\smolvla_so101\selected_100000\pretrained_model`. That is the path the scripts and the commands below use.
- Check it:
  - `train_config.json` → `dataset.repo_id` is `Project-IRA/TPSoSe2026_Dataset_Full_Merged_Final_LeRobot_SO101_V1`, revision `bf6f568e…`;
  - `model.safetensors` is 906,712,520 bytes, with sha256 starting `5d3e70bd5892550f`.

## 6. Run the scene and the model

```powershell
cd C:\RobotArm\so101sim
.\.venv\Scripts\python.exe app.py
```

This opens the dataset-matched episode-230 scene (the only scene on this branch) and a dashboard at http://localhost:8000.

```powershell
cd C:\RobotArm
$env:HF_HUB_CACHE = 'C:\RobotArm\data\models\huggingface'
.\so101sim\.venv\Scripts\python.exe so101sim\run_smolvla.py "C:\dev\robot-arm-conversion\staging\results\smolvla_so101\selected_100000\pretrained_model" --task "Place the ball into the bowl to clear the desk" --steps 900 --device cpu --viewer
```

- On a laptop CPU, each prediction takes about 20–40 s, and the window freezes meanwhile; that is normal.
- The first run downloads the SmolVLM2 config and tokenizer.
- Expect the failure described in FAILURE_LOG A1/A2: the arm approaches, hovers above the ball and does not grasp.
- For logged runs with per-step metrics, use `research/experiments/003-…/scripts/logged_rollout.py <ckpt> <out_dir> 900 <seed> [replan]`.

## 7. Optional: Colab GPU (about 0.5 s per prediction)

The scripts are in [scripts/colab/](scripts/colab/), and they use the Google Colab CLI (`pip install google-colab-cli`, then sign in).

1. `colab new -s robotarm --gpu T4`.
2. Zip `C:\RobotArm\so101sim` (without `.venv`, `runs`, `__pycache__`), plus `data\raw\desk_cleanup_episode_230.npz`, as `RobotArm/…`. Upload it with `colab upload -s robotarm sim.zip /content/sim.zip`.
3. `colab exec -s robotarm -f scripts/colab/setup_env.py`.
4. On the VM, run `pip uninstall -y datasets` (FAILURE_LOG C7).
5. Set `DRIVE_FOLDER_ID` (from Hoan) and run `scripts/colab/get_ckpt.py`.
6. Run each rollout **in its own process** (FAILURE_LOG C10). Use `scripts/colab/t3_launch.py` to launch `t3_rollout.py` with `LOOK`, `SEEDS`, `NOISE=cpu` and `TAG`.
7. Always `colab stop -s robotarm` when done; the VM uses compute units.
