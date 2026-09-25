import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { api } from './api';
import { tierFromThresholds } from './engine';
import type { Alert, AlertState, ApiAlert, ApiGuidance, ApiRule, ApiSettings, CaseFile, LiveStatus, ScoreBar, Settings, Status, Tracked, WatchProfile } from './types';

type Toast = { id: string; alert: Alert; channels: string[] };
type DetectInfo = { symbols: number; batches: number; alerts: number; elapsed_ms: number; cached: boolean } | null;

type Store = {
  loading: boolean; loadError: string; stage: string; detectInfo: DetectInfo;
  tick: number; playing: boolean; setPlaying: (p: boolean) => void; restart: () => void;
  sessionStart: number; bars: number;
  settings: Settings; setSettings: (s: Settings) => void; applySettings: () => Promise<void>; applying: boolean;
  tracked: Tracked[];
  alerts: Alert[]; status: (id: string) => Status; setStatus: (id: string, s: Status, note?: string) => Promise<void>;
  selected: string | null; select: (id: string | null) => void;
  focusSym: string; setFocusSym: (s: string) => void;
  toasts: Toast[]; dismiss: (id: string) => void; testToast: () => void;
  riskAt: (t: Tracked, i: number) => number; tierOf: (s: number) => string;
  ingest: (items: { symbol: string; csv?: string; parquet?: ArrayBuffer }[]) => Promise<{ symbol: string; loaded: number; dropped: number; reasons: Record<string, number> }[]>;
  reload: () => Promise<void>;
  uploadedSyms: Set<string>;
  rules: ApiRule[]; addRule: (r: { symbol: string; metric: string; threshold: number; note?: string }) => Promise<void>; removeRule: (id: string) => Promise<void>;
  guidance: ApiGuidance[];
  live: LiveStatus | null; startLive: (interval?: number) => Promise<void>; stopLive: () => Promise<void>; pollLive: () => Promise<void>; liveBusy: boolean;
  profiles: Record<string, WatchProfile>; setProfile: (sym: string, p: WatchProfile | null) => void;
  tierFor: (sym: string, s: number) => string;
  cases: CaseFile[]; addCase: (title: string, owner: string) => void; updateCase: (id: string, patch: Partial<CaseFile>) => void; removeCase: (id: string) => void;
  sectorMedian: (sym: string, bar: number) => { peers: number; median: number } | null;
};

const Ctx = createContext<Store | null>(null);
export const useStore = () => { const s = useContext(Ctx); if (!s) throw new Error('no store'); return s; };

export const stateToStatus = (s: AlertState): Status =>
  s === 'ACKNOWLEDGED' ? 'ack' : s === 'ESCALATED' ? 'escalated' : s === 'RESOLVED' ? 'resolved' : 'open';
export const statusToAction: Record<Status, 'acknowledge' | 'escalate' | 'resolve' | 'reopen'> = {
  open: 'reopen', ack: 'acknowledge', escalated: 'escalate', resolved: 'resolve',
};

const WINDOW = 150; // bars fetched per symbol (two sessions)
const SESSION = 75; // bars in the live replay window (one NSE session)

function toSettings(raw: ApiSettings, prev?: Settings): Settings {
  return {
    weights: {
      z: raw.risk_scoring.weights.ZScoreDetector ?? 0.35,
      ewma: raw.risk_scoring.weights.EWMADetector ?? 0.25,
      iforest: raw.risk_scoring.weights.IsolationForestDetector ?? 0.4,
    },
    thresholds: {
      medium: raw.risk_scoring.thresholds.medium ?? 50,
      high: raw.risk_scoring.thresholds.high ?? 70,
      critical: raw.risk_scoring.thresholds.critical ?? 85,
    },
    cooldownBars: raw.cooldown.window_bars,
    zscoreThreshold: raw.detectors.zscore_threshold,
    minObservations: raw.detectors.min_observations,
    ewmaAlpha: raw.detectors.ewma_alpha,
    ewmaThreshold: raw.detectors.ewma_threshold,
    ifRefit: raw.detectors.isolation_forest_refit_interval,
    webhookUrl: raw.notifications.webhook_url,
    minSeverity: raw.notifications.min_severity,
    minScore: prev?.minScore ?? 50,
    speed: prev?.speed ?? 1,
  };
}

const fmtDay = (iso: string) =>
  new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
const fmtTime = (iso: string) => {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
};

const DETECTOR_LABEL: Record<string, string> = { ZScoreDetector: 'Rolling Z-score', EWMADetector: 'EWMA deviation', IsolationForestDetector: 'Isolation Forest' };

export function mapAlert(a: ApiAlert, barsBySym: Record<string, ScoreBar[]>, names: Record<string, { name: string; sector: string }>, uploaded: Set<string>): Alert {
  const series = barsBySym[a.symbol] ?? [];
  const bar = series.findIndex(b => b.iso === a.timestamp);
  const factors = [...(a.explanation?.factors ?? [])]
    .filter(f => f.detail)
    .sort((x, y) => (y.weighted_contribution ?? y.normalized_evidence ?? 0) - (x.weighted_contribution ?? x.normalized_evidence ?? 0));
  const reasons: string[] = [];
  for (const f of factors) {
    if (reasons.length >= 5) break;
    const label = f.detector_name ? DETECTOR_LABEL[f.detector_name] : null;
    const text = label && !f.detail.toLowerCase().startsWith(label.toLowerCase()) ? `${label}: ${f.detail}` : f.detail;
    if (!reasons.includes(text)) reasons.push(text);
  }
  if (!reasons.length && a.explanation?.summary) reasons.push(a.explanation.summary);
  if (!reasons.length) reasons.push('Several signals are mildly elevated at once; no single one is extreme.');
  const contrib = { z: 0, ewma: 0, iforest: 0 };
  for (const f of factors) {
    const pts = (f.weighted_contribution ?? 0) * 100;
    if (f.detector_name === 'ZScoreDetector') contrib.z = Math.max(contrib.z, pts);
    if (f.detector_name === 'EWMADetector') contrib.ewma = Math.max(contrib.ewma, pts);
    if (f.detector_name === 'IsolationForestDetector') contrib.iforest = Math.max(contrib.iforest, pts);
  }
  const move = bar > 0 ? (series[bar].c / series[bar - 1].c - 1) * 100 : 0;
  const meta = names[a.symbol] ?? names[a.symbol.replace(/\.NS$/, '')];
  return {
    id: a.alert_id, sym: a.symbol, name: meta?.name ?? a.symbol, sector: meta?.sector ?? '',
    bar, t: fmtTime(a.timestamp), date: fmtDay(a.timestamp),
    score: Math.round(a.risk_score), sev: a.severity, move, reasons,
    contrib, agreement: bar >= 0 ? series[bar].agreement : 0,
    state: a.state, history: a.history,
    source: uploaded.has(a.symbol) ? 'upload' : 'live',
    simulated: a.is_simulated,
  };
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [stage, setStage] = useState('Connecting to the API');
  const [detectInfo, setDetectInfo] = useState<DetectInfo>(null);
  const [settings, setSettingsRaw] = useState<Settings | null>(null);
  const [barsBySym, setBarsBySym] = useState<Record<string, ScoreBar[]>>({});
  const [names, setNames] = useState<Record<string, { name: string; sector: string }>>({});
  const [apiAlerts, setApiAlerts] = useState<ApiAlert[]>([]);
  const [uploadedSyms, setUploadedSyms] = useState<Set<string>>(new Set());
  const [tick, setTick] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [selected, select] = useState<string | null>(null);
  const [focusSym, setFocusSym] = useState('');
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [applying, setApplying] = useState(false);
  const [rules, setRules] = useState<ApiRule[]>([]);
  const [guidance, setGuidance] = useState<ApiGuidance[]>([]);
  const [live, setLive] = useState<LiveStatus | null>(null);
  const [liveBusy, setLiveBusy] = useState(false);
  const seen = useRef<Set<string> | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setLoadError('');
    try {
      setStage('Reading settings and symbol universe');
      const [rawSettings, universe] = await Promise.all([api.settings(), api.universe().catch(() => ({ entries: {} }))]);
      setSettingsRaw(prev => toSettings(rawSettings, prev ?? undefined));
      const nameMap: Record<string, { name: string; sector: string }> = {};
      for (const [k, v] of Object.entries(universe.entries)) nameMap[k] = { name: v.name, sector: v.sector };
      setNames(nameMap);
      const [ruleList, guideList, liveStatus] = await Promise.all([
        api.rules().catch(() => []), api.guidance().catch(() => []), api.liveStatus().catch(() => null),
      ]);
      setRules(ruleList); setGuidance(guideList); setLive(liveStatus);
      setStage('Running Z-score, EWMA and Isolation Forest over the curated history');
      const det = await api.detect();
      setDetectInfo(det);
      setStage('Loading per-bar scores and alerts');
      const [scores, alerts] = await Promise.all([api.scores(WINDOW), api.alerts()]);
      setBarsBySym(scores.symbols);
      setApiAlerts(alerts);
      const syms = Object.keys(scores.symbols).sort();
      setFocusSym(prev => (prev && scores.symbols[prev] ? prev : syms[0] ?? ''));
      const len = scores.symbols[syms[0]]?.length ?? 0;
      setTick(t => (t > 0 && t < len ? t : Math.max(0, len - 26)));
      setPlaying(true);
    } catch (e) {
      setLoadError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const bars = useMemo(() => Object.values(barsBySym)[0]?.length ?? 0, [barsBySym]);
  const sessionStart = Math.max(0, bars - SESSION);

  useEffect(() => {
    if (!playing || !bars) return;
    const id = setInterval(() => setTick(t => { if (t >= bars - 1) { setPlaying(false); return t; } return t + 1; }), 2600 / (settings?.speed ?? 1));
    return () => clearInterval(id);
  }, [playing, settings?.speed, bars]);

  const tracked: Tracked[] = useMemo(() => Object.entries(barsBySym).sort(([a], [b]) => a.localeCompare(b)).map(([sym, series]) => ({
    sym,
    name: names[sym]?.name ?? names[sym.replace(/\.NS$/, '')]?.name ?? sym,
    sector: names[sym]?.sector ?? names[sym.replace(/\.NS$/, '')]?.sector ?? 'Custom',
    series,
    source: uploadedSyms.has(sym) ? 'upload' as const : 'live' as const,
  })), [barsBySym, names, uploadedSyms]);

  const alerts: Alert[] = useMemo(
    () => apiAlerts
      .map(a => mapAlert(a, barsBySym, names, uploadedSyms))
      .sort((a, b) => (b.bar - a.bar) || (b.score - a.score)),
    [apiAlerts, barsBySym, names, uploadedSyms],
  );

  const [profiles, setProfilesState] = useState<Record<string, WatchProfile>>(() => {
    try { return JSON.parse(localStorage.getItem('mw-profiles') ?? '{}'); } catch { return {}; }
  });
  const [cases, setCasesState] = useState<CaseFile[]>(() => {
    try { return JSON.parse(localStorage.getItem('mw-cases') ?? '[]'); } catch { return []; }
  });
  useEffect(() => { try { localStorage.setItem('mw-profiles', JSON.stringify(profiles)); } catch { /* ignore */ } }, [profiles]);
  useEffect(() => { try { localStorage.setItem('mw-cases', JSON.stringify(cases)); } catch { /* ignore */ } }, [cases]);

  const setProfile = useCallback((sym: string, p: WatchProfile | null) => {
    setProfilesState(prev => { const n = { ...prev }; if (p) n[sym] = p; else delete n[sym]; return n; });
  }, []);
  const tierFor = useCallback((sym: string, s: number) => {
    const th = profiles[sym] ?? (settings ?? { thresholds: { medium: 50, high: 70, critical: 85 } }).thresholds;
    return tierFromThresholds(s, th);
  }, [profiles, settings]);
  const addCase = useCallback((title: string, owner: string) => {
    setCasesState(prev => [{ id: `case-${Date.now().toString(36)}`, title: title.trim() || 'Untitled case', owner: owner.trim(), status: 'open', created: new Date().toISOString(), alertIds: [], notes: [] }, ...prev]);
  }, []);
  const updateCase = useCallback((id: string, patch: Partial<CaseFile>) => {
    setCasesState(prev => prev.map(c => (c.id === id ? { ...c, ...patch } : c)));
  }, []);
  const removeCase = useCallback((id: string) => { setCasesState(prev => prev.filter(c => c.id !== id)); }, []);
  const sectorMedian = useCallback((sym: string, bar: number) => {
    const self = tracked.find(t => t.sym === sym);
    if (!self) return null;
    const moves = tracked.filter(t => t.sym !== sym && t.sector === self.sector).map(t => {
      const i = Math.min(bar, t.series.length - 1);
      if (i <= 0) return null;
      return (t.series[i].c / t.series[i - 1].c - 1) * 100;
    }).filter((x): x is number => x !== null).sort((a, b) => a - b);
    if (!moves.length) return null;
    return { peers: moves.length, median: moves[Math.floor(moves.length / 2)] };
  }, [tracked]);

  const channels = useMemo(() => {
    if (!settings) return ['dashboard only'];
    if (settings.webhookUrl) {
      try { return [`webhook (${new URL(settings.webhookUrl).host})`, 'dashboard']; } catch { return ['webhook', 'dashboard']; }
    }
    return ['dashboard only'];
  }, [settings]);

  useEffect(() => {
    if (!alerts.length) return;
    if (!seen.current) { seen.current = new Set(alerts.map(a => a.id)); return; }
    const fresh = alerts.filter(a => !seen.current!.has(a.id));
    fresh.forEach(a => seen.current!.add(a.id));
    const loud = fresh.filter(a => a.bar >= 0 && a.bar <= tick && a.state === 'NEW' && settings && a.score >= settings.thresholds.high);
    if (loud.length) setToasts(ts => [...loud.slice(0, 2).map(a => ({ id: `${a.id}-${Date.now()}`, alert: a, channels })), ...ts].slice(0, 3));
  }, [alerts, tick, settings, channels]);

  useEffect(() => {
    if (!toasts.length) return;
    const id = setTimeout(() => setToasts(ts => ts.slice(0, -1)), 6500);
    return () => clearTimeout(id);
  }, [toasts]);

  const setStatus = useCallback(async (id: string, s: Status, note?: string) => {
    const updated = await api.act(id, statusToAction[s], note);
    setApiAlerts(list => list.map(a => (a.alert_id === id ? updated : a)));
  }, []);

  const applySettings = useCallback(async () => {
    if (!settings) return;
    setApplying(true);
    try {
      await api.putSettings({
        risk_scoring: {
          weights: { ZScoreDetector: settings.weights.z, EWMADetector: settings.weights.ewma, IsolationForestDetector: settings.weights.iforest },
          thresholds: { low: 0, ...settings.thresholds },
        },
        detectors: {
          zscore_threshold: settings.zscoreThreshold,
          min_observations: settings.minObservations,
          ewma_alpha: settings.ewmaAlpha,
          ewma_threshold: settings.ewmaThreshold,
          isolation_forest_refit_interval: settings.ifRefit,
        },
        cooldown: { window_bars: settings.cooldownBars },
        notifications: { webhook_url: settings.webhookUrl, min_severity: settings.minSeverity },
      });
      seen.current = null;
      await load();
    } finally {
      setApplying(false);
    }
  }, [settings, load]);

  const ingest = useCallback(async (items: { symbol: string; csv?: string; parquet?: ArrayBuffer }[]) => {
    const results: { symbol: string; loaded: number; dropped: number; reasons: Record<string, number> }[] = [];
    for (const item of items) {
      const r = await api.ingest(item.symbol, item.parquet ?? item.csv ?? '', Boolean(item.parquet));
      results.push({ symbol: r.symbol, loaded: r.rows_loaded, dropped: r.rows_dropped, reasons: r.invalid_reasons });
    }
    setUploadedSyms(prev => new Set([...prev, ...results.map(r => r.symbol)]));
    seen.current = null;
    await load();
    return results;
  }, [load]);

  if (!settings) {
    // still on first load; expose a minimal shell so screens render the loader
  }

  const store: Store = {
    loading, loadError, stage, detectInfo,
    tick, playing, setPlaying,
    restart: () => { seen.current = null; setTick(sessionStart); setPlaying(true); },
    sessionStart, bars,
    settings: settings ?? {
      weights: { z: 0.35, ewma: 0.25, iforest: 0.4 },
      thresholds: { medium: 50, high: 70, critical: 85 },
      cooldownBars: 6, zscoreThreshold: 3, minObservations: 3, ewmaAlpha: 0.3, ewmaThreshold: 2.5,
      ifRefit: 8, webhookUrl: '', minSeverity: 'HIGH', minScore: 50, speed: 1,
    },
    setSettings: setSettingsRaw,
    applySettings, applying,
    tracked, alerts,
    status: id => stateToStatus(apiAlerts.find(a => a.alert_id === id)?.state ?? 'NEW'),
    setStatus,
    selected, select, focusSym, setFocusSym,
    toasts, dismiss: id => setToasts(ts => ts.filter(t => t.id !== id)),
    testToast: () => { const a = alerts[0]; if (a) setToasts(ts => [{ id: `test-${Date.now()}`, alert: a, channels }, ...ts].slice(0, 3)); },
    riskAt: (t, i) => t.series[Math.max(0, Math.min(i, t.series.length - 1))]?.risk ?? 0,
    tierOf: s => tierFromThresholds(s, (settings ?? { thresholds: { medium: 50, high: 70, critical: 85 } }).thresholds),
    ingest,
    reload: load,
    uploadedSyms,
    rules,
    addRule: async (r) => { await api.addRule(r); setRules(await api.rules()); },
    removeRule: async (id) => { await api.removeRule(id); setRules(await api.rules()); },
    guidance,
    live,
    startLive: async (interval) => { setLiveBusy(true); try { setLive(await api.liveStart(interval)); } finally { setLiveBusy(false); } },
    stopLive: async () => { setLiveBusy(true); try { setLive(await api.liveStop()); } finally { setLiveBusy(false); } },
    profiles, setProfile, tierFor, cases, addCase, updateCase, removeCase, sectorMedian,
    pollLive: async () => {
      setLiveBusy(true);
      try {
        await api.livePoll();
        setLive(await api.liveStatus());
        setGuidance(await api.guidance().catch(() => []));
        setApiAlerts(await api.alerts().catch(() => []));
      } finally { setLiveBusy(false); }
    },
    liveBusy,
  };
  return <Ctx.Provider value={store}>{children}</Ctx.Provider>;
}
