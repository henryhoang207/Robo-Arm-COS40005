import mujoco

MODEL_PATH = "scene.xml"
JOINT_NAME = "gripper"
TEST_TARGETS = [-0.10, 1.00]
STEPS_PER_TARGET = 2000

model = mujoco.MjModel.from_xml_path(MODEL_PATH)
data = mujoco.MjData(model)

joint_id = mujoco.mj_name2id(
    model, mujoco.mjtObj.mjOBJ_JOINT, JOINT_NAME
)
actuator_id = mujoco.mj_name2id(
    model, mujoco.mjtObj.mjOBJ_ACTUATOR, JOINT_NAME
)

if joint_id < 0 or actuator_id < 0:
    raise RuntimeError("Gripper joint or actuator not found")

qpos_index = model.jnt_qposadr[joint_id]
lower, upper = model.actuator_ctrlrange[actuator_id]

print("GRIPPER MOTION TEST")
print(f"Model: {MODEL_PATH}")
print(f"Control range: [{lower:.4f}, {upper:.4f}] rad")
print(f"Initial angle: {data.qpos[qpos_index]:.6f} rad")

# Hold all joints at their initial positions.
for jid in range(model.njnt):
    if model.jnt_type[jid] == mujoco.mjtJoint.mjJNT_FREE:
        continue

for aid in range(model.nu):
    joint_for_actuator = model.actuator_trnid[aid, 0]
    if joint_for_actuator >= 0:
        q_index = model.jnt_qposadr[joint_for_actuator]
        data.ctrl[aid] = data.qpos[q_index]

mujoco.mj_forward(model, data)

results = []

for target in TEST_TARGETS:
    if not lower <= target <= upper:
        raise ValueError(f"Target outside control range: {target}")

    data.ctrl[actuator_id] = target

    for _ in range(STEPS_PER_TARGET):
        mujoco.mj_step(model, data)

    actual = float(data.qpos[qpos_index])
    error = target - actual
    results.append(actual)

    print(
        f"Target: {target:+.4f} rad | "
        f"Actual: {actual:+.6f} rad | "
        f"Error: {error:+.6f} rad"
    )

movement = abs(results[1] - results[0])
print(f"Measured angle change: {movement:.6f} rad")

if movement > 0.05:
    print("GRIPPER JOINT MOVEMENT TEST: PASS")
else:
    print("GRIPPER JOINT MOVEMENT TEST: FAIL")

print("Note: This test does not verify grasp force or object holding.")