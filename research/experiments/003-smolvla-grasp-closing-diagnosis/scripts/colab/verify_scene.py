import subprocess
env = "MUJOCO_GL=egl PYOPENGL_PLATFORM=egl"
for cmd in (f"cd /content/RobotArm/so101sim && {env} python self_test.py 2>&1 | tail -4",
            f"cd /content/RobotArm && {env} python so101sim/replay_desk_cleanup.py 2>&1",
            f"cd /content/RobotArm/so101sim && {env} python -m unittest tests.test_desk_cleanup tests.test_grasp 2>&1 | tail -3",
            f"cd /content/RobotArm/so101sim && {env} python -c \"import desk_cleanup as d; s=d.create_simulation(match_dataset=True); "
            f"import mujoco; r=mujoco.Renderer(s.model,480,640); r.update_scene(s.data,camera='overhead_camera'); "
            f"print('render ok', r.render().shape)\""):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"$ {cmd.split('&&')[-1].strip()[:90]}\n{r.stdout}{r.stderr[-800:]}", flush=True)
