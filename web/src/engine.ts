import type { Candle } from './types';

export const tier = (s: number) => (s >= 85 ? 'crit' : s >= 70 ? 'high' : s >= 50 ? 'med' : 'low');
export const tierFromThresholds = (s: number, th: { medium: number; high: number; critical: number }) =>
  s >= th.critical ? 'crit' : s >= th.high ? 'high' : s >= th.medium ? 'med' : 'low';
export const pctStr = (x: number) => `${x >= 0 ? '+' : ''}${x.toFixed(2)}%`;
export const price = (x: number) =>
  x >= 1000 ? x.toLocaleString('en-IN', { maximumFractionDigits: 0 }) : x.toFixed(2);

export type ParsedUpload = { series: Record<string, Candle[]>; rows: number; dropped: { line: number; why: string }[]; columns: string[] };

/** Client-side CSV pre-validation/grouping; the server re-validates authoritatively on ingest. */
export function parseCsv(text: string, fallbackSym = 'MYDATA'): ParsedUpload {
  const lines = text.replace(/\r/g, '').split('\n').filter(l => l.trim().length);
  if (lines.length < 2) throw new Error('Need a header row and at least one data row.');
  const split = (l: string) => l.split(',').map(x => x.trim().replace(/^"|"$/g, ''));
  const header = split(lines[0]).map(h => h.toLowerCase());
  const find = (...names: string[]) => header.findIndex(h => names.includes(h));
  const iDt = find('datetime', 'timestamp', 'ts', 'date_time', 'time_stamp');
  const iDate = find('date'), iTime = find('time');
  const iO = find('open', 'o'), iH = find('high', 'h'), iL = find('low', 'l'), iC = find('close', 'c', 'adj close', 'adj_close'), iV = find('volume', 'vol', 'v');
  const iS = find('symbol', 'ticker', 'sym', 'scrip');
  const missing = [['open', iO], ['high', iH], ['low', iL], ['close', iC], ['volume', iV]].filter(([, i]) => i === -1).map(([n]) => n);
  if (missing.length) throw new Error(`Missing column${missing.length > 1 ? 's' : ''}: ${missing.join(', ')}`);
  if (iDt === -1 && iDate === -1 && iTime === -1) throw new Error('No datetime column found (looked for datetime, timestamp, date, time).');
  const series: Record<string, Candle[]> = {};
  const dropped: { line: number; why: string }[] = [];
  let rows = 0;
  for (let k = 1; k < lines.length; k++) {
    const f = split(lines[k]);
    rows++;
    const [o, h, l, c, v] = [iO, iH, iL, iC, iV].map(i => Number(f[i]));
    if ([o, h, l, c, v].some(x => !Number.isFinite(x))) { dropped.push({ line: k + 1, why: 'non-numeric price or volume' }); continue; }
    if (v < 0) { dropped.push({ line: k + 1, why: 'negative volume' }); continue; }
    if (h < Math.max(o, c) - 1e-9 || l > Math.min(o, c) + 1e-9) { dropped.push({ line: k + 1, why: 'high/low inconsistent with open/close' }); continue; }
    const raw = iDt !== -1 ? f[iDt] : [iDate !== -1 ? f[iDate] : '', iTime !== -1 ? f[iTime] : ''].join(' ');
    const m = raw.match(/(\d{1,2}):(\d{2})/);
    const t = m ? `${m[1].padStart(2, '0')}:${m[2]}` : raw.trim().slice(0, 10);
    const sym = (iS !== -1 && f[iS] ? f[iS] : fallbackSym).toUpperCase();
    (series[sym] ||= []).push({ t, o, h, l, c, v });
  }
  return { series, rows, dropped, columns: header };
}

/** Build a single-symbol CSV (datetime + OHLCV) for POST /ingest. */
export function toIngestCsv(rows: { iso?: string; t: string }[], candles: Candle[], dates?: string[]): string {
  const out = ['datetime,open,high,low,close,volume'];
  candles.forEach((c, i) => out.push(`${rows[i]?.iso ?? dates?.[i] ?? ''} ${c.t}:00,${c.o},${c.h},${c.l},${c.c},${c.v}`));
  return out.join('\n');
}

export function sampleCsv(): string {
  // Deterministic two-symbol sample with one pump, one dump, and two bad rows.
  const rows = ['datetime,symbol,open,high,low,close,volume'];
  const mk = (sym: string, base: number, seed: number, evAt: number, evKind: 'pump' | 'dump') => {
    let s = seed; const r = () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
    let p = base;
    for (let i = 0; i < 75; i++) {
      const mins = 9 * 60 + 15 + i * 5;
      const t = `${String(Math.floor(mins / 60)).padStart(2, '0')}:${String(mins % 60).padStart(2, '0')}`;
      const ev = i >= evAt && i < evAt + 4;
      const first = i === evAt;
      let drift = (r() - 0.5) * 0.007;
      let vMul = Math.exp((r() + r() - 1) * 0.5);
      if (ev) { drift = (evKind === 'dump' ? -1 : 1) * (first ? 0.028 : 0.008); vMul = first ? 6 : 2.5; }
      const o = p; const c = p * (1 + drift);
      const h = Math.max(o, c) * (1 + r() * 0.002), l = Math.min(o, c) * (1 - r() * 0.002);
      const v = Math.round((1 + 0.8 * Math.exp(-i / 6)) * vMul * 95000);
      rows.push(`2026-09-24 ${t}:00,${sym},${o.toFixed(2)},${h.toFixed(2)},${l.toFixed(2)},${c.toFixed(2)},${v}`);
      p = c;
    }
  };
  mk('MYSTOCK', 540, 101, 38, 'pump');
  mk('OTHERCO', 128, 103, 55, 'dump');
  rows.splice(20, 0, '2026-09-24 10:50:00,MYSTOCK,abc,551.2,548.0,550.1,91000');
  rows.splice(44, 0, '2026-09-24 12:50:00,MYSTOCK,552.0,549.0,551.5,550.9,-5');
  return rows.join('\n');
}

export type SymbolCsv = { symbol: string; csv: string; rows: number };

/** Split a possibly multi-symbol CSV into per-symbol CSVs the /ingest endpoint accepts. */
export function splitCsvBySymbol(text: string, fallbackSym = 'MYDATA'): SymbolCsv[] {
  const lines = text.replace(/\r/g, '').split('\n').filter(l => l.trim().length);
  if (lines.length < 2) throw new Error('Need a header row and at least one data row.');
  const split = (l: string) => l.split(',').map(x => x.trim().replace(/^"|"$/g, ''));
  const header = split(lines[0]).map(h => h.toLowerCase());
  const find = (...names: string[]) => header.findIndex(h => names.includes(h));
  const iDt = find('datetime', 'timestamp', 'ts', 'date_time', 'time_stamp');
  const iDate = find('date'), iTime = find('time');
  const iO = find('open', 'o'), iH = find('high', 'h'), iL = find('low', 'l'), iC = find('close', 'c', 'adj close', 'adj_close'), iV = find('volume', 'vol', 'v');
  const iS = find('symbol', 'ticker', 'sym', 'scrip');
  if (iDt === -1 && iDate === -1 && iTime === -1) throw new Error('No datetime column found (looked for datetime, timestamp, date, time).');
  const bySym: Record<string, string[]> = {};
  for (let k = 1; k < lines.length; k++) {
    const f = split(lines[k]);
    const dt = (iDt !== -1 ? f[iDt] : [iDate !== -1 ? f[iDate] : '', iTime !== -1 ? f[iTime] : ''].join(' ')).trim();
    const sym = (iS !== -1 && f[iS] ? f[iS] : fallbackSym).toUpperCase().replace(/[^A-Z0-9^._-]/g, '').slice(0, 20) || fallbackSym;
    (bySym[sym] ||= []).push([dt, f[iO], f[iH], f[iL], f[iC], f[iV]].join(','));
  }
  return Object.entries(bySym).map(([symbol, rows]) => ({
    symbol,
    csv: ['datetime,open,high,low,close,volume', ...rows].join('\n'),
    rows: rows.length,
  }));
}
