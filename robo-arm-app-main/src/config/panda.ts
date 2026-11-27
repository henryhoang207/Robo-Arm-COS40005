// Franka Panda (LIBERO demo). Joint ranges are the simulator's own model:
// robosuite v1.4.0, robosuite/models/assets/robots/panda/robot.xml, `range` of joint1..joint7
// (radians, converted to degrees below). These are the simulation's limits, for the limit bars.

export const PANDA_JOINT_COUNT = 7;

export const PANDA_URDF_PATH = `${import.meta.env.BASE_URL}robot/panda/panda.urdf`;
export const PANDA_EE_LINK = 'panda_eef';
export const PANDA_FINGER_OPEN_M = 0.04;
/** Fallback LIBERO kitchen_table base offset (m) if plannedEefMm arrives without eefMm. */
export const PANDA_FALLBACK_BASE_M: readonly [number, number, number] = [-0.66, 0, 0.912];

const RANGES_RAD: [number, number][] = [
  [-2.8973, 2.8973],
  [-1.7628, 1.7628],
  [-2.8973, 2.8973],
  [-3.0718, -0.0698],
  [-2.8973, 2.8973],
  [-0.0175, 3.7525],
  [-2.8973, 2.8973],
];

const deg = (rad: number) => (rad * 180) / Math.PI;

/** LIBERO MountedPanda.init_qpos (degrees), shown before the first live arm_state arrives. */
export const PANDA_INIT_DEG: readonly number[] = [
  0,
  deg(-0.161037389),
  0,
  deg(-2.44459747),
  0,
  deg(2.2267522),
  deg(Math.PI / 4),
];

export interface PandaJointDef {
  /** "joint1" … "joint7", as in the simulator model. */
  id: string;
  /** CSS variable holding the joint colour. */
  color: string;
  /** [min, max] in degrees. */
  limitDeg: [number, number];
}

export const PANDA_JOINTS: PandaJointDef[] = RANGES_RAD.map(([lo, hi], i) => ({
  id: `joint${i + 1}`,
  color: `--panda-joint${i + 1}`,
  limitDeg: [deg(lo), deg(hi)],
}));

/** Chart groups: base and shoulder side, wrist side. */
export const PANDA_CHART_GROUPS: { id: 'base' | 'wrist'; joints: number[] }[] = [
  { id: 'base', joints: [0, 1, 2, 3] },
  { id: 'wrist', joints: [4, 5, 6] },
];
