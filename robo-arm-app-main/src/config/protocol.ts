// The command the BE accepts (`GET /api/v1/protocol`). With `free_text` (the LIBERO demo,
// SO101_SIM_LINK=libero) the web shows a prompt box instead of template + object.
import { useEffect, useState } from 'react';
import { apiBase } from '../transport';

export interface ProtocolDef {
  id: string;
  template_id: string;
  /** For LIBERO: the scene, e.g. "libero_goal/8". */
  object: string;
  ui_text: string;
  free_text: boolean;
  max_text_chars: number;
  suggestions: string[];
}

export interface GoalPreview {
  scored: boolean;
  label: string | null;
  source: string | null;
  reason: string | null;
}

let cached: Promise<ProtocolDef | null> | null = null;

function loadProtocol(): Promise<ProtocolDef | null> {
  const base = apiBase();
  if (base === null) return Promise.resolve(null);
  if (cached === null) {
    cached = fetch(`${base}/api/v1/protocol`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d: ProtocolDef | null) => (d && typeof d.free_text === 'boolean' ? d : null))
      .catch(() => {
        cached = null; // try again next time
        return null;
      });
  }
  return cached;
}

/** null on the mock, before the answer, or when the BE is older than this endpoint. */
export function useProtocol(): ProtocolDef | null {
  const [protocol, setProtocol] = useState<ProtocolDef | null>(null);
  useEffect(() => {
    let alive = true;
    void loadProtocol().then((p) => alive && setProtocol(p));
    return () => {
      alive = false;
    };
  }, []);
  return protocol;
}

/** True when the BE runs the LIBERO demo: no SO-101 arm, so its 3D model and joints are hidden. */
export function useLiberoMode(): boolean {
  return useProtocol()?.free_text === true;
}

/** What the demo bridge would score `text` against; null when unknown. */
export async function previewGoal(text: string, signal?: AbortSignal): Promise<GoalPreview | null> {
  const base = apiBase();
  if (base === null) return null;
  try {
    const r = await fetch(`${base}/api/v1/goal-preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
      signal,
    });
    if (!r.ok) return null;
    const data = (await r.json()) as { goal?: GoalPreview };
    return data.goal ?? null;
  } catch {
    return null;
  }
}
