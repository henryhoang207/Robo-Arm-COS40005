import { config } from '../config';
import type { ArmSample } from '../state/types';

/** Samples of the last chart window ending at `end` (browser time, ms). */
export function armWindow(samples: ArmSample[], end: number): ArmSample[] {
  const from = end - config.chartWindowMs;
  let lo = samples.length;
  while (lo > 0 && samples[lo - 1]!.t >= from) lo--;
  let hi = samples.length;
  while (hi > lo && samples[hi - 1]!.t > end) hi--;
  return samples.slice(lo, hi);
}

/**
 * Y range from the visible values, snapped to `step` so the plot is not rebuilt at every
 * sample, and never narrower than `minSpan`.
 */
export function snappedRange(
  values: (number | null)[],
  step: number,
  minSpan: number,
): [number, number] {
  const finite = values.filter((v): v is number => v !== null && Number.isFinite(v));
  if (finite.length === 0) return [-minSpan / 2, minSpan / 2];
  let lo = Math.floor(Math.min(...finite) / step) * step;
  let hi = Math.ceil(Math.max(...finite) / step) * step;
  if (hi - lo < minSpan) {
    const mid = (lo + hi) / 2;
    lo = Math.floor((mid - minSpan / 2) / step) * step;
    hi = lo + Math.ceil(minSpan / step) * step;
  }
  return [lo, hi];
}
