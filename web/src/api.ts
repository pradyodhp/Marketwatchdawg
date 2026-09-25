import type { ApiAlert, ApiSettings, ScoreBar } from './types';

const BASE = '';

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    let detail = `${res.status}`;
    try { detail = (await res.json()).detail ?? detail; } catch { /* non-JSON error */ }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

type ScoreBarWire = Omit<ScoreBar, 't' | 'iso'> & { t: string };

const fmtTime = (iso: string) => {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
};

export function mapBar(b: ScoreBarWire): ScoreBar {
  const { t, ...rest } = b;
  return { ...rest, iso: t, t: fmtTime(t) };
}

export const api = {
  stocks: () => req<{ symbols: string[]; count: number }>('/stocks'),
  universe: () => req<{ entries: Record<string, { name: string; sector: string; industry: string }> }>('/universe'),
  scores: (limit = 150, symbol?: string) =>
    req<{ symbols: Record<string, ScoreBarWire[]>; batches: number; elapsed_ms: number }>(
      `/scores?limit=${limit}${symbol ? `&symbol=${encodeURIComponent(symbol)}` : ''}`,
    ).then(r => ({ ...r, symbols: Object.fromEntries(Object.entries(r.symbols).map(([k, v]) => [k, v.map(mapBar)])) })),
  alerts: () => req<ApiAlert[]>('/alerts'),
  act: (id: string, action: 'acknowledge' | 'escalate' | 'resolve' | 'reopen', note?: string) =>
    req<ApiAlert>(`/alerts/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ action, note: note || null }),
    }),
  detect: () => req<{ symbols: number; batches: number; alerts: number; elapsed_ms: number; cached: boolean }>('/detect', { method: 'POST' }),
  settings: () => req<ApiSettings>('/settings'),
  putSettings: (update: Partial<{
    risk_scoring: { weights: Record<string, number>; thresholds: Record<string, number> };
    detectors: Record<string, number>;
    cooldown: { window_bars: number };
    notifications: { webhook_url: string; min_severity: string };
  }>) => req<ApiSettings>('/settings', { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify(update) }),
  ingest: (symbol: string, body: string | ArrayBuffer, isParquet: boolean) =>
    req<{ symbol: string; rows_received: number; rows_loaded: number; rows_dropped: number; invalid_reasons: Record<string, number> }>(
      `/ingest?symbol=${encodeURIComponent(symbol)}`, {
        method: 'POST',
        headers: { 'content-type': isParquet ? 'application/x-parquet' : 'text/csv' },
        body,
      },
    ),
};
