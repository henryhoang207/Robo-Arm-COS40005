import { useEffect, useState } from 'react';
import { config } from '../config';
import { useLiberoMode } from '../config/protocol';
import { useT } from '../strings';
import { CameraTile } from '../components/CameraTile';
import { CommandPanel } from '../components/CommandPanel';
import { JointTable } from '../components/JointTable';
import { PandaCharts } from '../components/PandaCharts';
import { PandaJointTable } from '../components/PandaJointTable';
import { RobotViewer3D } from '../components/RobotViewer3D';
import { TaskHistory } from '../components/TaskHistory';
import { TrajectoryCharts } from '../components/TrajectoryCharts';
import type { DerivedStatus } from '../state/deriveStatus';
import { useStore } from '../state/store';

type TabletTab = 'control' | 'joints' | 'charts';

function useTabletLayout() {
  const [tablet, setTablet] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(max-width: 1100px)').matches,
  );

  useEffect(() => {
    const media = window.matchMedia('(max-width: 1100px)');
    const update = () => setTablet(media.matches);
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);

  return tablet;
}

export function MonitoringPage({ derived, noUrdf }: { derived: DerivedStatus; noUrdf: boolean }) {
  const large = useStore((s) => s.largeSlot);
  const lang = useStore((s) => s.lang);
  // LIBERO demo: same layout as the SO-101 console, switching the 3D viewer, joint table
  // and charts to the 7-DOF Franka Panda arm.
  const libero = useLiberoMode();
  const t = useT();
  const bigCamera = config.cameras.find((c) => c.id === large);
  const arm = libero ? 'panda' : 'so101';
  const tablet = useTabletLayout();
  const liberoNote = (
    <section className="rb-card" data-testid="libero-note">
      <div className="rb-card__body">
        <p className="app-libero-note app-m0">{t.command.liberoScene}</p>
      </div>
    </section>
  );
  const [tabletTab, setTabletTab] = useState<TabletTab>('control');
  // LIBERO: the Franka Panda's own table and charts; SO-101 otherwise.
  const jointTable = libero ? (
    <PandaJointTable derived={derived} />
  ) : (
    <JointTable derived={derived} />
  );
  const charts = libero ? <PandaCharts /> : <TrajectoryCharts />;

  const visual = (
    <section
      className="rb-tablet-visual"
      aria-label={lang === 'vi' ? 'Khu vực quan sát robot' : 'Robot visual monitoring'}
    >
      <div className="rb-tablet-visual__main">
        {bigCamera ? (
          <CameraTile camera={bigCamera} stale={derived.stale} large />
        ) : (
          <RobotViewer3D arm={arm} forcePlaceholder={noUrdf} />
        )}
      </div>
      <div className="rb-cams rb-tablet-cams">
        {bigCamera && <RobotViewer3D arm={arm} compact forcePlaceholder={noUrdf} />}
        {config.cameras
          .filter((c) => c.id !== bigCamera?.id)
          .map((c) => (
            <CameraTile key={c.id} camera={c} stale={derived.stale} />
          ))}
      </div>
    </section>
  );

  if (!tablet) {
    return (
      <div className="rb-main">
        <div className="rb-col rb-col--left">
          <CommandPanel derived={derived} />
          <TaskHistory />
        </div>
        <div className="rb-col rb-col--center">
          {bigCamera ? (
            <CameraTile camera={bigCamera} stale={derived.stale} large />
          ) : (
            <RobotViewer3D arm={arm} forcePlaceholder={noUrdf} />
          )}
          <div className="rb-cams">
            {bigCamera && <RobotViewer3D arm={arm} compact forcePlaceholder={noUrdf} />}
            {config.cameras
              .filter((c) => c.id !== bigCamera?.id)
              .map((c) => (
                <CameraTile key={c.id} camera={c} stale={derived.stale} />
              ))}
          </div>
        </div>
        <div className="rb-col rb-col--right">
          {libero && liberoNote}
          {jointTable}
          {charts}
        </div>
      </div>
    );
  }

  const tabs: { id: TabletTab; label: string }[] =
    lang === 'vi'
      ? [
          { id: 'control', label: 'Điều khiển' },
          { id: 'joints', label: 'Trạng thái khớp' },
          { id: 'charts', label: 'Biểu đồ' },
        ]
      : [
          { id: 'control', label: 'Control' },
          { id: 'joints', label: 'Joint status' },
          { id: 'charts', label: 'Charts' },
        ];

  return (
    <div className="rb-tablet-layout">
      {visual}
      <section
        className="rb-tablet-panel"
        aria-label={lang === 'vi' ? 'Bảng điều khiển' : 'Control panel'}
      >
        <div
          className="rb-tablet-tabs"
          role="tablist"
          aria-label={lang === 'vi' ? 'Các khu vực điều khiển' : 'Control sections'}
        >
          {tabs.map((tab) => (
            <button
              className="rb-tablet-tabs__button"
              key={tab.id}
              id={`tablet-tab-${tab.id}`}
              type="button"
              role="tab"
              aria-selected={tabletTab === tab.id}
              aria-controls={`tablet-panel-${tab.id}`}
              onClick={() => setTabletTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div
          className="rb-tablet-panel__content"
          id={`tablet-panel-${tabletTab}`}
          role="tabpanel"
          aria-labelledby={`tablet-tab-${tabletTab}`}
        >
          {tabletTab === 'control' && (
            <div className="rb-tablet-control">
              <CommandPanel derived={derived} />
              <TaskHistory />
              {libero && liberoNote}
            </div>
          )}
          {tabletTab === 'joints' && jointTable}
          {tabletTab === 'charts' && charts}
        </div>
      </section>
    </div>
  );
}
