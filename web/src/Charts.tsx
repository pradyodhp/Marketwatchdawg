import React, { useId } from 'react';
import type { Candle } from './types';
import { useCountUp } from './hooks';
import { tier } from './engine';

const W = 600;

function scaleY(vals: number[], h: number, pad = 6) {
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const span = hi - lo || 1;
  return (v: number) => pad + (h - 2 * pad) * (1 - (v - lo) / span);
}

export function Spark({ values, up }: { values: number[]; up: boolean }) {
  const h = 32; const y = scaleY(values, h, 3);
  const d = values.map((v, i) => `${i ? 'L' : 'M'}${(i / Math.max(1, values.length - 1)) * 100},${y(v)}`).join(' ');
  return <svg className={`mx-spark ${up ? 'is-up' : 'is-down'}`} viewBox={`0 0 100 ${h}`} preserveAspectRatio="none" aria-hidden><path d={d} pathLength={1} className="mx-draw" /></svg>;
}

export function CandleChart({ series, upto, marks = [], highlight, height = 220 }: { series: Candle[]; upto?: number; marks?: number[]; highlight?: [number, number]; height?: number }) {
  const data = series.slice(0, (upto ?? series.length - 1) + 1);
  const n = series.length;
  const ph = height * 0.72, vh = height * 0.22;
  const all = data.flatMap(c => [c.h, c.l]);
  const y = scaleY(all.length ? all : [0, 1], ph, 8);
  const vmax = Math.max(1, ...data.map(c => c.v));
  const bw = W / n;
  const gid = useId().replace(/:/g, '');
  return <div className="mx-chart" style={{ height }}>
    <svg viewBox={`0 0 ${W} ${height}`} preserveAspectRatio="none" role="img" aria-label="Candlestick chart with volume">
      <defs><linearGradient id={`hl${gid}`} x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="var(--mx-accent)" stopOpacity=".28" /><stop offset="1" stopColor="var(--mx-accent)" stopOpacity="0" /></linearGradient></defs>
      {[0.25, 0.5, 0.75].map(g => <line key={g} x1={0} x2={W} y1={ph * g} y2={ph * g} className="mx-grid" />)}
      {highlight && <rect className="mx-hl" x={highlight[0] * bw} width={(highlight[1] - highlight[0] + 1) * bw} y={0} height={height} fill={`url(#hl${gid})`} />}
      {data.map((c, i) => {
        const up = c.c >= c.o; const x = i * bw + bw / 2;
        const top = y(Math.max(c.o, c.c)), bot = y(Math.min(c.o, c.c));
        const vbh = (c.v / vmax) * vh;
        const last = i === data.length - 1;
        return <g key={i} className={`mx-candle ${up ? 'is-up' : 'is-down'} ${last ? 'is-last' : ''} ${marks.includes(i) ? 'is-marked' : ''}`} style={{ ['--d' as string]: `${Math.min(i, 60) * 8}ms` }}>
          <line x1={x} x2={x} y1={y(c.h)} y2={y(c.l)} />
          <rect x={x - bw * 0.34} width={bw * 0.68} y={top} height={Math.max(1, bot - top)} rx={1} />
          <rect className="mx-vol" x={x - bw * 0.34} width={bw * 0.68} y={height - vbh} height={vbh} />
        </g>;
      })}
    </svg>
    {marks.filter(m => m < data.length).map(m => <span key={m} className="mx-dot" style={{ left: `${((m * bw + bw / 2) / W) * 100}%`, top: `${(Math.max(6, y(data[m].h) - 9) / height) * 100}%` }} />)}
    <div className="mx-axis"><span>{series[0]?.t}</span><span>{series[Math.floor(n / 2)]?.t}</span><span>{series[n - 1]?.t}</span></div>
  </div>;
}

export function LineChart({ values, base, band, zero, color = 'var(--mx-accent)', height = 120, markAt, label, domain, total }: { values: number[]; base?: number[]; band?: number; zero?: boolean; color?: string; height?: number; markAt?: number; label: string; domain?: [number, number]; total?: number }) {
  const ext = domain ? [...domain] : [...values, ...(base ?? []), ...(band ? [band, -band] : []), ...(zero ? [0] : [])];
  const y = scaleY(ext, height, 8);
  const x = (i: number) => (i / Math.max(1, (total ?? values.length) - 1)) * W;
  const d = values.map((v, i) => `${i ? 'L' : 'M'}${x(i)},${y(v)}`).join(' ');
  const gid = useId().replace(/:/g, '');
  return <div className="mx-chart" style={{ height }}>
    <svg viewBox={`0 0 ${W} ${height}`} preserveAspectRatio="none" role="img" aria-label={label}>
      <defs><linearGradient id={`a${gid}`} x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor={color} stopOpacity=".35" /><stop offset="1" stopColor={color} stopOpacity="0" /></linearGradient></defs>
      {band && <rect x={0} width={W} y={y(band)} height={y(-band) - y(band)} className="mx-band" />}
      {zero && <line x1={0} x2={W} y1={y(0)} y2={y(0)} className="mx-grid" />}
      {base && <path d={base.map((v, i) => `${i ? 'L' : 'M'}${x(i)},${y(v)}`).join(' ')} className="mx-base" />}
      <path d={`${d} L${x(values.length - 1)},${height} L0,${height} Z`} fill={`url(#a${gid})`} className="mx-area" />
      <path d={d} pathLength={1} className="mx-draw mx-line" style={{ stroke: color }} />
    </svg>
    {markAt !== undefined && <span className="mx-dot" style={{ left: `${(x(markAt) / W) * 100}%`, top: `${(y(values[markAt]) / height) * 100}%` }} />}
  </div>;
}

export function Gauge({ value, size = 150 }: { value: number; size?: number }) {
  const v = useCountUp(value, 1200);
  const r = 44; const c = 2 * Math.PI * r; const arc = 0.75;
  return <div className={`mx-gauge mx-t-${tier(value)}`} style={{ width: size, height: size }}>
    <svg viewBox="0 0 100 100">
      <circle cx="50" cy="50" r={r} className="mx-gauge-track" strokeDasharray={`${c * arc} ${c}`} />
      <circle cx="50" cy="50" r={r} className="mx-gauge-fill" strokeDasharray={`${c * arc * (v / 100)} ${c}`} />
    </svg>
    <div className="mx-gauge-v"><b>{Math.round(v)}</b><span>/ 100 risk</span></div>
  </div>;
}

export function Counter({ value, digits = 0, suffix = '' }: { value: number; digits?: number; suffix?: string }) {
  const v = useCountUp(value);
  return <>{v.toFixed(digits)}{suffix}</>;
}
