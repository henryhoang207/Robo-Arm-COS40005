import { Canvas } from '@react-three/fiber';
import { useEffect, useState } from 'react';
import type { ViewPreset } from '../config';
import { useStore } from '../state/store';
import type { Layers } from '../state/types';
import { loadRobotKit, type ArmKind, type RobotKit } from './robotKit';
import { RobotScene } from './Scene';

export interface ViewerCanvasProps {
  arm: ArmKind;
  forcePlaceholder: boolean;
  layers: Layers;
  selected: string | null;
  preset: ViewPreset;
  resetKey: number;
  pickLabel: string;
  dropLabel: string;
  ariaLabel: string;
  loading: React.ReactNode;
  onEe: (mm: [number, number, number] | null) => void;
}

const INITIAL_CAM: Record<ArmKind, [number, number, number]> = {
  so101: [0.42, 0.34, 0.42],
  panda: [1.25, 0.95, 1.25],
};

/** Lazy-loaded chunk: three.js, the URDF loader and the R3F canvas. */
export default function ViewerCanvas({
  arm,
  forcePlaceholder,
  loading,
  ariaLabel,
  ...scene
}: ViewerCanvasProps) {
  const setRobot = useStore((s) => s.setRobot);
  const [loaded, setLoaded] = useState<{ arm: ArmKind; kit: RobotKit } | null>(null);

  useEffect(() => {
    let alive = true;
    loadRobotKit({ arm, forcePlaceholder }).then((kit) => {
      if (!alive) return;
      setLoaded({ arm, kit });
      setRobot(kit.source, arm === 'so101' ? kit.limits : {});
    });
    return () => {
      alive = false;
    };
  }, [arm, forcePlaceholder, setRobot]);

  if (!loaded || loaded.arm !== arm) return <>{loading}</>;
  return (
    <Canvas
      frameloop="demand"
      dpr={[1, 2]}
      camera={{ fov: 40, near: 0.01, far: 30, position: INITIAL_CAM[arm] }}
      aria-label={ariaLabel}
      role="img"
    >
      <RobotScene arm={arm} kit={loaded.kit} {...scene} />
    </Canvas>
  );
}
