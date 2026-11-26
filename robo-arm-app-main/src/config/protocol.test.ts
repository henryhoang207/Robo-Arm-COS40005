import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../transport', () => ({ apiBase: () => '' }));

import { resetProtocolCache, useProtocol } from './protocol';

const PROTOCOL = {
  id: 'libero-goal8-v1',
  template_id: 'libero_prompt',
  object: 'libero_goal/8',
  ui_text: 'put the bowl on the plate',
  free_text: true,
  max_text_chars: 300,
  suggestions: [],
};

describe('useProtocol', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    resetProtocolCache();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('keeps asking while the BE is not up, then switches to the protocol', async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('connection refused'))
      .mockResolvedValueOnce(new Response('starting', { status: 503 }))
      .mockResolvedValue(new Response(JSON.stringify(PROTOCOL), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useProtocol());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current).toBeNull();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(result.current).toBeNull(); // 503: still not up
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(result.current?.free_text).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('stops asking when the BE has no protocol endpoint (404)', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('', { status: 404 }));
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useProtocol());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    expect(result.current).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
