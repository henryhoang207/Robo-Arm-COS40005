import { describe, expect, it } from 'vitest';
import type { ArmSample } from '../state/types';
import { armWindow, snappedRange } from './armChart';

const s = (t: number): ArmSample => ({
  t,
  ts: t,
  q: [0, 0, 0, 0, 0, 0, 0],
  v: [0, 0, 0, 0, 0, 0, 0],
  gripper: null,
  eefMm: null,
  step: null,
  plannedEefMm: null,
});

describe('armChart', () => {
  it('keeps the last 10 s up to the end time', () => {
    const all = [0, 5_000, 12_000, 19_000, 21_000].map(s);
    expect(armWindow(all, 20_000).map((x) => x.t)).toEqual([12_000, 19_000]);
  });

  it('snaps the y range and keeps a minimum span', () => {
    expect(snappedRange([-138.2, 150.1], 30, 60)).toEqual([-150, 180]);
    expect(snappedRange([10, 12], 30, 60)).toEqual([-30, 30]);
    expect(snappedRange([null, Number.NaN], 30, 60)).toEqual([-30, 30]);
  });
});
