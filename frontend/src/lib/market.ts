export type MarketKey = 'USA' | 'INDIA' | 'CRYPTO' | 'COMMODITIES';

export interface ProbabilityInsight {
  breakout: string;
  trend_continuation: string;
}

export interface AnalysisSummary {
  headline: string;
  explanation: string;
  why_now: string;
  rating: string;
  categories: string[];
  pattern_descriptions: string[];
  probability: ProbabilityInsight;
}

export interface PatternDetail {
  name: string;
  strength: number;
  breakout_level: number;
  description: string;
}

export interface Signal {
  symbol: string;
  market: MarketKey;
  strategy: string;
  signal: 'bullish' | 'bearish' | 'neutral';
  score: number;
  reasons: string[];
  timeframe: 'intraday' | 'swing';
  entry_zone?: number;
  stop_loss?: number;
  target?: number;
  risk_reward?: number;
  timestamp: string;
  timestamp_display_ist?: string;
  patterns: string[];
  pattern_strength?: number;
  breakout_level?: number;
  categories: string[];
  confluence_score?: number;
  pattern_details: PatternDetail[];
  probability?: ProbabilityInsight;
  analysis_summary?: AnalysisSummary;
}

export interface SearchResult {
  symbol: string;
  clean_symbol?: string;
  fetch_symbol?: string;
  name: string;
  market: MarketKey;
  exchange?: string;
  signal?: 'bullish' | 'bearish' | 'neutral' | string;
  rating?: string;
  categories?: string[];
  analysis?: {
    why_now?: string;
  } | null;
  price?: number | null;
  change_percent?: number | null;
  rsi?: number | null;
  volume?: number | null;
  updated_at?: string | null;
}

export interface MarketClock {
  market: MarketKey;
  timestamp_utc: string;
  india_time: string;
  india_label: string;
  display_timezone: string;
  local_time: string;
  local_label: string;
  phase: 'open' | 'closed' | 'extended';
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

export function getStatusBadgeClasses(color?: string) {
  if (color === 'green') return 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
  if (color === 'yellow') return 'bg-amber-500/20 text-amber-200 border border-amber-500/30';
  return 'bg-red-500/20 text-red-300 border border-red-500/30';
}

export function getSignalClasses(signal?: string) {
  if (signal === 'bullish') return 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
  if (signal === 'bearish') return 'bg-red-500/20 text-red-300 border border-red-500/30';
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

export function getWhyNow(signal?: Signal | null) {
  if (!signal) return 'No fresh catalyst has been recorded yet.';
  return signal.analysis_summary?.why_now || signal.reasons?.[0] || 'Price and volume are aligning for a possible move.';
}

export function get_tv_symbol(ticker: string) {
  const normalized = ticker.trim().toUpperCase();
  if (!normalized) return normalized;
  if (normalized.includes(':')) return normalized;
  if (normalized.endsWith('.NS')) return `NSE:${normalized.slice(0, -3)}`;
  if (normalized.endsWith('.BO')) return `BSE:${normalized.slice(0, -3)}`;
  return normalized;
}
