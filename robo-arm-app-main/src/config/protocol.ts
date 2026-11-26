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

// Settled answers only: a protocol, or `null` when the BE has no such endpoint (404, an older
// BE). A network error or a BE that is still starting is not cached, so the page asks again.
let settled: Promise<ProtocolDef | null> | null = null;
const RETRY_MS = 2000;

class NotYet extends Error {}

async function fetchProtocol(base: string): Promise<ProtocolDef | null> {
  const r = await fetch(`${base}/api/v1/protocol`);
  if (r.status === 404) return null;
  if (!r.ok) throw new NotYet(String(r.status));
  const d = (await r.json()) as ProtocolDef | null;
  return d && typeof d.free_text === 'boolean' ? d : null;
}

export function loadProtocol(): Promise<ProtocolDef | null> {
  const base = apiBase();
  if (base === null) return Promise.resolve(null);
  if (settled === null) {
    const attempt = fetchProtocol(base);
    settled = attempt;
    attempt.catch(() => {
      if (settled === attempt) settled = null; // not settled: the next call fetches again
    });
  }
  return settled;
}

/** Test hook: forget the cached answer. */
export function resetProtocolCache(): void {
  settled = null;
}

/** null on the mock, before the answer, or when the BE has no protocol endpoint. Keeps asking
 * every 2 s while the BE is unreachable, so a page opened before the BE is up still switches to
 * the LIBERO view once it answers. */
export function useProtocol(): ProtocolDef | null {
  const [protocol, setProtocol] = useState<ProtocolDef | null>(null);
  useEffect(() => {
    if (apiBase() === null) return;
    let alive = true;
    let timer: number | undefined;
    const tryLoad = () => {
      loadProtocol().then(
        (p) => alive && setProtocol(p),
        () => {
          if (alive) timer = window.setTimeout(tryLoad, RETRY_MS);
        },
      );
    };
    tryLoad();
    return () => {
      alive = false;
      window.clearTimeout(timer);
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
