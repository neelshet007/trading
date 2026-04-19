export type MarketKey = 'CRYPTO';

export interface RegimeContext {
  hmm_state: number;
  hmm_regime: string;
  regime_confidence: number;
  ipda_cycle: string;
  institutional_bias: string;
  correlated_factors: string[];
}

export interface MarketFootprint {
  htf_range_low: number;
  htf_range_high: number;
  nearest_order_block_low?: number | null;
  nearest_order_block_high?: number | null;
  nearest_fvg_low?: number | null;
  nearest_fvg_high?: number | null;
  fvg_atr_multiple?: number | null;
  premium_discount_state: string;
  ote_level?: number | null;
  structure_signal: string;
  cvd_divergence: string;
  liquidation_sweep_confirmed: boolean;
}

export interface TriggerPlan {
  entry_model: string;
  entry_price: number;
  entry_band_low: number;
  entry_band_high: number;
  stop_loss: number;
  take_profit: number;
  invalidation: string;
  execution_timeframe: string;
  confirmation: string;
}

export interface RiskEnvelope {
  var_95: number;
  gjr_garch_vol: number;
  convexity_risk: number;
  expected_slippage_bps: number;
  funding_rate_clamp_bps: number;
  max_equity_allocation: number;
  recommended_equity_allocation: number;
  r_multiple: number;
  expectancy: number;
}

export interface HumanLoopAssessment {
  inducement_traps: string[];
  human_checks: string[];
  automation_risk: string;
}

export interface ConfluenceScore {
  trend_alignment: number;
  fvg_mitigation: number;
  idm_sweep: number;
  discount_premium: number;
  order_flow_alignment: number;
  total_score: number;
}

export interface NarrativeDetail {
  reason: string;
  location: string;
  context: string;
  score_breakdown: string[];
  timeline: string[];
  zoom_reason?: string | null;
}

export interface SetupSignal {
  symbol: string;
  bias: 'bullish' | 'bearish' | 'neutral' | string;
  status: string;
  timestamp?: string;
  entry?: number;
  stop_loss?: number;
  take_profit?: number;
  risk_reward?: number;
  confluence: ConfluenceScore;
  context: RegimeContext;
  footprint: MarketFootprint;
  trigger: TriggerPlan;
  risk: RiskEnvelope;
  hitl: HumanLoopAssessment;
  narrative?: NarrativeDetail | null;
  ob_top?: number | null;
  ob_bottom?: number | null;
  zoom_resolution?: string | null;
  trade_classification?: string | null;
  margin_multiple?: string | null;
  auto_square_off?: string | null;
}

export interface SearchResult {
  symbol: string;
  clean_symbol?: string;
  fetch_symbol?: string;
  name: string;
  market: MarketKey;
  exchange?: string;
}

export interface MarketClock {
  market: MarketKey;
  timestamp_utc: string;
  india_time: string;
  india_label: string;
  display_timezone: string;
  local_time: string;
  local_label: string;
  phase: 'open';
  status_text: string;
  status_color: 'green' | 'red' | 'yellow';
  is_open: boolean;
}

export interface MarketSummary {
  market?: MarketKey;
  status: string;
  bullish_count: number;
  bearish_count: number;
  sector_strength: Record<string, string>;
  timestamp: string;
  timestamp_display_ist?: string;
  market_clock: MarketClock;
}

export interface SegmentScanResponse {
  segment: string;
  title: string;
  backend_market: string;
  default_timeframe: string;
  poll_interval_seconds: number;
  activation_ttl_seconds: number;
  scanner_focus: string;
  margin_profile: string;
  zoom_resolution: string;
  active: boolean;
  status: string;
  last_accessed?: string;
  last_completed?: string;
  last_error?: string | null;
  market_clock: MarketClock;
  opportunities: SetupSignal[];
}

export interface ForensicReport {
  symbol: string;
  formation: string;
  catalyst: string;
  checklist: {
    regime_allows_execution: boolean;
    liquidity_swept: boolean;
    fvg_created: boolean;
    in_ote_zone: boolean;
    cvd_supportive: boolean;
  };
  derivative_stats: {
    funding_rate_clamp_bps: number;
    liquidation_bias: string;
    cvd_divergence: string;
  };
  instruction: string;
  entry: number;
  stop_loss: number;
  take_profit: number;
  risk_reward: number;
  context: RegimeContext;
  footprint: MarketFootprint;
  risk: RiskEnvelope;
  hitl: HumanLoopAssessment;
  zoom_resolution?: string | null;
  trade_classification?: string | null;
  margin_multiple?: string | null;
  auto_square_off?: string | null;
}

export function getStatusBadgeClasses(color?: string) {
  if (color === 'green') return 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
  if (color === 'yellow') return 'bg-amber-500/20 text-amber-200 border border-amber-500/30';
  return 'bg-red-500/20 text-red-300 border border-red-500/30';
}

export function getSignalClasses(signal?: string) {
  if (signal === 'bullish') return 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
  if (signal === 'bearish') return 'bg-rose-500/20 text-rose-300 border border-rose-500/30';
  return 'bg-amber-500/20 text-amber-200 border border-amber-500/30';
}

export function formatDisplayTime(timestamp?: string, timeZone = 'Asia/Kolkata') {
  if (!timestamp) return '--';
  return new Intl.DateTimeFormat('en-IN', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone,
  }).format(new Date(timestamp));
}

export function formatDisplayDate(timestamp?: string, timeZone = 'Asia/Kolkata') {
  if (!timestamp) return '--';
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone,
  }).format(new Date(timestamp));
}

export function getWhyNow(signal?: SetupSignal | null) {
  if (!signal) return 'No qualified crypto catalyst is active right now.';
  return signal.narrative?.reason || signal.trigger.confirmation || signal.context.ipda_cycle;
}

export function get_tv_symbol(ticker: string) {
  const normalized = ticker.trim().toUpperCase();
  if (!normalized) return normalized;
  if (normalized.includes(':')) return normalized;
  if (normalized.endsWith('-USD')) return `BINANCE:${normalized.replace('-USD', 'USDT')}`;
  return normalized;
}
