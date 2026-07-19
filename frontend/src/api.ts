import type { Lineup, OptimizeResponse, OptimizeSettings, Player, PlayerAdjustment } from './types';

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ?? 'http://localhost:8000';

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === 'string') detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function fetchSampleSlate(): Promise<Player[]> {
  return handle(await fetch(`${API_BASE}/api/sample`));
}

export async function uploadCsv(file: File): Promise<Player[]> {
  const form = new FormData();
  form.append('file', file);
  return handle(await fetch(`${API_BASE}/api/upload`, { method: 'POST', body: form }));
}

export async function optimize(
  players: Player[],
  adjustments: PlayerAdjustment[],
  settings: OptimizeSettings,
): Promise<OptimizeResponse> {
  return handle(
    await fetch(`${API_BASE}/api/optimize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ players, adjustments, settings }),
    }),
  );
}

export async function exportDkCsv(lineups: Lineup[], sport: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sport, lineups }),
  });
  if (!res.ok) throw new Error('Export failed');
  return res.text();
}
