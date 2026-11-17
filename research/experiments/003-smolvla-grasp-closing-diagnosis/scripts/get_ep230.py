"""Download Project-IRA metadata + data parquet, extract episode 230 actions/states to npz."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from huggingface_hub import hf_hub_download

REPO = "Project-IRA/TPSoSe2026_Dataset_Full_Merged_Final_LeRobot_SO101_V1"
REV = "bf6f568e9ec218fff838fb266e161724ec4f7e2c"
dl_dir = Path(sys.argv[1])
out_npz = Path(sys.argv[2])
EP = 230

meta = pd.read_parquet(hf_hub_download(REPO, "meta/episodes/chunk-000/file-000.parquet", repo_type="dataset",
                                       revision=REV, local_dir=dl_dir))
row = meta[meta["episode_index"] == EP].iloc[0]
cols = [c for c in meta.columns if c.startswith(("data/", "videos/", "tasks", "length", "dataset_"))]
print("episode meta:", {c: (row[c].tolist() if hasattr(row[c], "tolist") else row[c]) for c in cols})
data_file = f"data/chunk-{int(row['data/chunk_index']):03d}/file-{int(row['data/file_index']):03d}.parquet"
print("data file:", data_file)
df = pd.read_parquet(hf_hub_download(REPO, data_file, repo_type="dataset", revision=REV, local_dir=dl_dir))
ep = df[df["episode_index"] == EP].sort_values("frame_index")
action = np.stack(ep["action"].to_numpy()).astype(np.float32)
state = np.stack(ep["observation.state"].to_numpy()).astype(np.float32)
print("frames:", len(ep), "action shape:", action.shape, "fps from timestamps:",
      round(1 / np.median(np.diff(ep["timestamp"].to_numpy())), 2))
print("frame 100 state :", np.round(state[100], 3).tolist())
print("frame 100 action:", np.round(action[100], 3).tolist())
out_npz.parent.mkdir(parents=True, exist_ok=True)
np.savez(out_npz, action=action, state=state, fps=np.array(30))
print("saved", out_npz)
