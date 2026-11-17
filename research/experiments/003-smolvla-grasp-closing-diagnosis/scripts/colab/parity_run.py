import subprocess
r = subprocess.run("cd /content && MUJOCO_GL=egl python /content/parity.py /content/ckpt/pretrained_model "
                   "/content/RobotArm/so101sim cuda,cpu 2>&1 | grep -E '^(torch|image|cuda|cpu)'",
                   shell=True, capture_output=True, text=True)
print(r.stdout, r.stderr[-500:])
