import os, subprocess, sys
def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"$ {cmd}\n{r.stdout[-1500:]}{r.stderr[-1500:]}", flush=True)
    return r.returncode
sh("cd /content && rm -rf RobotArm && python -m zipfile -e sim.zip /content && ls RobotArm RobotArm/so101sim | head -40")
sh("apt-get -qq install -y libegl1 libgl1 > /dev/null 2>&1; echo egl-ok")
sh("pip install -q 'mujoco==3.17.0' 'lerobot[smolvla]==0.7.0' av scipy pandas pyarrow 2>&1 | tail -3")
sh("python -c \"import torch,lerobot,mujoco;print(torch.__version__,torch.cuda.is_available(),lerobot.__version__,mujoco.__version__)\"")
