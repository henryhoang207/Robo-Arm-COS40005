import subprocess
r = subprocess.run("cd /content/RobotArm/so101sim && MUJOCO_GL=egl python -m unittest discover -s tests 2>&1 | grep -E '^(ERROR|FAIL|Ran|OK|FAILED)'",
                   shell=True, capture_output=True, text=True)
print(r.stdout, r.stderr[-500:])
