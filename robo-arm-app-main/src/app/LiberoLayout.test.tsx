import { act, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { applyMessage, initialUi, useStore } from '../state/store';
import { MockTransport } from '../transport/MockTransport';
import { App } from './App';

// Pretend the BE runs the LIBERO demo (GET /api/v1/protocol -> free_text: true).
vi.mock('../config/protocol', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../config/protocol')>();
  return { ...actual, useLiberoMode: () => true };
});

describe('LIBERO mode keeps the SO-101 console layout', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    localStorage.clear();
    useStore.getState().reset();
    useStore.setState({ ...initialUi(), lang: 'vi' });
  });
  afterEach(() => vi.useRealTimers());

  it('shows the 3D card (marked not applicable), both cameras, joint table and charts', async () => {
    render(<App createTransport={() => new MockTransport('idle')} scenario="idle" />);
    await act(async () => {
      vi.advanceTimersByTime(1500);
    });

    // 3D card stays in the large slot, with a message instead of the SO-101 model.
    expect(screen.getByText('Mô hình 3D · thời gian thực')).toBeInTheDocument();
    expect(screen.getByTestId('viewer-not-applicable')).toHaveTextContent('Franka Panda');
    // Right column as in the original layout: the Panda's own joint table and charts.
    expect(screen.getByTestId('libero-note')).toBeInTheDocument();
    expect(screen.getByText('Trạng thái khớp · Franka Panda')).toBeInTheDocument();
    expect(screen.getByText('Quỹ đạo theo thời gian · Franka Panda')).toBeInTheDocument();
    expect(screen.queryByText('Trạng thái khớp')).toBeNull(); // not the SO-101 table
    expect(screen.getByTestId('panda-joints').querySelectorAll('tbody tr')).toHaveLength(8);
    // Both cameras are small tiles under the 3D card; none is forced into the large slot.
    expect(useStore.getState().largeSlot).toBe('viewer');
    expect(document.querySelectorAll('.rb-cams .rb-camera')).toHaveLength(2);
  });

  it('fills the Panda table from arm_state messages', async () => {
    render(<App createTransport={() => new MockTransport('idle')} scenario="idle" />);
    await act(async () => {
      vi.advanceTimersByTime(1500);
    });
    const send = (ts: number, j4: number, gripper: 'open' | 'closed') =>
      useStore.setState((s) => ({
        ...applyMessage(
          s,
          {
            type: 'arm_state',
            ts,
            arm: 'panda',
            jointsDeg: [0.6, 11.6, -0.9, j4, 0.2, 150.1, 45.3],
            gripper,
            eefMm: [-201.6, 12.4, 1164.8],
            step: 31,
          },
          ts,
        ),
      }));
    await act(async () => {
      send(10_000, -138.2, 'open');
      send(10_100, -137.2, 'closed');
    });
    const table = screen.getByTestId('panda-joints');
    const row4 = within(table).getByText('joint4').closest('tr')!;
    expect(row4).toHaveTextContent('−137,2'); // vi: comma decimals, true minus sign
    expect(
      Number(row4.querySelector('[role=meter]')!.getAttribute('aria-valuenow')),
    ).toBeGreaterThan(0);
    expect(within(table).getByText('Đóng')).toBeInTheDocument(); // gripper from the command
    expect(screen.getByTestId('panda-eef')).toHaveTextContent('x −202 · y 12 · z 1165');
    expect(screen.getByTestId('panda-eef')).toHaveTextContent('Bước mô phỏng 31');
    // Velocity is estimated from positions: joint4 moved +1° in 0.1 s.
    const v = useStore.getState().arm[1]!.v[3]!;
    expect(v).toBeGreaterThan(0);
  });
});
