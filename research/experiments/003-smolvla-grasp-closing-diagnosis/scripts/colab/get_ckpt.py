"""Download the SmolVLA checkpoint folder from Google Drive onto the Colab VM.

The Drive folder id is NOT stored in this public repo. Ask Hoan for it, then run with
DRIVE_FOLDER_ID=<id> (set it in the VM environment or edit locally; do not commit it).
"""
import json, os, subprocess
FOLDER_ID = os.environ["DRIVE_FOLDER_ID"]


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"$ {cmd}\n{r.stdout[-1200:]}{r.stderr[-1200:]}", flush=True)


sh("pip install -q gdown 2>&1 | tail -1")
sh(f"mkdir -p /content/ckpt && gdown --folder {FOLDER_ID} -O /content/ckpt/pretrained_model 2>&1 | tail -5")
sh("ls -la /content/ckpt/pretrained_model")
cfg = json.load(open("/content/ckpt/pretrained_model/train_config.json"))
print("dataset:", cfg["dataset"]["repo_id"], cfg["dataset"]["revision"])   # expect Project-IRA ... bf6f568...
sh("sha256sum /content/ckpt/pretrained_model/model.safetensors")         # expect 5d3e70bd5892550f...
