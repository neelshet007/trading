'use client';

import { useEffect, useState } from 'react';
import { Activity, Clock3, Radar, TrendingUp } from 'lucide-react';

import { Sidebar } from '@/components/Sidebar';
import { useStore } from '@/store/useStore';
import { fetcher } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { SignalCard } from '@/components/SignalCard';
import {
  formatDisplayDate,
  formatDisplayTime,
  getStatusBadgeClasses,
  type MarketSummary,
  type Signal,
} from '@/lib/market';

const MARKET_ICONS: Record<string, string> = {
  USA: 'US',
  INDIA: 'IN',
  CRYPTO: 'CR',
  COMMODITIES: 'CM',
};

export default function Home() {
  const { timeframe, setTimeframe, market, setMarket, marketSummary, setMarketSummary } = useStore();
  const [signals, setSignals] = useState<Signal[]>([]);

  useEffect(() => {
    const loadData = async () => {
      const [summary, signalsData] = await Promise.all([
        fetcher(`/market-summary?market=${market}`),
        fetcher(`/signals?timeframe=${timeframe}&market=${market}`),
      ]);

      if (summary) setMarketSummary(summary as MarketSummary);
      if (signalsData) setSignals(signalsData as Signal[]);
    };

    const initialLoad = window.setTimeout(() => {
      void loadData();
    }, 0);
    const interval = window.setInterval(() => {
      void loadData();
    }, 30000);
    return () => {
      clearTimeout(initialLoad);
      clearInterval(interval);
    };
  }, [timeframe, market, setMarketSummary]);

  const topSignals = signals.slice(0, 10);
  const marketClock = marketSummary?.market_clock;

  return (
    <div className="flex h-screen overflow-hidden bg-[radial-gradient(circle_at_top,rgba(22,78,99,0.18),transparent_30%),linear-gradient(180deg,#020617_0%,#07111f_45%,#020617_100%)] text-slate-200">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mb-8 flex flex-col gap-5 border-b border-slate-800/80 pb-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <span className="rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1 text-xs font-semibold tracking-[0.3em] text-slate-300">
                {MARKET_ICONS[market]}
              </span>
              <Badge className={getStatusBadgeClasses(marketClock?.status_color)}>{marketClock?.status_text || 'Loading session'}</Badge>
            </div>
            <div>
              <h2 className="text-4xl font-bold tracking-tight text-white">{market} Intelligence Terminal</h2>
              <p className="mt-2 max-w-3xl text-slate-400">
                Clean signal ranking with market hours, timezone context, scanner categories, and a direct answer to why each stock matters right now.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-950/70 p-1">
              {(['USA', 'INDIA', 'CRYPTO', 'COMMODITIES'] as const).map((item) => (
                <button
                  key={item}
                  onClick={() => setMarket(item)}
                  className={`rounded-lg px-3 py-2 text-sm font-medium transition-all ${market === item ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  {item}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-950/70 p-1">
              <button
                onClick={() => setTimeframe('intraday')}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition-all ${timeframe === 'intraday' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
              >
                Intraday
              </button>
              <button
                onClick={() => setTimeframe('swing')}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition-all ${timeframe === 'swing' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
              >
                Swing
              </button>
            </div>
          </div>
        </div>

        <div className="mb-8 grid grid-cols-1 gap-6 xl:grid-cols-4">
          <Card className="border-slate-800 bg-slate-950/70 xl:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white"><Clock3 className="h-5 w-5 text-cyan-300" /> Market Status Panel</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="flex flex-wrap items-center gap-3">
                <Badge className={getStatusBadgeClasses(marketClock?.status_color)}>{marketClock?.status_text || 'Unknown'}</Badge>
                <div className="text-sm text-slate-400">
                  Session sentiment: <span className="font-medium text-slate-200">{marketSummary?.status || 'Unknown'}</span>
                </div>
              </div>
              <div className={`grid gap-4 ${market === 'USA' ? 'md:grid-cols-2' : 'md:grid-cols-1'}`}>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <div className="text-xs uppercase tracking-[0.2em] text-slate-500">India Time</div>
                  <div className="mt-2 text-3xl font-semibold text-white">{marketClock?.india_time || '--:--'}</div>
                  <div className="text-sm text-slate-400">IST</div>
                </div>
                {market === 'USA' && (
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                    <div className="text-xs uppercase tracking-[0.2em] text-slate-500">US Time</div>
                    <div className="mt-2 text-3xl font-semibold text-white">{marketClock?.local_time || '--:--'}</div>
                    <div className="text-sm text-slate-400">{marketClock?.local_label || 'ET'}</div>
                  </div>
                )}
              </div>
              <div className="text-sm text-slate-400">
                Last engine update: {formatDisplayTime(marketSummary?.timestamp)} IST on {formatDisplayDate(marketSummary?.timestamp)}
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-slate-950/70">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white"><TrendingUp className="h-5 w-5 text-emerald-300" /> Breadth</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                <div className="text-sm text-slate-400">Bullish</div>
                <div className="mt-1 text-3xl font-bold text-emerald-300">{marketSummary?.bullish_count ?? 0}</div>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                <div className="text-sm text-slate-400">Bearish</div>
                <div className="mt-1 text-3xl font-bold text-red-300">{marketSummary?.bearish_count ?? 0}</div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-slate-950/70">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white"><Radar className="h-5 w-5 text-amber-300" /> Right Now</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {topSignals.slice(0, 3).map((signal) => (
                <div key={`${signal.symbol}-${signal.strategy}`} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-semibold text-white">{signal.symbol}</div>
                    <Badge className={signal.signal === 'bullish' ? 'bg-emerald-500/20 text-emerald-300' : signal.signal === 'bearish' ? 'bg-red-500/20 text-red-300' : 'bg-amber-500/20 text-amber-200'}>
                      {signal.analysis_summary?.rating || 'Watch'}
                    </Badge>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-300">{signal.analysis_summary?.why_now || signal.reasons[0]}</p>
                </div>
              ))}
              {topSignals.length === 0 && (
                <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-400">
                  No action-ready setups are ranked yet for this market.
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader>
            <CardTitle className="flex items-center justify-between gap-3 text-white">
              <span>Top ranked setups</span>
              <Badge variant="outline" className="border-slate-700 text-slate-300">{topSignals.length} visible</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {topSignals.length === 0 ? (
              <div className="py-12 text-center text-slate-400">
                <Activity className="mx-auto mb-4 h-12 w-12 text-slate-700" />
                No high-conviction setups found right now for {market}.
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
                {topSignals.map((signal) => (
                  <SignalCard key={`${signal.symbol}-${signal.strategy}-${signal.timeframe}`} signal={signal} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
