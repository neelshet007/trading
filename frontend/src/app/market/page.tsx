'use client';

import { useEffect, useState } from 'react';
import { Activity, Clock3, TrendingUp } from 'lucide-react';

import { Sidebar } from '@/components/Sidebar';
import { useStore } from '@/store/useStore';
import { fetcher } from '@/lib/api';
import { SignalCard } from '@/components/SignalCard';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  formatDisplayDate,
  formatDisplayTime,
  getStatusBadgeClasses,
  type MarketKey,
  type MarketSummary,
  type Signal,
} from '@/lib/market';

const MARKET_ORDER: MarketKey[] = ['USA', 'INDIA', 'CRYPTO', 'COMMODITIES'];

interface MarketBoardData {
  summary: MarketSummary | null;
  signals: Signal[];
}

export default function MarketOverview() {
  const { market, timeframe, setMarket } = useStore();
  const [marketBoards, setMarketBoards] = useState<Record<MarketKey, MarketBoardData>>({
    USA: { summary: null, signals: [] },
    INDIA: { summary: null, signals: [] },
    CRYPTO: { summary: null, signals: [] },
    COMMODITIES: { summary: null, signals: [] },
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      const responses = await Promise.all(
        MARKET_ORDER.map(async (marketKey) => {
          const [summary, signals] = await Promise.all([
            fetcher(`/market-summary?market=${marketKey}`),
            fetcher(`/signals?market=${marketKey}&timeframe=${timeframe}`),
          ]);
          return [marketKey, { summary: (summary as MarketSummary) || null, signals: (signals as Signal[]) || [] }] as const;
        })
      );

      setMarketBoards(Object.fromEntries(responses) as Record<MarketKey, MarketBoardData>);
      setLoading(false);
    };

    const initialLoad = window.setTimeout(() => {
      void loadData();
    }, 0);

    return () => clearTimeout(initialLoad);
  }, [timeframe]);

  const selectedSignals = marketBoards[market]?.signals || [];

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-200">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mb-8 border-b border-slate-800 pb-6">
          <h2 className="text-3xl font-bold tracking-tight text-white">Global Market Overview</h2>
          <p className="mt-1 text-slate-400">
            India market overview, crypto market overview, commodities market overview, and the selected market all in one place.
          </p>
        </div>

        <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-2 2xl:grid-cols-4">
          {MARKET_ORDER.map((marketKey) => {
            const board = marketBoards[marketKey];
            const summary = board.summary;
            const topSignal = board.signals[0];

            return (
              <Card
                key={marketKey}
                className={`cursor-pointer border transition-colors ${market === marketKey ? 'border-emerald-500/50 bg-slate-900' : 'border-slate-800 bg-slate-950/70 hover:border-slate-700'}`}
                onClick={() => setMarket(marketKey)}
              >
                <CardHeader>
                  <CardTitle className="flex items-center justify-between gap-3 text-white">
                    <span>{marketKey}</span>
                    <Badge className={getStatusBadgeClasses(summary?.market_clock?.status_color)}>
                      {summary?.market_clock?.status_text || 'Loading'}
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                      <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Bullish</div>
                      <div className="mt-2 text-2xl font-semibold text-emerald-300">{summary?.bullish_count ?? 0}</div>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                      <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Bearish</div>
                      <div className="mt-2 text-2xl font-semibold text-red-300">{summary?.bearish_count ?? 0}</div>
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-sm text-slate-300">
                    <div className="mb-1 flex items-center gap-2 text-slate-500"><Clock3 className="h-4 w-4" /> Clock</div>
                    <div>India: {summary?.market_clock?.india_time || '--:--'} IST</div>
                    {marketKey !== 'INDIA' && <div>{marketKey}: {summary?.market_clock?.local_time || '--:--'} {summary?.market_clock?.local_label || ''}</div>}
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                    <div className="mb-1 flex items-center gap-2 text-sm text-slate-500"><TrendingUp className="h-4 w-4" /> Why now</div>
                    <p className="text-sm leading-6 text-slate-300">
                      {topSignal?.analysis_summary?.why_now || `No strong ${marketKey.toLowerCase()} catalyst is ranked yet.`}
                    </p>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <h3 className="text-2xl font-semibold text-white">{market} Detailed Overview</h3>
            <p className="mt-1 text-slate-400">
              Showing all currently active {timeframe} signals for {market}.
            </p>
          </div>
          <Badge variant="outline" className="border-slate-700 text-slate-300">
            {selectedSignals.length} ranked setups
          </Badge>
        </div>

        {loading ? (
          <div className="py-8 text-slate-400">Fetching market boards and ranked setups...</div>
        ) : (
          <>
            <div className="mb-6 rounded-2xl border border-slate-800 bg-slate-900/50 p-5 text-sm text-slate-400">
              Last update: {formatDisplayTime(marketBoards[market]?.summary?.timestamp)} IST on {formatDisplayDate(marketBoards[market]?.summary?.timestamp)}
            </div>

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
              {selectedSignals.map((signal) => (
                <SignalCard key={`${signal.symbol}-${signal.strategy}-${signal.timestamp}`} signal={signal} />
              ))}

              {selectedSignals.length === 0 && (
                <div className="col-span-full rounded-xl border border-dashed border-slate-800 bg-slate-900/50 py-12 text-center">
                  <Activity className="mx-auto mb-4 h-10 w-10 text-slate-700" />
                  <div className="mb-2 text-lg text-white">No signals generated yet.</div>
                  <div className="text-slate-400">
                    The engine may still be warming up, or no strong setups were found for {market} in the current market conditions.
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
