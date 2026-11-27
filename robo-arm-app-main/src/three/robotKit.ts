// Robot geometry for the 3D viewer: SO-101 or Franka Panda URDF when available,
// otherwise a placeholder kinematic chain built from cylinders. Both expose the same API.
import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import URDFLoader, { type URDFJoint, type URDFRobot } from 'urdf-loader';
import { ALL_JOINTS, config } from '../config';
import { PANDA_EE_LINK, PANDA_FINGER_OPEN_M, PANDA_JOINTS, PANDA_URDF_PATH } from '../config/panda';
import type { JointName } from '../types/messages';
import { urdfLimitsToData } from '../utils/units';

export type ArmKind = 'so101' | 'panda';

export interface JointHandle {
  object: THREE.Object3D;
  axis: THREE.Vector3;
  set: (rad: number) => void;
}

export interface RobotInstance {
  /** Robot base in URDF frame (z up). */
  root: THREE.Object3D;
  /** Ordered joint IDs exposed for rings, labels and link highlighting. */
  jointIds: string[];
  joints: Record<string, JointHandle>;
  ee: THREE.Object3D | null;
  /** Meshes moved directly by each joint (its child link). */
  linkMeshes: Record<string, THREE.Mesh[]>;
  meshes: THREE.Mesh[];
  /** Optional parallel-jaw gripper helper (Panda). */
  setGripper?: (open: boolean) => void;
}

export interface RobotKit {
  source: 'urdf' | 'placeholder';
  /** Joint ranges in data units (deg, gripper %), from the SO-101 URDF limits. */
  limits: Partial<Record<JointName, [number, number]>>;
  create: () => RobotInstance;
}

// --- URDF ------------------------------------------------------------------

function looksLikeUrdf(text: string): boolean {
  return /<robot[\s>]/.test(text);
}

async function loadUrdf(path: string): Promise<URDFRobot> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`URDF ${res.status}`);
  const text = await res.text();
  // Dev servers answer unknown paths with index.html: check the content.
  if (!looksLikeUrdf(text)) throw new Error('not a URDF');
  const manager = new THREE.LoadingManager();
  const loader = new URDFLoader(manager);
  let failed = false;
  manager.onError = () => (failed = true);
  const done = new Promise<void>((resolve) => {
    manager.onLoad = () => resolve();
    // Safety net if the URDF references no meshes (onLoad would never fire).
    setTimeout(resolve, 20_000);
  });
  loader.workingPath = THREE.LoaderUtils.extractUrlBase(path);
  if (import.meta.env.VITE_MESHES_AS_JSON === '1') loader.loadMeshCb = loadJsonMesh;
  const robot = loader.parse(text);
  await done;
  if (failed) throw new Error('URDF meshes failed to load');
  return robot;
}

/**
 * Hosts that cannot serve .stl (e.g. the claude.ai artifact preview) get each mesh as
 * `<name>.stl.json` = {"b64": base64 of the STL}; see scripts/stl-to-json.mjs.
 */
function loadJsonMesh(
  url: string,
  manager: THREE.LoadingManager,
  material: THREE.Material,
  done: (mesh: THREE.Object3D, err?: Error) => void,
) {
  manager.itemStart(url);
  fetch(`${url}.json`)
    .then((r) => r.json() as Promise<{ b64: string }>)
    .then(({ b64 }) => {
      const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
      done(new THREE.Mesh(new STLLoader().parse(bytes.buffer), material));
    })
    .catch((err: Error) => {
      manager.itemError(url);
      done(new THREE.Object3D(), err);
    })
    .finally(() => manager.itemEnd(url));
}

/** Visual meshes of a link, descending through fixed joints but stopping at movable child joints. */
function directMeshes(link: THREE.Object3D): THREE.Mesh[] {
  const out: THREE.Mesh[] = [];
  const walk = (o: THREE.Object3D) => {
    for (const c of o.children) {
      const j = c as URDFJoint;
      if (j.isURDFJoint && j.jointType !== 'fixed') continue;
      if ((c as THREE.Mesh).isMesh) out.push(c as THREE.Mesh);
      walk(c);
    }
  };
  walk(link);
  return out;
}

function collectMeshes(root: THREE.Object3D): THREE.Mesh[] {
  const meshes: THREE.Mesh[] = [];
  root.traverse((o) => {
    if ((o as THREE.Mesh).isMesh) meshes.push(o as THREE.Mesh);
  });
  return meshes;
}

function so101UrdfInstance(source: URDFRobot): RobotInstance {
  const robot = source.clone(true) as URDFRobot;
  const joints: Record<string, JointHandle> = {};
  const linkMeshes: Record<string, THREE.Mesh[]> = {};
  for (const name of ALL_JOINTS) {
    const j = robot.joints[name];
    if (!j) continue;
    joints[name] = { object: j, axis: j.axis.clone(), set: (rad) => void j.setJointValue(rad) };
    const child = j.children.find((c) => (c as { isURDFLink?: boolean }).isURDFLink);
    linkMeshes[name] = child ? directMeshes(child) : [];
  }
  const ee = robot.links[config.eeLink] ?? robot.frames?.[config.eeLink] ?? null;
  return {
    root: robot,
    jointIds: [...ALL_JOINTS],
    joints,
    ee,
    linkMeshes,
    meshes: collectMeshes(robot),
  };
}

function pandaUrdfInstance(source: URDFRobot): RobotInstance {
  const robot = source.clone(true) as URDFRobot;
  const joints: Record<string, JointHandle> = {};
  const linkMeshes: Record<string, THREE.Mesh[]> = {};
  const jointIds = PANDA_JOINTS.map((j) => j.id);
  for (let i = 0; i < PANDA_JOINTS.length; i++) {
    const id = PANDA_JOINTS[i]!.id;
    const j = robot.joints[`panda_joint${i + 1}`];
    if (!j) continue;
    joints[id] = { object: j, axis: j.axis.clone(), set: (rad) => void j.setJointValue(rad) };
    const child = j.children.find((c) => (c as { isURDFLink?: boolean }).isURDFLink);
    linkMeshes[id] = child ? directMeshes(child) : [];
  }
  const f1 = robot.joints['panda_finger_joint1'];
  const f2 = robot.joints['panda_finger_joint2'];
  const setGripper = (open: boolean) => {
    const pos = open ? PANDA_FINGER_OPEN_M : 0;
    f1?.setJointValue(pos);
    f2?.setJointValue(pos);
  };
  const ee = robot.links[PANDA_EE_LINK] ?? robot.frames?.[PANDA_EE_LINK] ?? null;
  return {
    root: robot,
    jointIds,
    joints,
    ee,
    linkMeshes,
    meshes: collectMeshes(robot),
    setGripper,
  };
}

// --- Placeholder chains ------------------------------------------------------

/** Rough SO-101 proportions (m); joint i rotates about `axis`, then offsets by `next`. */
const SO101_CHAIN: { joint: JointName; axis: [number, number, number]; length: number }[] = [
  { joint: 'shoulder_pan', axis: [0, 0, 1], length: 0.05 },
  { joint: 'shoulder_lift', axis: [0, 1, 0], length: 0.116 },
  { joint: 'elbow_flex', axis: [0, 1, 0], length: 0.135 },
  { joint: 'wrist_flex', axis: [0, 1, 0], length: 0.06 },
  { joint: 'wrist_roll', axis: [0, 0, 1], length: 0.04 },
  { joint: 'gripper', axis: [0, 1, 0], length: 0.06 },
];

function cylinder(length: number, radius: number): THREE.Mesh {
  const geo = new THREE.CylinderGeometry(radius, radius, length, 20);
  geo.rotateX(Math.PI / 2); // along +z
  geo.translate(0, 0, length / 2);
  return new THREE.Mesh(geo, new THREE.MeshStandardMaterial());
}

function so101PlaceholderInstance(): RobotInstance {
  const root = new THREE.Group();
  const base = cylinder(0.05, 0.045);
  root.add(base);
  const meshes: THREE.Mesh[] = [base];
  const joints: Record<string, JointHandle> = {};
  const linkMeshes: Record<string, THREE.Mesh[]> = {};
  let parent: THREE.Object3D = root;
  let offset = 0.05;
  for (const { joint, axis, length } of SO101_CHAIN) {
    const pivot = new THREE.Group();
    pivot.position.set(0, 0, offset);
    const ax = new THREE.Vector3(...axis);
    parent.add(pivot);
    const link =
      joint === 'gripper'
        ? cylinder(length, 0.006)
        : cylinder(length, joint === 'wrist_roll' ? 0.02 : 0.016);
    if (joint === 'gripper') link.position.x = 0.015;
    pivot.add(link);
    meshes.push(link);
    linkMeshes[joint] = [link];
    joints[joint] = {
      object: pivot,
      axis: ax,
      set: (rad) => pivot.quaternion.setFromAxisAngle(ax, rad),
    };
    if (joint !== 'gripper') parent = pivot;
    offset = length;
  }
  const ee = new THREE.Object3D();
  ee.position.set(0, 0, 0.1);
  joints.wrist_roll!.object.add(ee);
  return { root, jointIds: [...ALL_JOINTS], joints, ee, linkMeshes, meshes };
}

/** Rough Franka Panda kinematic chain (m) matching robosuite joint offsets. */
const PANDA_CHAIN: {
  id: string;
  xyz: [number, number, number];
  rpy: [number, number, number];
  length: number;
  radius: number;
}[] = [
  { id: 'joint1', xyz: [0, 0, 0.333], rpy: [0, 0, 0], length: 0.12, radius: 0.055 },
  { id: 'joint2', xyz: [0, 0, 0], rpy: [-Math.PI / 2, 0, 0], length: 0.316, radius: 0.05 },
  { id: 'joint3', xyz: [0, -0.316, 0], rpy: [Math.PI / 2, 0, 0], length: 0.12, radius: 0.045 },
  { id: 'joint4', xyz: [0.0825, 0, 0], rpy: [Math.PI / 2, 0, 0], length: 0.384, radius: 0.042 },
  { id: 'joint5', xyz: [-0.0825, 0.384, 0], rpy: [-Math.PI / 2, 0, 0], length: 0.12, radius: 0.038 },
  { id: 'joint6', xyz: [0, 0, 0], rpy: [Math.PI / 2, 0, 0], length: 0.088, radius: 0.036 },
  { id: 'joint7', xyz: [0.088, 0, 0], rpy: [Math.PI / 2, 0, 0], length: 0.1065, radius: 0.032 },
];

function pandaPlaceholderInstance(): RobotInstance {
  const root = new THREE.Group();
  const base = cylinder(0.14, 0.075);
  root.add(base);
  const meshes: THREE.Mesh[] = [base];
  const joints: Record<string, JointHandle> = {};
  const linkMeshes: Record<string, THREE.Mesh[]> = {};
  const zAxis = new THREE.Vector3(0, 0, 1);
  let parent: THREE.Object3D = root;
  for (const spec of PANDA_CHAIN) {
    const frame = new THREE.Group();
    frame.position.set(...spec.xyz);
    frame.rotation.set(...spec.rpy, 'XYZ');
    parent.add(frame);
    const pivot = new THREE.Group();
    frame.add(pivot);
    const link = cylinder(spec.length, spec.radius);
    pivot.add(link);
    meshes.push(link);
    linkMeshes[spec.id] = [link];
    joints[spec.id] = {
      object: pivot,
      axis: zAxis.clone(),
      set: (rad) => pivot.quaternion.setFromAxisAngle(zAxis, rad),
    };
    parent = pivot;
  }
  const ee = new THREE.Object3D();
  ee.position.set(0, 0, 0.2035);
  joints.joint7!.object.add(ee);
  return {
    root,
    jointIds: PANDA_JOINTS.map((j) => j.id),
    joints,
    ee,
    linkMeshes,
    meshes,
  };
}

// --- Kits --------------------------------------------------------------------

const placeholderKits: Record<ArmKind, RobotKit> = {
  so101: { source: 'placeholder', limits: {}, create: so101PlaceholderInstance },
  panda: { source: 'placeholder', limits: {}, create: pandaPlaceholderInstance },
};

const urdfKits = new Map<ArmKind, Promise<RobotKit>>();

/** Loads the requested arm's URDF once (cached per arm); falls back to a placeholder chain. */
export function loadRobotKit(
  opts: { arm?: ArmKind; forcePlaceholder?: boolean } = {},
): Promise<RobotKit> {
  const arm: ArmKind = opts.arm ?? 'so101';
  if (opts.forcePlaceholder) return Promise.resolve(placeholderKits[arm]);
  let cached = urdfKits.get(arm);
  if (!cached) {
    cached =
      arm === 'panda'
        ? loadUrdf(PANDA_URDF_PATH)
            .then(
              (robot): RobotKit => ({
                source: 'urdf',
                limits: {},
                create: () => pandaUrdfInstance(robot),
              }),
            )
            .catch(() => placeholderKits.panda)
        : loadUrdf(config.urdfPath)
            .then((robot): RobotKit => {
              const limits: RobotKit['limits'] = {};
              for (const name of ALL_JOINTS) {
                const l = robot.joints[name]?.limit;
                if (l && l.upper > l.lower) limits[name] = urdfLimitsToData(name, l.lower, l.upper);
              }
              return { source: 'urdf', limits, create: () => so101UrdfInstance(robot) };
            })
            .catch(() => placeholderKits.so101);
    urdfKits.set(arm, cached);
  }
  return cached;
}
