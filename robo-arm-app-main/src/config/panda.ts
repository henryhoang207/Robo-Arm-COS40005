// Franka Panda (LIBERO demo). Joint ranges are the simulator's own model:
// robosuite v1.4.0, robosuite/models/assets/robots/panda/robot.xml, `range` of joint1..joint7
// (radians, converted to degrees below). These are the simulation's limits, for the limit bars.

export const PANDA_JOINT_COUNT = 7;

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
