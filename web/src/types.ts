export type Candle = { t: string; o: number; h: number; l: number; c: number; v: number };

export type ScoreBar = Candle & {
  iso: string;
  slot: number;
  log_return: number;
  volume_ratio: number;
  park: number;
  pressure: number;
  z_ret: number;
  z_vol: number;
  z_pressure: number;
  ewma_dev: number;
  if_score: number;
  risk: number;
  severity: string;
  valid: boolean;
  contrib: { z: number; ewma: number; iforest: number };
  agreement: number;
};

export type AlertState = 'NEW' | 'ACKNOWLEDGED' | 'ESCALATED' | 'RESOLVED';
export type Status = 'open' | 'ack' | 'resolved' | 'escalated';

export type AlertEvent = { timestamp: string; from_state: AlertState | null; to_state: AlertState; note: string | null };

export type ExplanationFactor = {
  factor_type: string; key: string; label: string; detail: string;
  detector_name: string | null; feature_name: string | null;
  value: number | null; threshold: number | null;
  normalized_evidence: number | null; weighted_contribution: number | null;
  valid: boolean; reason: string | null;
};

export type ApiAlert = {
  alert_id: string; symbol: string; timestamp: string; slot_index: number;
  risk_score: number; severity: string; state: AlertState;
  explanation: { summary: string; factors: ExplanationFactor[]; contributing_detectors: string[]; disclaimer: string } | null;
  is_simulated: boolean; simulation_metadata: Record<string, unknown>; history: AlertEvent[];
};

export type Alert = {
  id: string; sym: string; name: string; sector: string; bar: number; t: string; date: string;
  score: number; sev: string; move: number; reasons: string[];
  contrib: { z: number; ewma: number; iforest: number }; agreement: number;
  state: AlertState; history: AlertEvent[]; source: 'live' | 'upload'; simulated: boolean;
};

export type Tracked = { sym: string; name: string; sector: string; series: ScoreBar[]; source: 'live' | 'upload' };

export type Settings = {
  weights: { z: number; ewma: number; iforest: number };
  thresholds: { medium: number; high: number; critical: number };
  cooldownBars: number;
  zscoreThreshold: number;
  minObservations: number;
  ewmaAlpha: number;
  ewmaThreshold: number;
  ifRefit: number;
  webhookUrl: string;
  minSeverity: string;
  minScore: number; // client-side queue filter
  speed: number;
};

export type ApiSettings = {
  risk_scoring: { weights: Record<string, number>; thresholds: Record<string, number> };
  detectors: { zscore_threshold: number; min_observations: number; ewma_alpha: number; ewma_threshold: number; isolation_forest_refit_interval: number };
  cooldown: { window_bars: number; minutes: number };
  notifications: { webhook_url: string; min_severity: string };
  replay: { default_speed: number; auto_play: boolean };
};

export type ApiRule = {
  id: string; symbol: string; metric: string; threshold: number;
  note: string; enabled: boolean; created_at: string;
};

export type ApiGuidance = {
  id: string; rule_id: string; symbol: string; timestamp: string;
  metric: string; threshold: number; observed: number; close: number;
  pct_change: number; volume_ratio: number | null; risk: number | null;
  zscore: number | null; pressure: number | null;
  title: string; suggestion: string; note: string; disclaimer: string;
};

export type LiveStatus = {
  running: boolean; interval_sec: number; source: string; delay_note: string;
  available: boolean; last_poll: string | null;
  last_summary: { new_bars?: number; new_alerts?: number; guidance_fired?: number; polled_at?: string };
  errors: string[];
};

export const RULE_METRICS: { id: string; label: string; hint: string }[] = [
  { id: 'price_above', label: 'Price rises above', hint: 'Rs level' },
  { id: 'price_below', label: 'Price falls below', hint: 'Rs level' },
  { id: 'pct_change_up', label: 'Jumps up in one bar', hint: '% move' },
  { id: 'pct_change_down', label: 'Drops in one bar', hint: '% move' },
  { id: 'volume_spike', label: 'Volume spike', hint: 'x average' },
  { id: 'risk_above', label: 'Fused risk at least', hint: '0-100' },
  { id: 'zscore_above', label: 'Z-score beyond', hint: 'sigma' },
  { id: 'pressure_above', label: 'Buy pressure above', hint: '-1..1' },
  { id: 'pressure_below', label: 'Sell pressure below', hint: '-1..1' },
];
