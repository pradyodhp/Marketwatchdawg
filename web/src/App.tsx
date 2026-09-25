import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Link, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import './style.css';
import { pctStr, price, sampleCsv, splitCsvBySymbol, tier } from './engine';
import { StoreProvider, useStore, stateToStatus } from './store';
import { RULE_METRICS } from './types';
import type { Alert, ScoreBar, Status, Tracked } from './types';
import { CandleChart, Counter, Gauge, LineChart, Spark } from './Charts';

const NAV = [
  { to: '/', label: 'Command' },
  { to: '/alerts', label: 'Alerts' },
  { to: '/markets', label: 'Markets' },
  { to: '/upload', label: 'Your data' },
  { to: '/settings', label: 'Settings' },
];
const STATUS_LABEL: Record<Status, string> = { open: 'Open', ack: 'Acknowledged', resolved: 'Resolved', escalated: 'Escalated' };

function Score({ s, big }: { s: number; big?: boolean }) { return <span className={`mx-score mx-t-${tier(s)} ${big ? 'is-big' : ''}`}>{s}</span>; }

function Topbar() {
  const { tick, playing, setPlaying, restart, settings, setSettings, alerts, status, tracked, bars } = useStore();
  const { pathname } = useLocation();
  const open = alerts.filter(a => status(a.id) === 'open' && a.score >= settings.minScore).length;
  const navRef = useRef<HTMLDivElement>(null);
  const [pill, setPill] = useState({ left: 0, width: 0 });
  useLayoutEffect(() => {
    const el = navRef.current?.querySelector<HTMLElement>('.is-active');
    if (el) setPill({ left: el.offsetLeft, width: el.offsetWidth });
  }, [pathname, open]);
  const series = tracked[0]?.series ?? [];
  const bar = series[Math.min(tick, series.length - 1)];
  const done = tick >= bars - 1;
  return <header className="mx-top">
    <div className="mx-top-row">
      <Link to="/" className="mx-brand"><span className="mx-logo"><i /><i /><i /></span><span>MarketWatch<b>AI</b></span></Link>
      <div className="mx-clock">
        <span className={`mx-live ${playing ? 'is-on' : ''}`}><i /><span>{done ? 'Session closed' : playing ? 'Live replay' : 'Paused'}</span></span>
        <b>{bar ? `${bar.t} IST` : '--:--'}</b>
        {done ? <button className="mx-icon" onClick={restart} aria-label="Replay the session">↺</button>
          : <button className="mx-icon" onClick={() => setPlaying(!playing)} aria-label={playing ? 'Pause replay' : 'Play replay'}>{playing ? '❚❚' : '▶'}</button>}
        <button className="mx-chip" onClick={() => setSettings({ ...settings, speed: settings.speed === 1 ? 4 : 1 })} aria-label="Replay speed">{settings.speed}x</button>
      </div>
    </div>
    <nav className="mx-nav" ref={navRef} aria-label="MarketWatch pages">
      <span className="mx-nav-pill" style={{ transform: `translateX(${pill.left}px)`, width: pill.width }} />
      {NAV.map(n => <Link key={n.to} to={n.to} className={pathname === n.to || (n.to === '/alerts' && pathname === '/alert') ? 'is-active' : ''}>
        {n.label}{n.to === '/alerts' && open > 0 && <em key={open} className="mx-badge">{open}</em>}
      </Link>)}
    </nav>
    <div className="mx-progress"><i style={{ width: `${(tick / Math.max(1, bars - 1)) * 100}%` }} /></div>
  </header>;
}

function Ticker() {
  const { tracked, tick } = useStore();
  const items = tracked.filter(t => t.source === 'live').map(t => { const i = Math.min(tick, t.series.length - 1); const c = t.series[i].c; const o = t.series[0].o; return { sym: t.sym, c, ch: (c / o - 1) * 100 }; });
  const row = items.map(i => <span key={i.sym} className={i.ch >= 0 ? 'is-up' : 'is-down'}><b>{i.sym}</b> {price(i.c)} <em>{pctStr(i.ch)}</em></span>);
  return <div className="mx-ticker" aria-hidden><div className="mx-ticker-in">{row}{row}</div></div>;
}

function Toasts() {
  const { toasts, dismiss, select } = useStore();
  const nav = useNavigate();
  return <div className="mx-toasts" role="status" aria-live="polite">
    {toasts.map(t => <div key={t.id} className={`mx-toast mx-t-${tier(t.alert.score)}`}>
      <div className="mx-toast-h"><b>{t.alert.sev} · {t.alert.sym}</b><button onClick={() => dismiss(t.id)} aria-label="Dismiss">×</button></div>
      <p>Sudden move {pctStr(t.alert.move)} at {t.alert.t}. Risk {t.alert.score}/100.</p>
      <div className="mx-toast-f"><span>Sent to {t.channels.join(', ')}</span><button onClick={() => { select(t.alert.id); dismiss(t.id); nav('/alert'); }}>Why?</button></div>
      <i className="mx-toast-timer" />
    </div>)}
  </div>;
}

function AlertCard({ a, i, compact }: { a: Alert; i: number; compact?: boolean }) {
  const { status, setStatus, select } = useStore();
  const nav = useNavigate();
  const st = status(a.id);
  return <article className={`mx-card mx-alert is-${st} mx-t-${tier(a.score)}`} style={{ ['--i' as string]: i }}>
    <div className="mx-alert-top">
      <Score s={a.score} />
      <div className="mx-alert-id"><b>{a.sym}</b><span>{a.date} {a.t} · {pctStr(a.move)} · {a.source === 'upload' ? 'your data' : a.name}</span></div>
      <span key={st} className={`mx-pill is-${st}`}>{STATUS_LABEL[st]}</span>
    </div>
    <p className="mx-reason">{a.reasons[0]}</p>
    {!compact && <div className="mx-actions">
      <button className="mx-btn is-ghost" onClick={() => { select(a.id); nav('/alert'); }}>Why? →</button>
      <button className="mx-btn" disabled={st !== 'open'} onClick={() => setStatus(a.id, 'ack')}>Acknowledge</button>
      <button className="mx-btn" disabled={st === 'resolved'} onClick={() => setStatus(a.id, 'resolved')}>Resolve</button>
    </div>}
    {compact && <button className="mx-card-link" onClick={() => { select(a.id); nav('/alert'); }} aria-label={`Open ${a.sym} alert`} />}
  </article>;
}

function GuidancePanel() {
  const { guidance, rules, live } = useStore();
  const nav = useNavigate();
  if (!guidance.length && !rules.length) return null;
  return <section className="mx-card mx-panel">
    <div className="mx-panel-h"><h2>Guidance</h2><span>{rules.length} trigger rule{rules.length === 1 ? '' : 's'} · {live?.running ? 'live polling on' : 'polling off'}</span></div>
    {guidance.slice(0, 4).map((g, i) => <article key={g.id} className="mx-card mx-alert" style={{ ['--i' as string]: i }}>
      <header><div className="mx-alert-id"><b>{g.title}</b><span>{new Date(g.timestamp).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</span></div><span className="mx-chip">Rs {g.close.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span></header>
      <p className="mx-alert-sum">{g.suggestion}</p>
      {g.note && <p className="mx-note">Your note: {g.note}</p>}
      <div className="mx-alert-foot"><button className="mx-btn is-ghost" onClick={() => nav('/markets')}>Chart →</button><span className="mx-note">{g.disclaimer}</span></div>
    </article>)}
    {!guidance.length && <p className="mx-empty">{rules.length} rule{rules.length === 1 ? '' : 's'} armed. They fire on new bars from live polling or uploads.</p>}
  </section>;
}

function Command() {
  const { tracked, tick, alerts, status, riskAt, setFocusSym, detectInfo, settings } = useStore();
  const nav = useNavigate();
  const live = tracked.filter(t => t.source === 'live');
  const open = alerts.filter(a => status(a.id) === 'open' && a.score >= settings.minScore).length;
  const top = Math.max(...alerts.map(a => a.score), 0);
  const cols = 24;
  return <div className="mx-stack">
    <section className="mx-hero">
      <div>
        <p className="mx-eyebrow">Unusual trading activity watchdog</p>
        <h1>Every candle, scored.<br /><span className="mx-grad">Every alert, explained.</span></h1>
        <p className="mx-sub">Rolling Z-score, EWMA and Isolation Forest run on each 5-minute bar across the watchlist, then blend into one 0-100 risk score with plain-English reasons.</p>
      </div>
      <div className="mx-kpis">
        <div className="mx-kpi"><b><Counter value={tracked.length} /></b><span>symbols watched</span></div>
        <div className="mx-kpi"><b><Counter value={open} /></b><span>open alerts</span></div>
        <div className="mx-kpi"><b><Counter value={top} /></b><span>top risk today</span></div>
        <div className="mx-kpi"><b><Counter value={detectInfo?.batches ?? 0} /></b><span>batches scored</span></div>
      </div>
    </section>

    <section className="mx-card mx-panel">
      <div className="mx-panel-h"><h2>Risk radar</h2><span>last {cols} candles · darker = riskier</span></div>
      <div className="mx-heat" role="img" aria-label="Heatmap of risk by symbol over recent candles">
        {live.map(t => { const from = Math.max(0, Math.min(tick, t.series.length - 1) - cols + 1); return <div className="mx-heat-row" key={t.sym}>
          <button className="mx-heat-sym" onClick={() => { setFocusSym(t.sym); nav('/markets'); }}>{t.sym}</button>
          <div className="mx-heat-cells">{Array.from({ length: cols }, (_, k) => { const i = from + k; const r = i <= tick ? riskAt(t, i) : 0; return <i key={i} className={`mx-t-${tier(r)} ${i === tick ? 'is-new' : ''}`} style={{ ['--r' as string]: (r / 100).toFixed(2) }} title={`${t.sym} ${t.series[i]?.t}: ${Math.round(r)}`} />; })}</div>
        </div>; })}
      </div>
    </section>

    <GuidancePanel />

    <section className="mx-split">
      <div className="mx-card mx-panel">
        <div className="mx-panel-h"><h2>Latest alerts</h2><Link to="/alerts" className="mx-more">All alerts →</Link></div>
        <div className="mx-list">{alerts.filter(a => a.score >= settings.minScore).slice(0, 4).map((a, i) => <AlertCard key={a.id} a={a} i={i} compact />)}{!alerts.length && <p className="mx-empty">Quiet so far. Alerts appear here the moment a bar crosses your threshold.</p>}</div>
      </div>
      <div className="mx-card mx-panel">
        <div className="mx-panel-h"><h2>Watchlist</h2><span>tap to chart</span></div>
        <div className="mx-watch">{live.map((t, k) => {
          const i = Math.min(tick, t.series.length - 1);
          const c = t.series[i].c; const ch = (c / t.series[0].o - 1) * 100; const r = riskAt(t, i);
          return <button key={t.sym} className="mx-watch-row" onClick={() => { setFocusSym(t.sym); nav('/markets'); }} style={{ ['--i' as string]: k }}>
            <span className="mx-watch-id"><b>{t.sym}</b><em>{t.sector}</em></span>
            <Spark values={t.series.slice(0, i + 1).map(x => x.c)} up={ch >= 0} />
            <span className="mx-watch-p"><b>{price(c)}</b><em className={ch >= 0 ? 'is-up' : 'is-down'}>{pctStr(ch)}</em></span>
            <Score s={Math.round(r)} />
          </button>;
        })}</div>
      </div>
    </section>
  </div>;
}

function Alerts() {
  const { alerts, status, setStatus, settings } = useStore();
  const [filter, setFilter] = useState<'all' | Status>('all');
  const [sev, setSev] = useState<'all' | 'CRITICAL' | 'HIGH' | 'MEDIUM'>('all');
  const [q, setQ] = useState('');
  const visible = alerts.filter(a => a.score >= settings.minScore);
  const list = visible.filter(a => (filter === 'all' || status(a.id) === filter) && (sev === 'all' || a.sev === sev) && a.sym.includes(q.toUpperCase()));
  const counts = (s: 'all' | Status) => visible.filter(a => s === 'all' || status(a.id) === s).length;
  const openIds = list.filter(a => status(a.id) === 'open').map(a => a.id);
  return <div className="mx-stack">
    <div className="mx-page-h"><div><p className="mx-eyebrow">Analyst queue · risk ≥ {settings.minScore}</p><h1>Alerts</h1></div>
      <button className="mx-btn" disabled={!openIds.length} onClick={() => openIds.forEach(id => setStatus(id, 'ack'))}>Acknowledge {openIds.length || ''} open</button></div>
    <div className="mx-filters">
      <div className="mx-seg">{(['all', 'open', 'ack', 'escalated', 'resolved'] as const).map(f => <button key={f} className={filter === f ? 'is-on' : ''} onClick={() => setFilter(f)}>{f === 'all' ? 'All' : STATUS_LABEL[f]} <em>{counts(f)}</em></button>)}</div>
      <div className="mx-seg is-small">{(['all', 'CRITICAL', 'HIGH', 'MEDIUM'] as const).map(f => <button key={f} className={sev === f ? 'is-on' : ''} onClick={() => setSev(f)}>{f === 'all' ? 'Any severity' : f[0] + f.slice(1).toLowerCase()}</button>)}</div>
      <input className="mx-input" placeholder="Search symbol" value={q} onChange={e => setQ(e.target.value)} aria-label="Search symbol" />
    </div>
    <div className="mx-list" key={filter + sev}>{list.map((a, i) => <AlertCard key={a.id} a={a} i={i} />)}
      {!list.length && <div className="mx-empty"><b>Nothing here.</b> {visible.length ? 'Try another filter.' : 'Alerts appear as the replay runs.'}</div>}</div>
  </div>;
}

const fmtLogTime = (iso: string) => {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`;
};
const EVENT_VERB: Record<string, string> = { NEW: 'Alert raised by the detector pipeline', ACKNOWLEDGED: 'Acknowledged', ESCALATED: 'Escalated to compliance', RESOLVED: 'Resolved' };

function AlertDetail() {
  const { alerts, selected, select, tracked, status, setStatus, settings } = useStore();
  const [note, setNote] = useState('');
  const a = alerts.find(x => x.id === selected) ?? alerts[0];
  if (!a) return <div className="mx-empty">No alerts yet. <Link to="/">Back to command</Link></div>;
  const t = tracked.find(x => x.sym === a.sym) as Tracked | undefined;
  const idx = alerts.indexOf(a);
  const inWindow = t && a.bar >= 0;
  let series: ScoreBar[] = [], sc: ScoreBar[] = [], m = 0, lo = 0;
  if (inWindow && t) {
    lo = Math.max(0, a.bar - 30); const hi = Math.min(t.series.length - 1, a.bar + 8);
    series = t.series.slice(lo, hi + 1); sc = series; m = a.bar - lo;
  }
  const vols = series.map(c => c.v / 1000);
  const baseline = vols.map((_, i) => { const w = series.slice(Math.max(0, i - 20), i).map(c => c.v / 1000); return w.length ? w.reduce((s, x) => s + x, 0) / w.length : vols[i]; });
  const st = status(a.id);
  const parts = [
    { k: 'z' as const, label: 'Rolling Z-score', hint: 'price, volume and pressure vs time-of-day baselines', v: a.contrib.z, max: settings.weights.z },
    { k: 'ewma' as const, label: 'EWMA deviation', hint: 'break from the smoothed trend', v: a.contrib.ewma, max: settings.weights.ewma },
    { k: 'iforest' as const, label: 'Isolation Forest', hint: 'multivariate rarity, walk-forward', v: a.contrib.iforest, max: settings.weights.iforest },
  ];
  const wsum = settings.weights.z + settings.weights.ewma + settings.weights.iforest || 1;
  const act = (s: Status) => { setStatus(a.id, s, note.trim() || undefined); setNote(''); };
  const log = [...a.history].reverse();
  return <div className="mx-stack" key={a.id}>
    <div className="mx-crumbs"><Link to="/alerts">← Alerts</Link>
      <span><button className="mx-icon" disabled={idx <= 0} onClick={() => select(alerts[idx - 1].id)} aria-label="Newer alert">‹</button>{idx + 1} of {alerts.length}<button className="mx-icon" disabled={idx >= alerts.length - 1} onClick={() => select(alerts[idx + 1].id)} aria-label="Older alert">›</button></span></div>
    <section className={`mx-card mx-detail-hero mx-t-${tier(a.score)}`}>
      <Gauge value={a.score} />
      <div className="mx-detail-id">
        <span className={`mx-sev mx-t-${tier(a.score)}`}>{a.sev}</span>
        <h1>{a.sym}</h1>
        <p>{a.name} · {a.date} {a.t} IST · <b className={a.move >= 0 ? 'is-up' : 'is-down'}>{pctStr(a.move)}</b> in 5 min{a.simulated ? ' · simulated injection' : ''}</p>
        <span key={st} className={`mx-pill is-${st}`}>{STATUS_LABEL[st]}</span>
      </div>
    </section>
    <section className="mx-card mx-panel">
      <div className="mx-panel-h"><h2>Why this fired</h2></div>
      <ol className="mx-reasons">{a.reasons.map((r, i) => <li key={i} style={{ ['--i' as string]: i }}>{r}</li>)}</ol>
    </section>
    <section className="mx-card mx-panel">
      <div className="mx-panel-h"><h2>What drove the score</h2><span>{a.score} points total</span></div>
      <div className="mx-contrib">{parts.map((p, i) => { const max = (p.max / wsum) * 100; return <div key={p.k} className="mx-contrib-row" style={{ ['--i' as string]: i }}>
        <div><b>{p.label}</b><span>{p.hint}</span></div>
        <div className="mx-bar"><i style={{ width: `${Math.max(2, (p.v / Math.max(1, max)) * 100)}%` }} /></div>
        <em>+{p.v.toFixed(0)}<small> / {max.toFixed(0)}</small></em>
      </div>; })}
        {a.agreement > 0 && <div className="mx-contrib-row" style={{ ['--i' as string]: 3 }}>
          <div><b>Detector agreement</b><span>bonus when 2+ detectors fire together</span></div>
          <div className="mx-bar"><i style={{ width: `${a.agreement}%` }} /></div>
          <em>+{a.agreement.toFixed(0)}<small> / 10</small></em>
        </div>}
      </div>
    </section>
    {inWindow && <>
      <section className="mx-card mx-panel">
        <div className="mx-panel-h"><h2>Price, 5-min candles</h2><span>flagged bar highlighted</span></div>
        <CandleChart series={series} marks={[m]} highlight={[m, Math.min(series.length - 1, m + 1)]} height={230} />
      </section>
      <div className="mx-grid2">
        <section className="mx-card mx-panel"><div className="mx-panel-h"><h3>Volume vs baseline</h3><span>thousands</span></div><LineChart values={vols} base={baseline} markAt={m} label="Volume against rolling baseline" /></section>
        <section className="mx-card mx-panel"><div className="mx-panel-h"><h3>Volatility (Parkinson)</h3><span>% per bar</span></div><LineChart values={sc.map(s => s.park)} color="var(--mx-violet)" markAt={m} label="Parkinson volatility" /></section>
        <section className="mx-card mx-panel"><div className="mx-panel-h"><h3>Buy/sell pressure proxy</h3><span>-1 to +1</span></div><LineChart values={sc.map(s => s.pressure)} zero color="var(--mx-amber)" markAt={m} label="Buy sell pressure proxy" /><p className="mx-note">Estimated from where each candle closes in its range. True order-book imbalance needs depth data.</p></section>
        <section className="mx-card mx-panel"><div className="mx-panel-h"><h3>Return Z-score</h3><span>band ±3</span></div><LineChart values={sc.map(s => Math.max(-8, Math.min(8, s.z_ret)))} band={3} zero color="var(--mx-red)" markAt={m} label="Return Z-score with plus minus 3 band" /></section>
      </div>
    </>}
    {!inWindow && <section className="mx-card mx-panel"><p className="mx-empty">This alert is outside the loaded chart window (last {t?.series.length ?? 0} bars). The reasons and score breakdown above come from the server-side detection run.</p></section>}
    <section className="mx-card mx-panel">
      <div className="mx-panel-h"><h2>Analyst decision</h2></div>
      <textarea className="mx-input mx-textarea" placeholder="Add a note (optional), e.g. checked news, block deal reported" value={note} onChange={e => setNote(e.target.value)} />
      <div className="mx-actions">
        <button className="mx-btn" disabled={st === 'ack'} onClick={() => act('ack')}>Acknowledge</button>
        <button className="mx-btn is-warn" disabled={st === 'escalated'} onClick={() => act('escalated')}>Escalate</button>
        <button className="mx-btn is-primary" disabled={st === 'resolved'} onClick={() => act('resolved')}>Resolve</button>
        {st !== 'open' && <button className="mx-btn is-ghost" onClick={() => act('open')}>Reopen</button>}
      </div>
      <ul className="mx-log">{log.map((e, i) => <li key={e.timestamp + i}><time>{fmtLogTime(e.timestamp)}</time>{EVENT_VERB[e.to_state] ?? e.to_state}{e.note ? `: "${e.note}"` : ''}</li>)}</ul>
    </section>
  </div>;
}

function Markets() {
  const { tracked, tick, focusSym, setFocusSym, riskAt, alerts, settings } = useStore();
  const t = tracked.find(x => x.sym === focusSym) ?? tracked[0];
  if (!t) return <div className="mx-empty">No data loaded.</div>;
  const upto = Math.min(tick, t.series.length - 1);
  const b = t.series[upto]; const c = t.series[upto];
  const ch = (c.c / t.series[0].o - 1) * 100;
  const marks = alerts.filter(a => a.sym === t.sym && a.bar >= 0).map(a => a.bar);
  const riskSeries = t.series.slice(0, upto + 1).map(s => s.risk);
  const meters = [
    { label: 'Z-score', v: Math.min(1, Math.max(Math.abs(b.z_ret), Math.abs(b.z_vol)) / 6), txt: `${Math.max(Math.abs(b.z_ret), Math.abs(b.z_vol)).toFixed(1)}σ` },
    { label: 'EWMA', v: Math.min(1, Math.abs(b.ewma_dev) / 6), txt: `${b.ewma_dev.toFixed(1)}σ` },
    { label: 'Isolation Forest', v: Math.max(0, Math.min(1, b.if_score + 0.2)), txt: b.if_score.toFixed(2) },
    { label: 'Pressure proxy', v: Math.abs(b.pressure), txt: `${b.pressure >= 0 ? '+' : ''}${b.pressure.toFixed(2)}` },
  ];
  return <div className="mx-stack">
    <div className="mx-symbols" role="tablist">{tracked.map(x => <button key={x.sym} role="tab" aria-selected={x.sym === t.sym} className={x.sym === t.sym ? 'is-on' : ''} onClick={() => setFocusSym(x.sym)}>{x.sym}{x.source === 'upload' && <em>yours</em>}</button>)}</div>
    <section className="mx-card mx-panel" key={t.sym}>
      <div className="mx-quote">
        <div><p className="mx-eyebrow">{t.sector}</p><h1>{t.sym}</h1><p className="mx-sub">{t.name}</p></div>
        <div className="mx-quote-p"><b>₹{price(c.c)}</b><em className={ch >= 0 ? 'is-up' : 'is-down'}>{pctStr(ch)} today</em><Score s={Math.round(riskAt(t, upto))} big /></div>
      </div>
      <CandleChart series={t.series} upto={upto} marks={marks} height={260} />
      <div className="mx-meters">{meters.map(mt => <div key={mt.label} className="mx-meter"><span>{mt.label}</span><b>{mt.txt}</b><div className="mx-bar"><i style={{ width: `${Math.max(3, mt.v * 100)}%` }} /></div></div>)}</div>
    </section>
    <section className="mx-card mx-panel">
      <div className="mx-panel-h"><h3>Risk through the session</h3><span>dashed band = HIGH severity threshold ({settings.thresholds.high})</span></div>
      <div className="mx-thresh-wrap"><LineChart values={riskSeries} total={t.series.length} domain={[0, 100]} color="var(--mx-accent)" height={130} label="Risk score over the session" />
        <i className="mx-thresh" style={{ top: `${8 + (1 - settings.thresholds.high / 100) * 114}px` }} /></div>
    </section>
  </div>;
}

const STEPS = ['Validate rows', 'Upload to API', 'Server validation', 'Z-score + EWMA + Isolation Forest', 'Score + explain'];

function Upload() {
  const { ingest, setFocusSym, select } = useStore();
  const nav = useNavigate();
  const [text, setText] = useState('');
  const [fileName, setFileName] = useState('');
  const [parquet, setParquet] = useState<ArrayBuffer | null>(null);
  const [err, setErr] = useState('');
  const [step, setStep] = useState(-1);
  const [drag, setDrag] = useState(false);
  const [result, setResult] = useState<{ symbol: string; loaded: number; dropped: number; reasons: Record<string, number> }[] | null>(null);
  const [busy, setBusy] = useState(false);

  const load = (f: File) => {
    setErr(''); setResult(null);
    setFileName(f.name);
    if (/\.parquet$/i.test(f.name)) {
      setText(''); f.arrayBuffer().then(setParquet);
    } else {
      setParquet(null); f.text().then(setText);
    }
  };
  const run = async () => {
    setErr(''); setResult(null); setBusy(true); setStep(0);
    try {
      let items: { symbol: string; csv?: string; parquet?: ArrayBuffer }[];
      if (parquet) {
        const sym = (fileName.replace(/\.[^.]+$/, '') || 'MYDATA').toUpperCase().replace(/[^A-Z0-9^._-]/g, '').slice(0, 20) || 'MYDATA';
        items = [{ symbol: sym, parquet }];
      } else {
        const parts = splitCsvBySymbol(text, (fileName.replace(/\.[^.]+$/, '') || 'MYDATA').toUpperCase());
        items = parts.map(p => ({ symbol: p.symbol, csv: p.csv }));
      }
      STEPS.forEach((_, i) => setTimeout(() => setStep(i + 1), 500 * (i + 1)));
      const res = await ingest(items);
      setStep(STEPS.length);
      setResult(res);
    } catch (e) {
      setErr((e as Error).message); setStep(-1);
    } finally {
      setBusy(false);
    }
  };

  return <div className="mx-stack">
    <div className="mx-page-h"><div><p className="mx-eyebrow">Bring your own market data</p><h1>Your data</h1><p className="mx-sub">Drop a CSV or Parquet of 5-minute NSE candles. The API validates, stores and scores it with the same detectors.</p></div></div>
    <label className={`mx-card mx-drop ${drag ? 'is-drag' : ''}`} onDragOver={e => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={e => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) load(f); }}>
      <input type="file" accept=".csv,.parquet,text/csv" onChange={e => { const f = e.target.files?.[0]; if (f) load(f); }} />
      <span className="mx-drop-ic">⇪</span>
      <b>{fileName || 'Drop a CSV or Parquet here or tap to choose'}</b>
      <span>Columns: datetime, open, high, low, close, volume, and optionally symbol. 5-min bars, 09:15-15:30 IST.</span>
    </label>
    <div className="mx-actions">
      <button className="mx-btn is-ghost" onClick={() => { setText(sampleCsv()); setParquet(null); setFileName('sample.csv'); setResult(null); setErr(''); }}>Load sample data</button>
      <button className="mx-btn is-primary" disabled={busy || (!text.trim() && !parquet)} onClick={run}>Upload + run detection</button>
    </div>
    {!parquet && <textarea className="mx-input mx-textarea is-code" placeholder="…or paste CSV text here" value={text} onChange={e => { setText(e.target.value); setResult(null); }} spellCheck={false} />}
    {parquet && <p className="mx-note">Parquet ready ({Math.round(parquet.byteLength / 1024)} KB) — sent straight to POST /ingest.</p>}
    {err && <div className="mx-error">{err}</div>}
    {step >= 0 && <div className="mx-steps">{STEPS.map((s, i) => <div key={s} className={step > i ? 'is-done' : step === i ? 'is-run' : ''}><i />{s}</div>)}</div>}
    {result && <div className="mx-stack mx-result">
      <div className="mx-kpis is-row">
        <div className="mx-kpi"><b><Counter value={result.reduce((s, r) => s + r.loaded, 0)} /></b><span>valid candles</span></div>
        <div className="mx-kpi"><b><Counter value={result.reduce((s, r) => s + r.dropped, 0)} /></b><span>rows dropped</span></div>
        <div className="mx-kpi"><b><Counter value={result.length} /></b><span>symbols</span></div>
      </div>
      {result.map(r => <section key={r.symbol} className="mx-card mx-panel">
        <div className="mx-panel-h"><h2>{r.symbol}</h2><span>{r.loaded} candles stored{r.dropped ? ` · ${r.dropped} dropped` : ''}</span></div>
        {Object.keys(r.reasons).length > 0 && <details className="mx-dropped"><summary>Why rows were dropped</summary><ul>{Object.entries(r.reasons).map(([why, n]) => <li key={why}>{why}: {n}</li>)}</ul></details>}
      </section>)}
      <div className="mx-actions">
        <button className="mx-btn is-primary" onClick={() => { setFocusSym(result[0].symbol); nav('/markets'); }}>Open in Markets →</button>
        <button className="mx-btn is-ghost" onClick={() => nav('/alerts')}>Open alert queue →</button>
      </div>
    </div>}
  </div>;
}

function Slider({ label, value, min, max, step, onChange, fmt }: { label: string; value: number; min: number; max: number; step: number; onChange: (v: number) => void; fmt: (v: number) => string }) {
  return <label className="mx-slider"><span>{label}</span><b>{fmt(value)}</b>
    <input type="range" min={min} max={max} step={step} value={value} onChange={e => onChange(Number(e.target.value))} style={{ ['--p' as string]: `${((value - min) / (max - min)) * 100}%` }} /></label>;
}

function LiveCard() {
  const { live, startLive, stopLive, pollLive, liveBusy } = useStore();
  if (!live) return null;
  return <section className="mx-card mx-panel">
    <div className="mx-panel-h"><h2>Live market data</h2><span className={`mx-chip ${live.running ? '' : 'is-ghost'}`}>{live.running ? `polling every ${Math.round(live.interval_sec / 60)} min` : 'off'}</span></div>
    <p className="mx-sub">Source: {live.source}. {live.delay_note}</p>
    {live.last_summary?.polled_at && <p className="mx-note">Last poll {new Date(live.last_summary.polled_at).toLocaleTimeString('en-IN')}: {live.last_summary.new_bars ?? 0} new bars, {live.last_summary.new_alerts ?? 0} new alerts, {live.last_summary.guidance_fired ?? 0} rule hits.</p>}
    <div className="mx-actions">
      {live.running
        ? <button className="mx-btn" disabled={liveBusy} onClick={stopLive}>Stop polling</button>
        : <button className="mx-btn is-primary" disabled={liveBusy || !live.available} onClick={() => startLive(300)}>Start live polling</button>}
      <button className="mx-btn is-ghost" disabled={liveBusy || !live.available} onClick={pollLive}>{liveBusy ? 'Polling…' : 'Poll once now'}</button>
    </div>
    {!live.available && <p className="mx-note">yfinance is not installed on the server - pip install yfinance to enable.</p>}
  </section>;
}

function RulesCard() {
  const { rules, addRule, removeRule, tracked } = useStore();
  const [symbol, setSymbol] = useState('*');
  const [metric, setMetric] = useState('price_above');
  const [threshold, setThreshold] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const meta = RULE_METRICS.find(m => m.id === metric)!;
  const submit = async () => {
    const v = parseFloat(threshold);
    if (!Number.isFinite(v)) return;
    setBusy(true);
    try { await addRule({ symbol, metric, threshold: v, note }); setThreshold(''); setNote(''); } finally { setBusy(false); }
  };
  return <section className="mx-card mx-panel">
    <div className="mx-panel-h"><h2>Trigger rules</h2><span>{rules.length} armed</span></div>
    <p className="mx-sub">Fire guidance when a stock hits a level or a metric crosses a line - evaluated on every new bar from live polling or uploads.</p>
    {rules.map(r => <div key={r.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,.08)' }}>
      <div><b>{r.symbol}</b> · {RULE_METRICS.find(m => m.id === r.metric)?.label ?? r.metric} <b>{r.threshold}</b>{r.note ? <span className="mx-note"> · {r.note}</span> : null}</div>
      <button className="mx-btn is-ghost" onClick={() => removeRule(r.id)}>Delete</button>
    </div>)}
    <div style={{ display: 'grid', gap: 8, marginTop: 12 }}>
      <div className="mx-seg is-small">
        <button className={symbol === '*' ? 'is-on' : ''} onClick={() => setSymbol('*')}>Any stock</button>
        {tracked.slice(0, 6).map(t => <button key={t.sym} className={symbol === t.sym ? 'is-on' : ''} onClick={() => setSymbol(t.sym)}>{t.sym}</button>)}
      </div>
      <select className="mx-input" value={metric} onChange={e => setMetric(e.target.value)}>
        {RULE_METRICS.map(m => <option key={m.id} value={m.id}>{m.label}</option>)}
      </select>
      <input className="mx-input" type="number" placeholder={`Threshold (${meta.hint})`} value={threshold} onChange={e => setThreshold(e.target.value)} />
      <input className="mx-input" placeholder="Note to self (optional)" value={note} onChange={e => setNote(e.target.value)} />
      <button className="mx-btn is-primary" disabled={busy || !threshold} onClick={submit}>{busy ? 'Adding…' : 'Arm rule'}</button>
    </div>
    <p className="mx-note">Guidance is statistical decision support, not financial advice. No trades are placed.</p>
  </section>;
}

function Settings() {
  const { settings: s, setSettings, applySettings, applying, testToast } = useStore();
  const wsum = s.weights.z + s.weights.ewma + s.weights.iforest || 1;
  const nw = { z: s.weights.z / wsum, ewma: s.weights.ewma / wsum, iforest: s.weights.iforest / wsum };
  const setW = (k: 'z' | 'ewma' | 'iforest', v: number) => setSettings({ ...s, weights: { ...s.weights, [k]: v } });
  const yaml = `risk_scoring:\n  weights:\n    ZScoreDetector: ${s.weights.z.toFixed(2)}\n    EWMADetector: ${s.weights.ewma.toFixed(2)}\n    IsolationForestDetector: ${s.weights.iforest.toFixed(2)}\n  thresholds:\n    medium: ${s.thresholds.medium}\n    high: ${s.thresholds.high}\n    critical: ${s.thresholds.critical}\ndetectors:\n  zscore_threshold: ${s.zscoreThreshold}\n  min_observations: ${s.minObservations}\n  ewma_alpha: ${s.ewmaAlpha.toFixed(2)}\n  ewma_threshold: ${s.ewmaThreshold}\n  isolation_forest_refit_interval: ${s.ifRefit}\ncooldown:\n  window_bars: ${s.cooldownBars}  # ${s.cooldownBars * 5} minutes\nnotifications:\n  webhook_url: "${s.webhookUrl}"\n  min_severity: ${s.minSeverity}`;
  return <div className="mx-stack">
    <div className="mx-page-h"><div><p className="mx-eyebrow">Tune the watchdog</p><h1>Settings</h1><p className="mx-sub">Apply writes config/settings.yaml and re-runs the full detection pass server-side (about 20s on sample data).</p></div>
      <button className="mx-btn is-primary" disabled={applying} onClick={applySettings}>{applying ? 'Re-running detection…' : 'Apply + re-score'}</button></div>
    <section className="mx-card mx-panel">
      <div className="mx-panel-h"><h2>Alert rules</h2></div>
      <Slider label="Show alerts with risk at least" value={s.minScore} min={20} max={90} step={5} onChange={v => setSettings({ ...s, minScore: v })} fmt={v => `${v}`} />
      <Slider label="MEDIUM severity from" value={s.thresholds.medium} min={20} max={70} step={5} onChange={v => setSettings({ ...s, thresholds: { ...s.thresholds, medium: Math.min(v, s.thresholds.high - 5) } })} fmt={v => `${v}`} />
      <Slider label="HIGH severity from" value={s.thresholds.high} min={40} max={90} step={5} onChange={v => setSettings({ ...s, thresholds: { ...s.thresholds, high: Math.min(Math.max(v, s.thresholds.medium + 5), s.thresholds.critical - 5) } })} fmt={v => `${v}`} />
      <Slider label="CRITICAL severity from" value={s.thresholds.critical} min={60} max={100} step={5} onChange={v => setSettings({ ...s, thresholds: { ...s.thresholds, critical: Math.max(v, s.thresholds.high + 5) } })} fmt={v => `${v}`} />
      <Slider label="Cooldown per symbol" value={s.cooldownBars} min={1} max={12} step={1} onChange={v => setSettings({ ...s, cooldownBars: v })} fmt={v => `${v * 5} min`} />
    </section>
    <section className="mx-card mx-panel">
      <div className="mx-panel-h"><h2>Detector weights</h2><span>normalised to 100%</span></div>
      <div className="mx-mix">{(['z', 'ewma', 'iforest'] as const).map(k => <i key={k} className={`is-${k}`} style={{ flexGrow: nw[k] }} />)}</div>
      <Slider label="Rolling Z-score" value={s.weights.z} min={0} max={1} step={0.05} onChange={v => setW('z', v)} fmt={() => `${Math.round(nw.z * 100)}%`} />
      <Slider label="EWMA deviation" value={s.weights.ewma} min={0} max={1} step={0.05} onChange={v => setW('ewma', v)} fmt={() => `${Math.round(nw.ewma * 100)}%`} />
      <Slider label="Isolation Forest" value={s.weights.iforest} min={0} max={1} step={0.05} onChange={v => setW('iforest', v)} fmt={() => `${Math.round(nw.iforest * 100)}%`} />
      <p className="mx-note">Buy/sell pressure is scored inside the Z-score detector (it is one of the candle-based features), not fused separately.</p>
    </section>
    <section className="mx-card mx-panel">
      <div className="mx-panel-h"><h2>Detector tuning</h2></div>
      <Slider label="Z-score threshold" value={s.zscoreThreshold} min={1.5} max={6} step={0.5} onChange={v => setSettings({ ...s, zscoreThreshold: v })} fmt={v => `${v.toFixed(1)}σ`} />
      <Slider label="EWMA alpha (responsiveness)" value={s.ewmaAlpha} min={0.05} max={0.9} step={0.05} onChange={v => setSettings({ ...s, ewmaAlpha: v })} fmt={v => v.toFixed(2)} />
      <Slider label="EWMA threshold" value={s.ewmaThreshold} min={1} max={5} step={0.5} onChange={v => setSettings({ ...s, ewmaThreshold: v })} fmt={v => `${v.toFixed(1)}σ`} />
      <Slider label="Isolation Forest refit every" value={s.ifRefit} min={1} max={20} step={1} onChange={v => setSettings({ ...s, ifRefit: v })} fmt={v => `${v} batch${v > 1 ? 'es' : ''}`} />
    </section>
    <section className="mx-card mx-panel">
      <div className="mx-panel-h"><h2>Sudden-move notifications</h2><span>min severity {s.minSeverity}</span></div>
      <input className="mx-input" placeholder="Webhook URL (Slack, Telegram, automation…) — empty disables" value={s.webhookUrl} onChange={e => setSettings({ ...s, webhookUrl: e.target.value })} />
      <div className="mx-seg is-small" style={{ marginTop: 10 }}>{(['MEDIUM', 'HIGH', 'CRITICAL'] as const).map(m => <button key={m} className={s.minSeverity === m ? 'is-on' : ''} onClick={() => setSettings({ ...s, minSeverity: m })}>{m}</button>)}</div>
      <div className="mx-actions" style={{ marginTop: 12 }}><button className="mx-btn" onClick={testToast}>Send a test alert</button><button className="mx-btn is-ghost" onClick={() => setSettings({ ...s, minScore: 50, thresholds: { medium: 50, high: 70, critical: 85 }, cooldownBars: 6, zscoreThreshold: 3, ewmaAlpha: 0.3, ewmaThreshold: 2.5, ifRefit: 8, weights: { z: 0.35, ewma: 0.25, iforest: 0.4 } })}>Reset to defaults</button></div>
      <p className="mx-note">HIGH and CRITICAL alerts post to the webhook above. Connect Slack, Telegram or WhatsApp through any webhook bridge.</p>
    </section>
    <LiveCard />
    <RulesCard />
    <section className="mx-card mx-panel">
      <div className="mx-panel-h"><h3>config/settings.yaml</h3><span>live preview</span></div>
      <pre className="mx-code">{yaml}</pre>
    </section>
  </div>;
}

const LOAD_STAGES = ['Connecting to the API', 'Reading settings and symbol universe', 'Running Z-score, EWMA and Isolation Forest over the curated history', 'Loading per-bar scores and alerts'];

function Loader() {
  const { stage, loadError } = useStore();
  const [shown, setShown] = useState(0);
  useEffect(() => { const i = LOAD_STAGES.indexOf(stage); if (i >= 0) setShown(i); }, [stage]);
  if (loadError) return <div className="mx-loader"><div className="mx-card mx-panel" style={{ maxWidth: 520 }}>
    <h2>Could not reach the MarketWatch API</h2>
    <p className="mx-sub">{loadError}</p>
    <p className="mx-note">Start the backend first: <code>uvicorn marketwatch.api:app --app-dir src</code>, then reload. In dev, run <code>npm run dev</code> in web/ (it proxies the API).</p>
    <div className="mx-actions"><button className="mx-btn is-primary" onClick={() => location.reload()}>Retry</button></div>
  </div></div>;
  return <div className="mx-loader"><div style={{ maxWidth: 420, width: '100%' }}>
    <span className="mx-logo is-loader"><i /><i /><i /></span>
    <h2 style={{ margin: '18px 0 6px' }}>Scoring the market…</h2>
    <p className="mx-sub">{stage}</p>
    <div className="mx-steps">{LOAD_STAGES.map((s, i) => <div key={s} className={i < shown ? 'is-done' : i === shown ? 'is-run' : ''}><i />{s}</div>)}</div>
    <p className="mx-note">The full-history detection pass takes about 20s the first time (cached afterwards).</p>
  </div></div>;
}

function Shell() {
  const { pathname } = useLocation();
  const { loading, loadError } = useStore();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    const move = (e: PointerEvent) => { const card = (e.target as HTMLElement).closest?.('.mx-card') as HTMLElement | null; if (!card) return; const r = card.getBoundingClientRect(); card.style.setProperty('--mx', `${e.clientX - r.left}px`); card.style.setProperty('--my', `${e.clientY - r.top}px`); };
    el.addEventListener('pointermove', move);
    return () => el.removeEventListener('pointermove', move);
  }, []);
  useEffect(() => { const el = ref.current; if (el && el.getBoundingClientRect().top < 0) el.scrollIntoView({ block: 'start', behavior: 'smooth' }); }, [pathname]);
  if (loading || loadError) return <div className="mx" ref={ref}><Loader /></div>;
  return <div className="mx" ref={ref}>
    <div className="mx-aurora" aria-hidden><i /><i /><i /></div>
    <Topbar />
    <Ticker />
    <main className="mx-page" key={pathname}>
      <Routes>
        <Route path="/" element={<Command />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/alert" element={<AlertDetail />} />
        <Route path="/markets" element={<Markets />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Command />} />
      </Routes>
    </main>
    <Toasts />
    <footer className="mx-foot">Decision support for surveillance analysts. Not investment advice, no trades are placed. Detection runs server-side on curated data.</footer>
  </div>;
}

export function App() {
  return <StoreProvider><Shell /></StoreProvider>;
}
