'use client';

import { useEffect, useState } from 'react';
import { Activity, Clock3, TrendingUp } from 'lucide-react';

import { Sidebar } from '@/components/Sidebar';
import { fetcher } from '@/lib/api';
import { SignalCard } from '@/components/SignalCard';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatDisplayDate, formatDisplayTime, getStatusBadgeClasses, isDataPulseStale, type MarketSummary, type SegmentScanResponse } from '@/lib/market';

export default function MarketOverview() {
  const [summary, setSummary] = useState<MarketSummary | null>(null);
  const [segment, setSegment] = useState<SegmentScanResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      const [marketSummary, segmentPayload] = await Promise.all([
        fetcher('/market-summary?market=CRYPTO'),
        fetcher('/scan/crypto'),
      ]);
      setSummary((marketSummary as MarketSummary) || null);
      setSegment((segmentPayload as SegmentScanResponse) || null);
      setLoading(false);
    };
    void loadData();
  }, []);

  const dataPulse = segment?.data_pulse || summary?.data_pulse;
  const opportunities = isDataPulseStale(dataPulse) ? [] : segment?.opportunities || [];
  const leaders = opportunities.filter((item) => ['BTC-USD', 'ETH-USD', 'SOL-USD'].includes(item.symbol));

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-200">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mb-8 border-b border-slate-800 pb-6">
          <h2 className="text-3xl font-bold tracking-tight text-white">Crypto Market Overview</h2>
          <p className="mt-1 text-slate-400">
            HTF regime state, leader participation, and currently qualified crypto opportunities.
          </p>
        </div>

        <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Card className="border-slate-800 bg-slate-950/70">
            <CardHeader>
              <CardTitle className="flex items-center justify-between gap-3 text-white">
                <span>Session State</span>
                <Badge className={getStatusBadgeClasses(summary?.market_clock?.status_color)}>
                  {summary?.market_clock?.status_text || 'Loading'}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-slate-300">
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                <div className="mb-1 flex items-center gap-2 text-slate-500"><Clock3 className="h-4 w-4" /> UTC Clock</div>
                <div>{summary?.market_clock?.local_time || '--:--'} {summary?.market_clock?.local_label || ''}</div>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                Last update: {formatDisplayTime(summary?.timestamp)} on {formatDisplayDate(summary?.timestamp)}
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-slate-950/70">
            <CardHeader>
              <CardTitle className="text-white">Bias Split</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Bullish</div>
                <div className="mt-2 text-2xl font-semibold text-emerald-300">{summary?.bullish_count ?? 0}</div>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Bearish</div>
                <div className="mt-2 text-2xl font-semibold text-rose-300">{summary?.bearish_count ?? 0}</div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-slate-950/70">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white"><TrendingUp className="h-4 w-4" /> Leaderboard</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-slate-300">
              {leaders.length === 0 ? (
                <div>No core asset is qualified right now.</div>
              ) : (
                leaders.map((item) => (
                  <div key={item.symbol} className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                    <div className="font-semibold text-white">{item.symbol}</div>
                    <div className="text-slate-400">{item.context.hmm_regime}</div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        {isDataPulseStale(dataPulse) ? (
          <div className="mb-8 rounded-2xl border border-rose-500/40 bg-rose-500/10 p-5 text-rose-100">
            <div className="text-sm font-semibold tracking-[0.18em] text-rose-300">STALE DATA: RECONNECTING</div>
            <div className="mt-2 text-sm text-rose-100/90">
              The overview is intentionally blank until BTC, ETH, and SOL all return a fresh packet inside the 300-second tolerance.
            </div>
          </div>
        ) : null}

        {loading ? (
          <div className="py-8 text-slate-400">Fetching crypto overview...</div>
        ) : opportunities.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/50 py-12 text-center">
            <Activity className="mx-auto mb-4 h-10 w-10 text-slate-700" />
            <div className="mb-2 text-lg text-white">No setups generated yet.</div>
            <div className="text-slate-400">The engine is filtering out low-quality conditions until regime and sweep alignment returns.</div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
            {opportunities.map((signal, index) => (
              <SignalCard key={`${signal.symbol}-${signal.trigger.entry_model}-${index}`} signal={signal} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
