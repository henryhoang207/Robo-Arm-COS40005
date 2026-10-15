import time

import mujoco
import mujoco.viewer


model = mujoco.MjModel.from_xml_path("scene.xml")
data = mujoco.MjData(model)

mujoco.mj_forward(model, data)

# Keep every actuator initially at its current joint position.
for actuator_id in range(model.nu):
    joint_id = model.actuator_trnid[actuator_id, 0]
    qpos_index = model.jnt_qposadr[joint_id]
    data.ctrl[actuator_id] = data.qpos[qpos_index]

actuator_name = "shoulder_pan"

actuator_id = mujoco.mj_name2id(
    model,
    mujoco.mjtObj.mjOBJ_ACTUATOR,
    actuator_name
)

joint_id = mujoco.mj_name2id(
    model,
    mujoco.mjtObj.mjOBJ_JOINT,
    actuator_name
)

qpos_index = model.jnt_qposadr[joint_id]

target = 0.5  # radians, about 28.6 degrees

print("Actuator ID:", actuator_id)
print("Joint ID:", joint_id)
print("Initial position:", data.qpos[qpos_index])
print("Target:", target)

data.ctrl[actuator_id] = target

with mujoco.viewer.launch_passive(model, data) as viewer:
    start_time = time.time()

    while viewer.is_running() and time.time() - start_time < 8.0:
        mujoco.mj_step(model, data)
        viewer.sync()

        time.sleep(model.opt.timestep)

    print("Final position:", data.qpos[qpos_index])
    print("Position error:", target - data.qpos[qpos_index])