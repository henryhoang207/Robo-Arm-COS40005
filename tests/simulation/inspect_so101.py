import mujoco

model = mujoco.MjModel.from_xml_path("scene.xml")
data = mujoco.MjData(model)

print("=" * 60)
print("SO-101 MODEL INFORMATION")
print("=" * 60)

print(f"\nNumber of joints: {model.njnt}")
print(f"Number of actuators: {model.nu}")
print(f"Number of qpos values: {model.nq}")
print(f"Number of qvel values: {model.nv}")

print("\n" + "=" * 60)
print("JOINTS")
print("=" * 60)

for joint_id in range(model.njnt):
    name = mujoco.mj_id2name(
        model,
        mujoco.mjtObj.mjOBJ_JOINT,
        joint_id
    )

    qpos_address = model.jnt_qposadr[joint_id]
    joint_range = model.jnt_range[joint_id]

    print(
        f"[{joint_id}] "
        f"name={name}, "
        f"qpos_index={qpos_address}, "
        f"range=[{joint_range[0]:.4f}, {joint_range[1]:.4f}]"
    )

print("\n" + "=" * 60)
print("ACTUATORS")
print("=" * 60)

for actuator_id in range(model.nu):
    actuator_name = mujoco.mj_id2name(
        model,
        mujoco.mjtObj.mjOBJ_ACTUATOR,
        actuator_id
    )

    joint_id = model.actuator_trnid[actuator_id, 0]

    joint_name = mujoco.mj_id2name(
        model,
        mujoco.mjtObj.mjOBJ_JOINT,
        joint_id
    )

    ctrl_range = model.actuator_ctrlrange[actuator_id]

    print(
        f"[{actuator_id}] "
        f"actuator={actuator_name}, "
        f"joint={joint_name}, "
        f"ctrlrange=[{ctrl_range[0]:.4f}, {ctrl_range[1]:.4f}]"
    )

print("\n" + "=" * 60)
print("INITIAL JOINT STATE")
print("=" * 60)

print("qpos =", data.qpos)
print("qvel =", data.qvel)