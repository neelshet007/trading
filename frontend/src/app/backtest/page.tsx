'use client';

import { useState } from 'react';
import { Sidebar } from '@/components/Sidebar';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Download,
  FlaskConical,
  TrendingUp,
  TrendingDown,
  BarChart3,
  ShieldCheck,
  Zap,
  Activity,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

// ── Safe numeric helpers ───────────────────────────────────────────────────────
function fmtNum(v: number | undefined | null, decimals = 2): string {
  if (v == null || isNaN(v)) return '—';
  return v.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}
function fmtInt(v: number | undefined | null): string {
  if (v == null || isNaN(v)) return '—';
  return Math.round(v).toLocaleString();
}
function fmtPct(v: number | undefined | null, sign = false): string {
  if (v == null || isNaN(v)) return '—';
  return `${sign && v > 0 ? '+' : ''}${v.toFixed(2)}%`;
}
function fmtUsd(v: number | undefined | null): string {
  if (v == null || isNaN(v)) return '—';
  return `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

// ── Types ─────────────────────────────────────────────────────────────────────
interface TradeLog {
  date_time: string;
  market_context: string;
  trade_type: string;
  direction: string;
  trigger_why: string;
  entry_price?: number;
  stop_loss?: number;
  target?: number;
  exit_price?: number;
  risk_reward?: number;
  pnl_pct?: number;
  pnl_dollars?: number;
  account_equity?: number;
  result?: string;
  confluence_score?: number;
  trade_balance_before?: number;
  dollar_risk?: number;
  position_size?: number;
}

interface BacktestStats {
  total_trades: number;
  win_rate_pct: number;
  profit_factor: number;
  max_drawdown_pct: number;
  max_drawdown_usd: number;
  sharpe_ratio: number;
  total_return_pct: number;
  final_equity_usd: number;
  buy_hold_return_pct: number;
  alpha_vs_bnh_pct: number;
  wins: number;
  losses: number;
  avg_confluence_score?: number;
}

interface BacktestResult {
  stats: BacktestStats;
  trades: TradeLog[];
}

const SYMBOLS = [
  'BTC-USD',
  'ETH-USD',
  'SOL-USD',
  'XRP-USD',
  'BNB-USD',
  'DOGE-USD',
  'ADA-USD',
  'TRX-USD',
  'LINK-USD',
  'AVAX-USD',
  'DOT-USD',
  'TON11419-USD',
  'SHIB-USD',
  'SUI20947-USD',
  'HBAR-USD',
  'BCH-USD',
  'LTC-USD',
  'XLM-USD',
  'UNI7083-USD',
  'APT21794-USD',
  'NEAR-USD',
  'PEPE24478-USD',
  'ICP-USD',
  'ETC-USD',
  'AAVE-USD',
  'MKR-USD',
  'ARB11841-USD',
  'OP-USD',
  'INJ-USD',
  'FIL-USD',
  'ATOM-USD',
  'RENDER-USD',
  'TAO22974-USD',
  'SEI23149-USD',
  'FET-USD',
  'VET-USD',
  'RUNE-USD',
  'TIA22861-USD',
  'JUP29210-USD',
  'WIF-USD',
  'BONK-USD',
  'ALGO-USD',
  'IMX10603-USD',
  'STX4847-USD',
  'FLOW-USD',
  'GRT6719-USD',
  'EOS-USD',
  'THETA-USD',
  'SAND-USD',
  'MANA-USD',
];

// ── Component ─────────────────────────────────────────────────────────────────
export default function BacktestPage() {
  const [symbol, setSymbol] = useState('BTC-USD');
  const [start, setStart]   = useState('2023-01-01');
  const [end, setEnd]       = useState('2025-12-31');
  const [initialCapital, setInitialCapital] = useState('10000');
  const [loading, setLoading]     = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError]   = useState<string | null>(null);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  const API = 'http://localhost:8000';

  const runBacktest = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const cap = parseFloat(initialCapital) || 10000;
      const res = await fetch(
        `${API}/backtest/stats?symbol=${encodeURIComponent(symbol)}&start=${start}&end=${end}&initial_capital=${cap}`
      );
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Backtest failed.');
      }
      const data: BacktestResult = await res.json();
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const downloadExcel = async () => {
    setDownloading(true);
    try {
      const cap = parseFloat(initialCapital) || 10000;
      const res = await fetch(
        `${API}/backtest/download?symbol=${encodeURIComponent(symbol)}&start=${start}&end=${end}&initial_capital=${cap}`
      );
      if (!res.ok) throw new Error('Export failed');
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = `SMC_Backtest_${symbol.replace('-', '_')}_${start.slice(0, 4)}_${end.slice(0, 4)}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Download failed');
    } finally {
      setDownloading(false);
    }
  };

  const stats = result?.stats;

  // Build stat cards with fully safe string values
  const statCards = stats
    ? [
        { label: 'Win Rate',       value: fmtPct(stats.win_rate_pct),            icon: ShieldCheck,  color: 'emerald', pos: (stats.win_rate_pct ?? 0) >= 50 },
        { label: 'Profit Factor',  value: `${fmtNum(stats.profit_factor)}x`,     icon: BarChart3,    color: 'cyan',    pos: (stats.profit_factor ?? 0) >= 1  },
        { label: 'Max Drawdown',   value: `-${fmtPct(stats.max_drawdown_pct)} (${fmtUsd(stats.max_drawdown_usd)})`, icon: TrendingDown, color: 'rose', pos: false },
        { label: 'Sharpe Ratio',   value: fmtNum(stats.sharpe_ratio),            icon: Activity,     color: 'violet',  pos: (stats.sharpe_ratio ?? 0) >= 1    },
        { label: 'Total Return',   value: fmtPct(stats.total_return_pct, true),  icon: TrendingUp,   color: 'emerald', pos: (stats.total_return_pct ?? 0) > 0  },
        { label: 'Final Equity',   value: fmtUsd(stats.final_equity_usd),        icon: TrendingUp,   color: 'cyan',    pos: (stats.final_equity_usd ?? 0) > 10000 },
        { label: 'BTC Buy & Hold', value: fmtPct(stats.buy_hold_return_pct, true), icon: BarChart3,  color: 'amber',   pos: (stats.buy_hold_return_pct ?? 0) > 0 },
        { label: 'SMC Alpha',      value: fmtPct(stats.alpha_vs_bnh_pct, true),  icon: Zap,          color: 'violet',  pos: (stats.alpha_vs_bnh_pct ?? 0) > 0  },
        { label: 'Avg Score',      value: `${stats.avg_confluence_score ?? '—'}/10`,  icon: ShieldCheck,  color: 'amber',   pos: (stats.avg_confluence_score ?? 0) >= 6 },
      ]
    : [];

  return (
    <div className="flex h-screen overflow-hidden bg-[radial-gradient(circle_at_top,rgba(30,64,175,0.10),transparent_40%),linear-gradient(180deg,#020617_0%,#07111f_50%,#020617_100%)] text-slate-200">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8 border-l border-slate-800">

        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <FlaskConical className="h-7 w-7 text-violet-400" />
            <h1 className="text-3xl font-bold tracking-tight text-white">Crypto SMC / ICT Backtester</h1>
            <Badge className="bg-violet-500/20 text-violet-300 border border-violet-500/30 text-xs tracking-widest hover:bg-violet-500/20">
              QUANTITATIVE ENGINE
            </Badge>
          </div>
          <p className="text-slate-400 max-w-3xl">
            Full structural SMC backtest — Liquidity Sweeps, BOS, FVG Confirmation &amp; Order Block entries
            across 1H candles. Generates a forensic Excel workbook on completion.
          </p>
        </div>

        {/* Config */}
        <Card className="border-slate-800 bg-slate-950/70 mb-6">
          <CardHeader className="border-b border-slate-800 pb-4">
            <CardTitle className="text-sm uppercase tracking-widest text-slate-400">
              Backtest Configuration
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-5">
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
              <div>
                <label className="text-[10px] uppercase text-slate-500 font-bold mb-1.5 block tracking-widest">Symbol</label>
                <select
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 text-slate-200 rounded px-3 py-2.5 text-sm focus:ring-1 focus:ring-violet-500 outline-none"
                >
                  {SYMBOLS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="text-[10px] uppercase text-slate-500 font-bold mb-1.5 block tracking-widest">Start Date</label>
                <input
                  type="date" value={start}
                  onChange={(e) => setStart(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 text-slate-200 rounded px-3 py-2.5 text-sm focus:ring-1 focus:ring-violet-500 outline-none"
                />
              </div>
              <div>
                <label className="text-[10px] uppercase text-slate-500 font-bold mb-1.5 block tracking-widest">End Date</label>
                <input
                  type="date" value={end}
                  onChange={(e) => setEnd(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 text-slate-200 rounded px-3 py-2.5 text-sm focus:ring-1 focus:ring-violet-500 outline-none"
                />
              </div>
              <div>
                <label className="text-[10px] uppercase text-slate-500 font-bold mb-1.5 block tracking-widest">Initial Capital ($)</label>
                <input
                  type="number" value={initialCapital}
                  onChange={(e) => setInitialCapital(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 text-slate-200 rounded px-3 py-2.5 text-sm focus:ring-1 focus:ring-violet-500 outline-none font-mono"
                />
              </div>
              <button
                onClick={runBacktest}
                disabled={loading}
                className="flex items-center justify-center gap-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold rounded px-5 py-3 text-sm transition-all shadow-[0_0_20px_rgba(139,92,246,0.3)] hover:shadow-[0_0_30px_rgba(139,92,246,0.5)]"
              >
                {loading ? (
                  <><Activity className="h-4 w-4 animate-spin" />Running Backtest...</>
                ) : (
                  <><Zap className="h-4 w-4" />Run Backtest</>
                )}
              </button>
            </div>
            {loading && (
              <div className="mt-4 text-xs text-violet-400 animate-pulse flex items-center gap-2">
                <Activity className="h-3 w-3 animate-spin" />
                Fetching 1H candles from 2023–2025, applying SMC/ICT engine… this may take 20–40 seconds.
              </div>
            )}
          </CardContent>
        </Card>

        {error && (
          <div className="mb-6 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-300">
            ⚠️ {error}
          </div>
        )}

        {/* Stats Dashboard */}
        {stats && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {statCards.map(({ label, value, icon: Icon, color, pos }) => (
                <Card key={label} className="border-slate-800 bg-slate-950/70 relative overflow-hidden">
                  <div className={`absolute inset-0 bg-${color}-500/5 pointer-events-none`} />
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] uppercase tracking-widest text-slate-500">{label}</span>
                      <Icon className={`h-4 w-4 text-${color}-400`} />
                    </div>
                    <div className={`text-2xl font-bold ${pos ? 'text-emerald-400' : label === 'Max Drawdown' ? 'text-rose-400' : 'text-slate-200'}`}>
                      {value}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Win/Loss bar */}
            <Card className="border-slate-800 bg-slate-950/70 mb-6">
              <CardContent className="p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs uppercase tracking-widest text-slate-400">
                    Trade Distribution — {fmtInt(stats.total_trades)} total trades
                  </span>
                  <div className="flex gap-4 text-xs">
                    <span className="text-emerald-400">✅ {fmtInt(stats.wins)} Wins</span>
                    <span className="text-rose-400">❌ {fmtInt(stats.losses)} Losses</span>
                  </div>
                </div>
                <div className="h-3 rounded-full bg-slate-800 overflow-hidden flex">
                  <div
                    className="h-full bg-emerald-500 transition-all duration-700"
                    style={{ width: `${stats.win_rate_pct ?? 0}%` }}
                  />
                  <div className="h-full bg-rose-500 flex-1" />
                </div>
              </CardContent>
            </Card>

            {/* Download */}
            <div className="flex justify-end mb-6">
              <button
                onClick={downloadExcel}
                disabled={downloading}
                className="flex items-center gap-2 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold rounded-lg px-6 py-3 text-sm transition-all shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:shadow-[0_0_30px_rgba(16,185,129,0.5)]"
              >
                <Download className="h-4 w-4" />
                {downloading ? 'Generating Excel…' : 'Download Forensic Excel Report (.xlsx)'}
              </button>
            </div>

            {/* Trade log table */}
            <Card className="border-slate-800 bg-slate-950/70">
              <CardHeader className="border-b border-slate-800 pb-4">
                <CardTitle className="text-sm uppercase tracking-widest text-slate-400 flex items-center gap-2">
                  <FlaskConical className="h-4 w-4 text-violet-400" />
                  SMC Forensic Trade Log
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 bg-slate-900/50">
                        {['Date_Time','Type','Dir','Entry','SL','Target','Exit','PnL%','Equity','Result'].map(h => (
                          <th key={h} className="px-3 py-3 text-left text-[10px] uppercase tracking-widest text-slate-500 font-semibold whitespace-nowrap">{h}</th>
                        ))}
                        <th className="px-3 py-3 w-8" />
                      </tr>
                    </thead>
                    <tbody>
                      {result?.trades.map((trade, idx) => {
                        const isWin  = trade.result?.includes('Target');
                        const isLoss = trade.result?.includes('Stopped');
                        const expanded = expandedRow === idx;

                        return (
                          <>
                            <tr
                              key={idx}
                              onClick={() => setExpandedRow(expanded ? null : idx)}
                              className={`border-b transition-colors cursor-pointer ${
                                isWin  ? 'border-emerald-500/10 bg-emerald-500/5 hover:bg-emerald-500/10' :
                                isLoss ? 'border-rose-500/10   bg-rose-500/5   hover:bg-rose-500/10' :
                                         'border-slate-800      bg-slate-900/20  hover:bg-slate-900/50'
                              }`}
                            >
                              <td className="px-3 py-2.5 text-slate-400 whitespace-nowrap">
                                {trade.date_time ? trade.date_time.slice(0, 16) : '—'}
                              </td>
                              <td className="px-3 py-2.5">
                                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${
                                  trade.trade_type === 'Swing'
                                    ? 'bg-violet-500/20 text-violet-300 border-violet-500/30'
                                    : 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30'
                                }`}>{trade.trade_type ?? '—'}</span>
                              </td>
                              <td className="px-3 py-2.5">
                                <span className={`font-bold ${trade.direction === 'LONG' ? 'text-emerald-400' : 'text-rose-400'}`}>
                                  {trade.direction === 'LONG' ? '↑' : '↓'} {trade.direction ?? '—'}
                                </span>
                              </td>
                              <td className="px-3 py-2.5 text-slate-300 font-mono">{fmtUsd(trade.entry_price)}</td>
                              <td className="px-3 py-2.5 text-rose-400 font-mono">{fmtUsd(trade.stop_loss)}</td>
                              <td className="px-3 py-2.5 text-emerald-400 font-mono">{fmtUsd(trade.target)}</td>
                              <td className="px-3 py-2.5 text-slate-300 font-mono">{fmtUsd(trade.exit_price)}</td>
                              <td className={`px-3 py-2.5 font-bold font-mono ${
                                (trade.pnl_pct ?? 0) > 0 ? 'text-emerald-400' :
                                (trade.pnl_pct ?? 0) < 0 ? 'text-rose-400' : 'text-slate-400'
                              }`}>
                                {trade.pnl_pct != null ? fmtPct(trade.pnl_pct, true) : '—'}
                              </td>
                              <td className="px-3 py-2.5 text-slate-300 font-mono">{fmtUsd(trade.account_equity)}</td>
                              <td className="px-3 py-2.5">
                                <span className={`text-xs font-semibold ${
                                  isWin ? 'text-emerald-400' : isLoss ? 'text-rose-400' : 'text-amber-400'
                                }`}>
                                  {trade.result ?? '—'}
                                </span>
                              </td>
                              <td className="px-3 py-2.5 text-slate-600">
                                {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                              </td>
                            </tr>
                            {expanded && (
                              <tr key={`${idx}-detail`} className="border-b border-slate-800 bg-slate-900/60">
                                <td colSpan={11} className="px-6 py-4">
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="space-y-4">
                                      <div>
                                        <div className="text-[10px] uppercase text-violet-400 font-bold mb-1 tracking-widest">📍 SMC Trigger (Why)</div>
                                        <div className="text-slate-300 text-xs leading-relaxed">{trade.trigger_why ?? '—'}</div>
                                      </div>
                                      <div>
                                        <div className="text-[10px] uppercase text-cyan-400 font-bold mb-1 tracking-widest">📊 Market Context</div>
                                        <div className="text-slate-300 text-xs leading-relaxed">{trade.market_context ?? '—'}</div>
                                      </div>
                                    </div>
                                    <div className="border border-slate-700/50 bg-slate-900/50 rounded-lg p-3 grid grid-cols-2 gap-3">
                                      <div>
                                        <div className="text-[10px] uppercase text-slate-500 font-bold mb-1 tracking-widest">Risk Amount</div>
                                        <div className="text-amber-400 font-mono text-sm font-bold">{fmtUsd(trade.dollar_risk)}</div>
                                      </div>
                                      <div>
                                        <div className="text-[10px] uppercase text-slate-500 font-bold mb-1 tracking-widest">Pos Size (Units)</div>
                                        <div className="text-slate-200 font-mono text-sm">{trade.position_size?.toLocaleString(undefined, { maximumFractionDigits: 4 }) ?? '—'}</div>
                                      </div>
                                      <div>
                                        <div className="text-[10px] uppercase text-slate-500 font-bold mb-1 tracking-widest">Bal Before Trade</div>
                                        <div className="text-slate-300 font-mono text-sm">{fmtUsd(trade.trade_balance_before)}</div>
                                      </div>
                                      <div>
                                        <div className="text-[10px] uppercase text-slate-500 font-bold mb-1 tracking-widest">Net PnL</div>
                                        <div className={`font-mono text-sm font-bold ${(trade.pnl_dollars ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                          {fmtUsd(trade.pnl_dollars)}
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                </td>
                              </tr>
                            )}
                          </>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </main>
    </div>
  );
}
