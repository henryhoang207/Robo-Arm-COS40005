import subprocess
for cmd in ("pip uninstall -y -q datasets 2>&1 | tail -1",
            "python -c \"from lerobot.policies import make_pre_post_processors; "
            "from lerobot.policies.smolvla import SmolVLAPolicy; print('lerobot policies import OK')\""):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"$ {cmd}\n{r.stdout}{r.stderr[-600:]}", flush=True)
