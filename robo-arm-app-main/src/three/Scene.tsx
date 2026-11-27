import { OrbitControls } from '@react-three/drei';
import { useThree } from '@react-three/fiber';
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { ALL_JOINTS, config, type ViewPreset } from '../config';
import { PANDA_FALLBACK_BASE_M, PANDA_INIT_DEG, PANDA_JOINTS } from '../config/panda';
import { useStore } from '../state/store';
import type { ArmSample, Layers, Sample } from '../state/types';
import type { JointValues, TaskInfo } from '../types/messages';
import { cssNumber, cssVar } from '../utils/css';
import { dataToUrdf } from '../utils/units';
import { disposeLabel, makeLabel } from './labels';
import type { ArmKind, RobotInstance, RobotKit } from './robotKit';

/** URDF is z-up; three.js is y-up. */
const ROOT_ROTATION = new THREE.Euler(-Math.PI / 2, 0, 0);
const DEG_TO_RAD = Math.PI / 180;

interface ArmRig {
  target: THREE.Vector3;
  presets: Record<ViewPreset, [number, number, number]>;
  gridSize: number;
  gridDivs: number;
  axesSize: number;
  ringRadius: number;
  ringTube: number;
  trailDash: number;
  trailGap: number;
  planDash: number;
  planGap: number;
  minDist: number;
  maxDist: number;
}

const RIGS: Record<ArmKind, ArmRig> = {
  so101: {
    target: new THREE.Vector3(0, 0.12, 0),
    presets: {
      perspective: [0.42, 0.34, 0.42],
      top: [0, 0.75, 0.0001],
      front: [0.62, 0.16, 0],
      side: [0, 0.16, 0.62],
    },
    gridSize: 1.6,
    gridDivs: 32,
    axesSize: 0.12,
    ringRadius: 0.02,
    ringTube: 0.0025,
    trailDash: 0.008,
    trailGap: 0.004,
    planDash: 0.012,
    planGap: 0.008,
    minDist: 0.15,
    maxDist: 2,
  },
  panda: {
    target: new THREE.Vector3(0.2, 0.42, 0),
    presets: {
      perspective: [1.25, 0.95, 1.25],
      top: [0.25, 2.0, 0.0001],
      front: [1.65, 0.48, 0],
      side: [0.2, 0.48, 1.55],
    },
    gridSize: 3.0,
    gridDivs: 30,
    axesSize: 0.25,
    ringRadius: 0.055,
    ringTube: 0.006,
    trailDash: 0.018,
    trailGap: 0.01,
    planDash: 0.022,
    planGap: 0.014,
    minDist: 0.35,
    maxDist: 4.5,
  },
};

function applySo101Joints(robot: RobotInstance, values: Partial<JointValues>) {
  for (const j of ALL_JOINTS) {
    const v = values[j];
    if (v !== undefined) robot.joints[j]?.set(dataToUrdf(j, v));
  }
}

function applyPandaJoints(
  robot: RobotInstance,
  jointsDeg: readonly number[],
  gripper: 'open' | 'closed' | null,
) {
  for (let i = 0; i < PANDA_JOINTS.length; i++) {
    const deg = jointsDeg[i];
    if (deg !== undefined) robot.joints[PANDA_JOINTS[i]!.id]?.set(deg * DEG_TO_RAD);
  }
  robot.setGripper?.(gripper !== 'closed');
}

function eeWorld(robot: RobotInstance, out: THREE.Vector3): THREE.Vector3 | null {
  if (!robot.ee) return null;
  robot.root.updateMatrixWorld(true);
  return robot.ee.getWorldPosition(out);
}

interface SceneProps {
  arm: ArmKind;
  kit: RobotKit;
  layers: Layers;
  selected: string | null;
  preset: ViewPreset;
  resetKey: number;
  pickLabel: string;
  dropLabel: string;
  /** End-effector position (mm), throttled. */
  onEe: (mm: [number, number, number] | null) => void;
}

export function RobotScene(props: SceneProps) {
  const { arm, kit, layers, selected } = props;
  const rig = RIGS[arm];
  const invalidate = useThree((s) => s.invalidate);

  const colors = useMemo(() => {
    const jointEntries =
      arm === 'panda'
        ? PANDA_JOINTS.map((j) => [j.id, cssVar(j.color, '#64748b')])
        : ALL_JOINTS.map((j) => [j, cssVar(`--joint-${j}`, '#64748b')]);
    return {
      body: cssVar('--robot-body', '#7b8794'),
      ghost: cssVar('--robot-ghost', '#1f6feb'),
      trail: cssVar('--ee-trail', '#1f2933'),
      plan: cssVar('--planned-path', '#1f6feb'),
      floor: cssVar('--viewport-floor', '#f6f8fa'),
      grid: cssVar('--viewport-grid', '#e4e7eb'),
      surface: cssVar('--surface', '#ffffff'),
      text: cssVar('--text', '#1f2933'),
      ghostOpacity: cssNumber('--opacity-ghost', 0.3),
      trailMin: cssNumber('--opacity-trail-min', 0.15),
      joints: Object.fromEntries(jointEntries) as Record<string, string>,
    };
  }, [arm]);

  // Measured instance for both arms; ghost + FK instances only for SO-101.
  const measured = useMemo(() => kit.create(), [kit]);
  const ghost = useMemo(() => (arm === 'so101' ? kit.create() : null), [arm, kit]);
  const fk = useMemo(() => {
    if (arm !== 'so101') return null;
    const r = kit.create();
    const holder = new THREE.Group();
    holder.rotation.copy(ROOT_ROTATION);
    holder.add(r.root);
    return r;
  }, [arm, kit]);

  // Materials: one per moving link so a selected joint can be tinted.
  const linkMaterials = useMemo(() => {
    const base = new THREE.MeshStandardMaterial({
      color: colors.body,
      roughness: 0.75,
      metalness: 0.05,
    });
    for (const m of measured.meshes) m.material = base;
    const perJoint: Record<string, THREE.MeshStandardMaterial> = {};
    for (const j of measured.jointIds) {
      const mat = base.clone();
      perJoint[j] = mat;
      for (const m of measured.linkMeshes[j] ?? []) m.material = mat;
    }
    if (ghost) {
      const ghostMat = new THREE.MeshBasicMaterial({
        color: colors.ghost,
        transparent: true,
        opacity: colors.ghostOpacity,
        depthWrite: false,
      });
      for (const m of ghost.meshes) {
        m.material = ghostMat;
        m.renderOrder = 2;
      }
    }
    return perJoint;
  }, [measured, ghost, colors]);

  // Joint rings in each joint's fixed colour.
  useEffect(() => {
    const rings: THREE.Mesh[] = [];
    for (const j of measured.jointIds) {
      const h = measured.joints[j];
      if (!h) continue;
      const radius = j === 'gripper' ? 0.012 : rig.ringRadius;
      const geo = new THREE.TorusGeometry(radius, rig.ringTube, 8, 32);
      const ring = new THREE.Mesh(
        geo,
        new THREE.MeshBasicMaterial({ color: colors.joints[j] ?? '#64748b' }),
      );
      ring.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), h.axis.clone().normalize());
      h.object.add(ring);
      rings.push(ring);
    }
    invalidate();
    return () => rings.forEach((r) => r.removeFromParent());
  }, [measured, colors, rig, invalidate]);

  // Highlight the selected joint's link.
  useEffect(() => {
    for (const j of measured.jointIds) {
      const mat = linkMaterials[j];
      if (!mat) continue;
      if (j === selected) {
        mat.emissive.set(colors.joints[j] ?? '#64748b');
        mat.emissiveIntensity = 0.55;
      } else {
        mat.emissive.set('#000000');
      }
    }
    invalidate();
  }, [selected, measured, linkMaterials, colors, invalidate]);

  // --- trail ---------------------------------------------------------------
  const trailPoints = useRef<{ t: number; p: THREE.Vector3 }[]>([]);
  const trailLine = useMemo(() => {
    const line = new THREE.Line(
      new THREE.BufferGeometry(),
      new THREE.LineDashedMaterial({
        vertexColors: true,
        dashSize: rig.trailDash,
        gapSize: rig.trailGap,
        transparent: true,
        // The tip sits inside the gripper, so draw the trail on top to keep it visible.
        depthTest: false,
      }),
    );
    line.renderOrder = 3;
    line.frustumCulled = false;
    return line;
  }, [rig]);

  const updateTrail = (now: number) => {
    const pts = trailPoints.current;
    while (pts.length && pts[0]!.t < now - config.trailMs) pts.shift();
    const pos = new Float32Array(pts.length * 3);
    const col = new Float32Array(pts.length * 3);
    const ink = new THREE.Color(colors.trail);
    const floor = new THREE.Color(colors.floor);
    const c = new THREE.Color();
    pts.forEach((pt, i) => {
      pos.set([pt.p.x, pt.p.y, pt.p.z], i * 3);
      const age = (now - pt.t) / config.trailMs;
      const strength = 1 - (1 - colors.trailMin) * Math.min(1, age);
      c.copy(floor).lerp(ink, strength);
      col.set([c.r, c.g, c.b], i * 3);
    });
    const g = trailLine.geometry;
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    g.computeBoundingSphere();
    trailLine.computeLineDistances();
  };

  // --- Panda planned path (URDF base frame, inside ROOT_ROTATION group) -----
  const pandaPlan = useMemo(() => {
    const group = new THREE.Group();
    group.visible = false;
    const line = new THREE.Line(
      new THREE.BufferGeometry(),
      new THREE.LineDashedMaterial({
        color: colors.plan,
        dashSize: rig.planDash,
        gapSize: rig.planGap,
        depthTest: false,
      }),
    );
    line.renderOrder = 4;
    line.frustumCulled = false;
    const endDot = new THREE.Mesh(
      new THREE.SphereGeometry(0.012, 14, 14),
      new THREE.MeshBasicMaterial({ color: colors.plan, depthTest: false }),
    );
    endDot.renderOrder = 5;
    group.add(line, endDot);
    return { group, line, endDot };
  }, [colors.plan, rig]);

  // --- data -> pose ----------------------------------------------------------
  const lastEeEmit = useRef(0);
  const onEe = useRef(props.onEe);
  useEffect(() => {
    onEe.current = props.onEe;
  });

  useEffect(() => {
    trailPoints.current = [];
    updateTrail(0);
    pandaPlan.group.visible = false;

    if (arm === 'panda') {
      const applyArm = (sample: ArmSample | undefined, running: boolean) => {
        if (!sample) {
          applyPandaJoints(measured, PANDA_INIT_DEG, 'open');
          pandaPlan.group.visible = false;
          invalidate();
          return;
        }
        applyPandaJoints(measured, sample.q, sample.gripper);
        const p = eeWorld(measured, new THREE.Vector3());
        const fkBase = p ? measured.root.worldToLocal(p.clone()) : null;
        if (p) {
          trailPoints.current.push({ t: sample.t, p });
          updateTrail(sample.t);
        }
        if (sample.t - lastEeEmit.current > 200) {
          lastEeEmit.current = sample.t;
          if (sample.eefMm) onEe.current(sample.eefMm);
          else if (fkBase) onEe.current([fkBase.x * 1000, fkBase.y * 1000, fkBase.z * 1000]);
        }
        // Align LIBERO world waypoints onto the 3D Panda base frame via live (fkBase - eefWorld).
        const pts = running && sample.plannedEefMm?.length ? sample.plannedEefMm : null;
        if (pts && fkBase) {
          const [ox, oy, oz] = sample.eefMm
            ? [
                fkBase.x - sample.eefMm[0] / 1000,
                fkBase.y - sample.eefMm[1] / 1000,
                fkBase.z - sample.eefMm[2] / 1000,
              ]
            : [-PANDA_FALLBACK_BASE_M[0], -PANDA_FALLBACK_BASE_M[1], -PANDA_FALLBACK_BASE_M[2]];
          const verts = new Float32Array((pts.length + 1) * 3);
          verts.set([fkBase.x, fkBase.y, fkBase.z], 0);
          let lx = fkBase.x;
          let ly = fkBase.y;
          let lz = fkBase.z;
          for (let i = 0; i < pts.length; i++) {
            const wp = pts[i]!;
            lx = wp[0] / 1000 + ox;
            ly = wp[1] / 1000 + oy;
            lz = wp[2] / 1000 + oz;
            verts.set([lx, ly, lz], (i + 1) * 3);
          }
          const g = pandaPlan.line.geometry;
          g.setAttribute('position', new THREE.BufferAttribute(verts, 3));
          g.computeBoundingSphere();
          pandaPlan.line.computeLineDistances();
          pandaPlan.endDot.position.set(lx, ly, lz);
          pandaPlan.group.visible = true;
        } else {
          pandaPlan.group.visible = false;
        }
        invalidate();
      };
      const s = useStore.getState();
      applyArm(s.arm[s.arm.length - 1], s.task.state === 'running');
      return useStore.subscribe((st, prev) => {
        if (st.arm !== prev.arm || st.task.state !== prev.task.state) {
          applyArm(st.arm[st.arm.length - 1], st.task.state === 'running');
        }
      });
    }

    const apply = (sample: Sample | undefined) => {
      if (!sample) return;
      const state = {} as JointValues;
      const action = {} as JointValues;
      let hasAction = true;
      for (const j of ALL_JOINTS) {
        state[j] = sample.joints[j].state;
        const a = sample.joints[j].action;
        if (a === null) hasAction = false;
        else action[j] = a;
      }
      applySo101Joints(measured, state);
      if (ghost) {
        // No target from the source: hide the ghost rather than draw a fake one (spec R3).
        ghost.root.visible = hasAction;
        if (hasAction) applySo101Joints(ghost, action);
      }
      const p = eeWorld(measured, new THREE.Vector3());
      if (p) {
        trailPoints.current.push({ t: sample.t, p });
        updateTrail(sample.t);
        if (sample.t - lastEeEmit.current > 200) {
          lastEeEmit.current = sample.t;
          const local = measured.root.worldToLocal(p.clone());
          onEe.current([local.x * 1000, local.y * 1000, local.z * 1000]);
        }
      }
      invalidate();
    };
    const s = useStore.getState();
    apply(s.samples[s.samples.length - 1]);
    return useStore.subscribe((st, prev) => {
      if (st.samples !== prev.samples) apply(st.samples[st.samples.length - 1]);
    });
    // updateTrail only reads refs and memoised objects.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [arm, measured, ghost, pandaPlan, invalidate]);

  useEffect(() => {
    if (!measured.ee) onEe.current(null);
  }, [measured]);

  // --- SO-101 plan -----------------------------------------------------------
  const task = useStore((s) =>
    s.task.state === 'running' ? s.tasks.find((t) => t.id === s.task.id) : undefined,
  );
  const plan = usePlan(arm === 'so101' ? task : undefined, fk);

  useEffect(() => invalidate(), [layers, plan, invalidate]);

  return (
    <>
      <color attach="background" args={[colors.surface]} />
      <hemisphereLight args={['#ffffff', '#c8ced6', 1.6]} />
      <directionalLight position={[0.6, 1, 0.4]} intensity={1.6} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.0005, 0]}>
        <planeGeometry args={[10, 10]} />
        <meshBasicMaterial color={colors.floor} />
      </mesh>
      <gridHelper args={[rig.gridSize, rig.gridDivs, colors.grid, colors.grid]} />

      <group rotation={ROOT_ROTATION}>
        <primitive object={measured.root} />
        {ghost && layers.ghost && <primitive object={ghost.root} />}
        {arm === 'panda' && layers.plan && <primitive object={pandaPlan.group} />}
        {layers.axes && <axesHelper args={[rig.axesSize]} />}
      </group>
      {layers.trail && <primitive object={trailLine} />}
      {arm === 'so101' && layers.plan && plan && (
        <PlanLayer plan={plan} color={colors.plan} ink={colors.text} {...props} />
      )}
      {layers.labels && <JointLabels robot={measured} />}

      <CameraRig rig={rig} preset={props.preset} resetKey={props.resetKey} />
    </>
  );
}

interface PlanGeometry {
  points: THREE.Vector3[];
  pick: THREE.Vector3 | null;
  drop: THREE.Vector3 | null;
  object: string | undefined;
}

/** Planned path in scene coordinates, from the task's joint waypoints (FK). */
function usePlan(task: TaskInfo | undefined, fk: RobotInstance | null): PlanGeometry | null {
  return useMemo(() => {
    if (!task?.plan?.length || !fk?.ee) return null;
    const points: THREE.Vector3[] = [];
    for (const wp of task.plan) {
      applySo101Joints(fk, wp);
      fk.root.parent?.updateMatrixWorld(true);
      const p = eeWorld(fk, new THREE.Vector3());
      if (p) points.push(p);
    }
    return {
      points,
      pick: task.pickIndex !== undefined ? (points[task.pickIndex] ?? null) : null,
      drop: task.dropIndex !== undefined ? (points[task.dropIndex] ?? null) : null,
      object: task.params?.object,
    };
  }, [task?.id, task?.plan, fk]); // eslint-disable-line react-hooks/exhaustive-deps
}

function PlanLayer({
  plan,
  color,
  ink,
  pickLabel,
  dropLabel,
}: { plan: PlanGeometry; color: string; ink: string } & Pick<
  SceneProps,
  'pickLabel' | 'dropLabel'
>) {
  const line = useMemo(() => {
    const l = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(plan.points),
      new THREE.LineDashedMaterial({ color, dashSize: 0.012, gapSize: 0.008 }),
    );
    l.computeLineDistances();
    return l;
  }, [plan, color]);
  return (
    <>
      <primitive object={line} />
      {plan.pick && <Marker at={plan.pick} label={pickLabel} ink={ink} />}
      {plan.drop && <Marker at={plan.drop} label={dropLabel} ink={ink} />}
    </>
  );
}

function Marker({ at, label, ink }: { at: THREE.Vector3; label: string; ink: string }) {
  const ring = useMemo(() => {
    const curve = new THREE.EllipseCurve(0, 0, 0.03, 0.03, 0, Math.PI * 2);
    const pts = curve.getPoints(48).map((p) => new THREE.Vector3(p.x, 0, p.y));
    const l = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(pts),
      new THREE.LineDashedMaterial({ color: ink, dashSize: 0.008, gapSize: 0.006 }),
    );
    l.computeLineDistances();
    return l;
  }, [ink]);
  const sprite = useMemo(() => makeLabel(label, { strong: true }), [label]);
  useEffect(() => () => disposeLabel(sprite), [sprite]);
  return (
    <group position={[at.x, 0.001, at.z]}>
      <primitive object={ring} />
      <primitive object={sprite} position={[0, 0.005, 0.035]} />
    </group>
  );
}

function JointLabels({ robot }: { robot: RobotInstance }) {
  const invalidate = useThree((st) => st.invalidate);
  useEffect(() => {
    const sprites: THREE.Sprite[] = [];
    for (const j of robot.jointIds) {
      const h = robot.joints[j];
      if (!h) continue;
      const sprite = makeLabel(j);
      h.object.add(sprite);
      sprites.push(sprite);
    }
    invalidate();
    return () => {
      for (const sp of sprites) {
        sp.removeFromParent();
        disposeLabel(sp);
      }
      invalidate();
    };
  }, [robot, invalidate]);
  return null;
}

function CameraRig({
  rig,
  preset,
  resetKey,
}: {
  rig: ArmRig;
  preset: ViewPreset;
  resetKey: number;
}) {
  const camera = useThree((s) => s.camera);
  const controls = useThree((s) => s.controls) as unknown as {
    target: THREE.Vector3;
    update: () => void;
  } | null;
  const invalidate = useThree((s) => s.invalidate);
  useEffect(() => {
    camera.position.set(...rig.presets[preset]);
    if (controls) {
      controls.target.copy(rig.target);
      controls.update();
    } else {
      camera.lookAt(rig.target);
    }
    invalidate();
  }, [rig, preset, resetKey, camera, controls, invalidate]);
  return (
    <OrbitControls
      makeDefault
      target={rig.target}
      enableDamping={false}
      minDistance={rig.minDist}
      maxDistance={rig.maxDist}
    />
  );
}
