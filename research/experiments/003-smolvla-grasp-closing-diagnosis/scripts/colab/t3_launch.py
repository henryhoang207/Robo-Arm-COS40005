import subprocess
# One process per seed: a second MuJoCo EGL Renderer in the same process rendered pure noise.
loop = ("for look in small big; do for s in $(seq 0 19); do "
        "LOOK=$look NOISE=cpu SEEDS=$s REPLAN=50 TAG=fix MUJOCO_GL=egl python /content/t3_rollout.py; done; done")
subprocess.run(f"cd /content && nohup sh -c '{loop}' > /content/t3_fix.log 2>&1 &", shell=True)
print("launched")
