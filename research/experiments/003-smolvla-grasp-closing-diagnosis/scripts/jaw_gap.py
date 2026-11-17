"""Jaw pad gap vs recorded gripper percent, and the recorded gripper values during episode 230."""
import sys
sys.path.insert(0, r"C:\RobotArm\so101sim")
import numpy as np
import mujoco
import desk_cleanup

sim = desk_cleanup.create_simulation(match_dataset=True)
m, d = sim.model, sim.data
g = m.joint("gripper")
a, b = m.geom("fixed_finger_pad").id, m.geom("moving_finger_pad").id
lo, hi = m.jnt_range[g.id]
print(f"gripper joint range {lo:.3f}..{hi:.3f} rad; mapping rad = {desk_cleanup.ZERO_RAD[-1]:.3f} + "
      f"{desk_cleanup.RAD_PER_UNIT[-1]} * percent")
fromto = np.zeros(6)
for pct in (0, 10, 20, 24, 30, 40, 50, 60, 80, 100):
    q = desk_cleanup.ZERO_RAD[-1] + desk_cleanup.RAD_PER_UNIT[-1] * pct
    d.qpos[m.jnt_qposadr[g.id]] = np.clip(q, lo, hi)
    mujoco.mj_forward(m, d)
    dist = mujoco.mj_geomDistance(m, d, a, b, 1.0, fromto)
    tips = np.linalg.norm(d.site("gripperframe").xpos - d.geom_xpos[b])
    print(f"  {pct:3d}% -> {np.degrees(np.clip(q, lo, hi)):6.1f} deg, pad-to-pad gap {1000 * dist:5.1f} mm")
ep = np.load(r"C:\RobotArm\data\raw\desk_cleanup_episode_230.npz")
grip = ep["action"][100:, -1]
print("recorded gripper % (frames 100-948): max", grip.max().round(1), "at frame", 100 + int(grip.argmax()),
      "| during hold ~frames 480-620: min", grip[380:520].min().round(1), "max", grip[380:520].max().round(1))
print(f"ball diameter in sim now: {2000 * m.geom('blue_ball_geom').size[0]:.1f} mm")
