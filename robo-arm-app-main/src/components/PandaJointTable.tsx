import { config, type AngleUnit } from '../config';
import { PANDA_JOINTS } from '../config/panda';
import type { DerivedStatus } from '../state/deriveStatus';
import { useStore } from '../state/store';
import { fmt, useT } from '../strings';
import { formatNumber } from '../utils/units';
import { Icon } from './Icon';
import { Tooltip } from './Tooltip';

const UNITS: AngleUnit[] = ['deg', 'rad'];
const toUnit = (deg: number, unit: AngleUnit) => (unit === 'rad' ? (deg * Math.PI) / 180 : deg);

function PandaLimitBar({
  id,
  value,
  range,
}: {
  id: string;
  value: number | null;
  range: [number, number];
}) {
  const t = useT();
  const [lo, hi] = range;
  const ratio = value === null ? null : Math.min(1, Math.max(0, (value - lo) / (hi - lo)));
  const near =
    ratio !== null && (ratio > config.nearLimitRatio || ratio < 1 - config.nearLimitRatio);
  const pct = ratio === null ? 0 : Math.round(ratio * 100);
  const bar = (
    <span
      className={`rb-limit ${near ? 'is-near' : ''}`}
      role="meter"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct}
      aria-label={fmt(t.joints.limitAria, { joint: id, pct })}
    >
      {ratio !== null && <span className="rb-limit__mark" style={{ left: `${ratio * 100}%` }} />}
    </span>
  );
  if (!near) return bar;
  return (
    <span className="rb-limit-wrap">
      {bar}
      <Icon name="warn" label={t.joints.nearLimit} />
    </span>
  );
}

/**
 * The LIBERO demo's Franka Panda: 7 measured joints, gripper (open/closed, from the command)
 * and end-effector position. Same card and table style as the SO-101 joint table; no command
 * or error columns, because the bridge has no per-joint command.
 */
export function PandaJointTable({ derived }: { derived: DerivedStatus }) {
  const t = useT();
  const lang = useStore((s) => s.lang);
  const unit = useStore((s) => s.unit);
  const setUnit = useStore((s) => s.setUnit);
  const latest = useStore((s) => s.arm[s.arm.length - 1]);
  const cell = derived.stale ? 'is-stale' : '';
  const dec = unit === 'deg' ? 1 : 3;
  const angle = unit === 'deg' ? t.joints.unitSuffix.deg : t.joints.unitSuffix.rad;
  const speed = unit === 'deg' ? t.joints.unitSuffix.degS : t.joints.unitSuffix.radS;
  const num = (v: number | undefined) =>
    v === undefined ? '—' : formatNumber(toUnit(v, unit), dec, lang);

  return (
    <section className="rb-card" aria-labelledby="panda-joints-title" data-testid="panda-joints">
      <div className="rb-card__head app-center">
        <div className="app-flex1">
          <h2 className="rb-card__title" id="panda-joints-title">
            {t.panda.jointsTitle}
          </h2>
          <p className="rb-card__sub app-m0">{t.panda.jointsSub}</p>
        </div>
        <div className="rb-seg" role="group" aria-label={t.joints.unitLabel}>
          {UNITS.map((u) => (
            <button key={u} type="button" aria-pressed={unit === u} onClick={() => setUnit(u)}>
              {t.joints.units[u]}
            </button>
          ))}
        </div>
      </div>
      <div className="app-table-scroll">
        <table className="rb-joints">
          <thead>
            <tr>
              <th scope="col">{t.joints.cols.joint}</th>
              <th scope="col">
                {t.joints.cols.position} {angle}
              </th>
              <th scope="col">
                {t.joints.cols.velocity} {speed}
                <br />
                <span className="rb-tag">{t.joints.estimated}</span>
              </th>
              <th scope="col">
                <Tooltip content={t.panda.limitTip} align="end">
                  {(id) => (
                    <span className="rb-term" tabIndex={0} aria-describedby={id}>
                      {t.joints.cols.limit}
                    </span>
                  )}
                </Tooltip>
              </th>
            </tr>
          </thead>
          <tbody>
            {PANDA_JOINTS.map((j, i) => (
              <tr key={j.id} data-joint={j.id}>
                <td>
                  <span className="rb-joint">
                    <span className="rb-joint__swatch" style={{ background: `var(${j.color})` }} />
                    <span className="rb-joint__name">{j.id}</span>
                    <span className="rb-joint__desc">{t.panda.desc[i]}</span>
                  </span>
                </td>
                <td className={cell}>{num(latest?.q[i])}</td>
                <td className={cell}>{num(latest?.v[i])}</td>
                <td style={{ textAlign: 'left' }}>
                  <PandaLimitBar id={j.id} value={latest?.q[i] ?? null} range={j.limitDeg} />
                </td>
              </tr>
            ))}
            <tr data-joint="gripper">
              <td>
                <span className="rb-joint">
                  <span
                    className="rb-joint__swatch"
                    style={{ background: 'var(--joint-gripper)' }}
                  />
                  <span className="rb-joint__name">{t.panda.gripper}</span>
                  <span className="rb-joint__desc">{t.panda.gripperNote}</span>
                </span>
              </td>
              <td className={cell} colSpan={3} style={{ textAlign: 'left' }}>
                {latest?.gripper ? t.panda.gripperState[latest.gripper] : '—'}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div className="rb-card__foot app-foot">
        <span data-testid="panda-eef">
          <b>
            {t.panda.eef} ({t.panda.eefUnit})
          </b>{' '}
          {latest?.eefMm
            ? `x ${formatNumber(latest.eefMm[0], 0, lang)} · y ${formatNumber(latest.eefMm[1], 0, lang)} · z ${formatNumber(latest.eefMm[2], 0, lang)}`
            : '—'}
          {latest?.step !== null && latest?.step !== undefined && (
            <>
              {' · '}
              {t.panda.step} {latest.step}
            </>
          )}
        </span>
        <span>{latest ? t.panda.foot : t.panda.noData}</span>
      </div>
    </section>
  );
}
