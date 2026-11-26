import { useMemo, useState } from 'react';
import type uPlot from 'uplot';
import { config } from '../config';
import { PANDA_CHART_GROUPS, PANDA_JOINTS } from '../config/panda';
import { useStore } from '../state/store';
import type { ArmSample } from '../state/types';
import { armWindow, snappedRange } from '../utils/armChart';
import { fmt, useT } from '../strings';
import { cssVar } from '../utils/css';
import { formatNumber } from '../utils/units';
import { Icon } from './Icon';
import { UPlotChart, type SeriesDef } from './UPlotChart';

type PandaTab = 'position' | 'velocity' | 'eef';
const TABS: PandaTab[] = ['position', 'velocity', 'eef'];
const EEF_AXES = ['x', 'y', 'z'] as const;
const EEF_COLORS = ['--panda-eef-x', '--panda-eef-y', '--panda-eef-z'];

/** Franka Panda (LIBERO demo): joint positions, estimated velocities and end-effector path. */
export function PandaCharts() {
  const t = useT();
  const lang = useStore((s) => s.lang);
  const samples = useStore((s) => s.arm);
  const pausedAt = useStore((s) => s.chartPausedAt);
  const pause = useStore((s) => s.pauseCharts);
  const [tab, setTab] = useState<PandaTab>('position');
  const [hidden, setHidden] = useState<Record<string, boolean>>({});
  const [cursor, setCursor] = useState<number | null>(null);

  const last = samples[samples.length - 1];
  const end = pausedAt ?? last?.t ?? 0;
  const win = useMemo(() => armWindow(samples, end), [samples, end]);
  const live = pausedAt === null;
  const at = !live && cursor !== null ? win[cursor] : win[win.length - 1];
  const x = win.map((s) => (s.t - end) / 1000);

  // End effector: one small chart per axis, each on its own scale (z sits near 1 m while
  // x and y move around 0, so a shared scale would flatten them).
  const groups: { id: string; title: string; keys: number[] }[] =
    tab === 'eef'
      ? EEF_AXES.map((a, k) => ({ id: a, title: `${t.panda.eef} ${a}`, keys: [k] }))
      : PANDA_CHART_GROUPS.map((g) => ({ id: g.id, title: t.panda.groups[g.id], keys: g.joints }));

  const valueOf = (s: ArmSample, k: number): number | null => {
    if (tab === 'eef') return s.eefMm ? s.eefMm[k]! : null;
    return (tab === 'velocity' ? s.v[k] : s.q[k]) ?? null;
  };
  const nameOf = (k: number) => (tab === 'eef' ? EEF_AXES[k]! : PANDA_JOINTS[k]!.id);
  const colorVar = (k: number) => (tab === 'eef' ? EEF_COLORS[k]! : PANDA_JOINTS[k]!.color);
  const unit = tab === 'eef' ? ' mm' : tab === 'velocity' ? '°/s' : '°';
  const key =
    tab === 'eef' ? t.panda.keyEef : tab === 'velocity' ? t.panda.keyVelocity : t.panda.keyState;

  return (
    <section className="rb-card" aria-labelledby="panda-charts-title" data-testid="panda-charts">
      <div className="rb-card__head app-center">
        <h2 className="rb-card__title app-flex1" id="panda-charts-title">
          {t.panda.chartsTitle}
        </h2>
        <div className="rb-card__actions">
          {live ? (
            <button type="button" className="rb-btn rb-btn--live" aria-pressed="true">
              <span className="rb-live-dot" />
              {t.charts.live}
            </button>
          ) : (
            <button type="button" className="rb-btn" onClick={() => pause(null)}>
              <Icon name="play" />
              {t.charts.backToLive}
            </button>
          )}
        </div>
      </div>
      <div className="rb-card__body app-stack-3">
        <div className="app-row-wrap">
          <div className="rb-seg" role="tablist" aria-label={t.charts.tabsLabel}>
            {TABS.map((x) => (
              <button
                key={x}
                type="button"
                role="tab"
                aria-selected={tab === x}
                onClick={() => setTab(x)}
              >
                {t.panda.tabs[x]}
              </button>
            ))}
          </div>
          <div className="rb-legend app-muted">
            <span className="rb-legend__item">
              <span className="rb-key" />
              {key}
            </span>
          </div>
        </div>
        {groups.map((g) => {
          const series: SeriesDef[] = g.keys.map((k) => ({
            key: `${tab}-${k}`,
            color: cssVar(colorVar(k), '#64748b'),
            width: 2,
            show: !hidden[`${tab}-${k}`],
          }));
          const cols = g.keys.map((k) => win.map((s) => valueOf(s, k)));
          const yRange =
            tab === 'velocity'
              ? snappedRange(cols.flat(), 15, 30)
              : tab === 'eef'
                ? snappedRange(cols.flat(), 20, 40)
                : snappedRange(cols.flat(), 30, 60);
          const data: uPlot.AlignedData = [x, ...cols];
          const title = g.title;
          const names = g.keys.map(nameOf).join(', ');
          return (
            <div className="rb-chart" key={`${tab}-${g.id}`}>
              <h3 className="rb-chart__title">
                {title} <span>· {names}</span>
              </h3>
              <UPlotChart
                series={series}
                data={data}
                xRange={[-config.chartWindowMs / 1000, 0]}
                yRange={yRange}
                height={tab === 'eef' ? 90 : 150}
                yAxisSize={tab === 'eef' ? 56 : 44}
                ariaLabel={fmt(t.charts.chartAria, { group: title, joints: names })}
                onHover={() => live && pause(end)}
                onCursor={setCursor}
              />
              <div className="rb-legend">
                {g.keys.map((k) => {
                  const id = `${tab}-${k}`;
                  const v = at ? valueOf(at, k) : null;
                  return (
                    <label key={id} className="rb-legend__item">
                      <input
                        type="checkbox"
                        checked={!hidden[id]}
                        onChange={() => setHidden({ ...hidden, [id]: !hidden[id] })}
                        aria-label={fmt(t.charts.toggle, { joint: nameOf(k) })}
                      />
                      <span className="rb-swatch" style={{ background: `var(${colorVar(k)})` }} />
                      <span className="rb-mono">{nameOf(k)}</span>
                      <span className="rb-legend__val">
                        {formatNumber(v, tab === 'eef' ? 0 : 1, lang)}
                        {unit}
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>
          );
        })}
        <p className="app-panda-note app-m0">{t.panda.chartNote}</p>
      </div>
    </section>
  );
}
