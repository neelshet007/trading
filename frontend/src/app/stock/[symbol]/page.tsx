'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, Clock3, Radar, ShieldAlert, Target, TrendingUp } from 'lucide-react';

import { Sidebar } from '@/components/Sidebar';
import { fetcher } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  formatDisplayDate,
  formatDisplayTime,
  get_tv_symbol,
  getSignalClasses,
  getStatusBadgeClasses,
  type MarketClock,
  type Signal,
} from '@/lib/market';

type TradingViewWindow = Window & {
  TradingView?: {
    widget: new (config: Record<string, unknown>) => unknown;
  };
};

export default function StockDetailPage() {
  const params = useParams();
  const symbol = params.symbol as string;
  const [signals, setSignals] = useState<Signal[]>([]);
  const [marketClock, setMarketClock] = useState<MarketClock | null>(null);
  const chartContainerRef = useRef<HTMLDivElement>(null);

  const latestSignal = signals[0];
  const market = latestSignal?.market || (symbol.toUpperCase().endsWith('.NS') ? 'INDIA' : 'USA');
  const tvSymbol = get_tv_symbol(symbol);

  useEffect(() => {
    const loadSignals = async () => {
      const data = await fetcher(`/stock/${symbol}?market=${market}`);
      if (data) setSignals(data as Signal[]);
    };
    loadSignals();
  }, [symbol, market]);

  useEffect(() => {
    const loadClock = async () => {
      const data = await fetcher(`/market-clock?market=${market}`);
      if (data) setMarketClock(data as MarketClock);
    };
    loadClock();
  }, [market]);

  useEffect(() => {
    if (!chartContainerRef.current) return;
    chartContainerRef.current.innerHTML = '';

    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/tv.js';
    script.async = true;
    script.onload = () => {
      const tradingViewWindow = window as TradingViewWindow;
      if (tradingViewWindow.TradingView) {
        new tradingViewWindow.TradingView.widget({
          autosize: true,
          symbol: tvSymbol,
          interval: 'D',
          timezone: market === 'INDIA' ? 'Asia/Kolkata' : market === 'USA' ? 'America/New_York' : 'Etc/UTC',
          theme: 'dark',
          style: '1',
          locale: 'en',
          enable_publishing: false,
          backgroundColor: '#020617',
          gridColor: '#172033',
          hide_top_toolbar: false,
          hide_legend: false,
          save_image: false,
          container_id: 'tv_chart_container',
        });
      }
    };
    chartContainerRef.current.appendChild(script);
  }, [tvSymbol, market]);

  const patternDescriptions = useMemo(() => {
    if (!latestSignal?.pattern_details) return [];
    return latestSignal.pattern_details.map((pattern) => ({
      title: `${pattern.name} ${pattern.strength >= 8 ? '(Strong)' : '(Developing)'}`,
      description: pattern.description,
    }));
  }, [latestSignal]);

  return (
    <div className="flex h-screen overflow-hidden bg-[radial-gradient(circle_at_top,rgba(30,64,175,0.12),transparent_30%),linear-gradient(180deg,#020617_0%,#07111f_45%,#020617_100%)] text-slate-200">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mb-6">
          <Link href="/" className="mb-4 inline-flex items-center text-sm text-slate-400 transition-colors hover:text-emerald-300">
            <ArrowLeft className="mr-1 h-4 w-4" /> Back to Dashboard
          </Link>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-4xl font-bold tracking-tight text-white">{symbol.toUpperCase()}</h2>
            {latestSignal && <Badge className={getSignalClasses(latestSignal.signal)}>{latestSignal.signal}</Badge>}
            {marketClock && <Badge className={getStatusBadgeClasses(marketClock.status_color)}>{marketClock.status_text}</Badge>}
          </div>
          <p className="mt-2 max-w-3xl text-slate-400">
            Beginner-friendly analysis with live market context, pattern detection, and a direct answer to why this stock matters right now.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-8 xl:grid-cols-3">
          <div className="flex flex-col gap-6 xl:col-span-2">
            <Card className="h-[520px] overflow-hidden border-slate-800 bg-slate-950/70">
              <div id="tv_chart_container" className="h-full w-full" ref={chartContainerRef} />
            </Card>

            <Card className="border-slate-800 bg-slate-950/70">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white"><Radar className="h-5 w-5 text-amber-300" /> Why Is This Important Right Now?</CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 text-slate-100">
                  {latestSignal?.analysis_summary?.explanation || 'No fresh analysis summary is available for this symbol yet.'}
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
                    <div className="mb-3 text-xs uppercase tracking-[0.2em] text-slate-500">Detected patterns</div>
                    <div className="space-y-3">
                      {patternDescriptions.length > 0 ? patternDescriptions.map((pattern) => (
                        <div key={pattern.title} className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                          <div className="font-medium text-white">{pattern.title}</div>
                          <p className="mt-1 text-sm leading-6 text-slate-300">{pattern.description}</p>
                        </div>
                      )) : (
                        <div className="text-sm text-slate-400">No advanced price pattern was confirmed on the latest scan.</div>
                      )}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
                    <div className="mb-3 text-xs uppercase tracking-[0.2em] text-slate-500">Simple readout</div>
                    <div className="space-y-3">
                      <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                        <div className="text-sm text-slate-400">Breakout probability</div>
                        <div className="mt-1 text-xl font-semibold text-white">{latestSignal?.probability?.breakout || 'Unknown'}</div>
                      </div>
                      <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                        <div className="text-sm text-slate-400">Trend continuation</div>
                        <div className="mt-1 text-xl font-semibold text-white">{latestSignal?.probability?.trend_continuation || 'Unknown'}</div>
                      </div>
                      <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                        <div className="text-sm text-slate-400">Plain-language takeaway</div>
                        <p className="mt-1 text-sm leading-6 text-slate-300">{latestSignal?.analysis_summary?.why_now || 'The setup is still forming, so patience is better than chasing.'}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="flex flex-col gap-6">
            <Card className="border-slate-800 bg-slate-950/70">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white"><Clock3 className="h-5 w-5 text-cyan-300" /> Market Status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {marketClock && (
                  <>
                    <Badge className={getStatusBadgeClasses(marketClock.status_color)}>{marketClock.status_text}</Badge>
                    <div className={`grid gap-3 ${market === 'USA' ? 'grid-cols-2' : 'grid-cols-1'}`}>
                      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                        <div className="text-xs uppercase tracking-[0.2em] text-slate-500">India Time</div>
                        <div className="mt-2 text-2xl font-semibold text-white">{marketClock.india_time}</div>
                        <div className="text-sm text-slate-400">IST</div>
                      </div>
                      {market === 'USA' && (
                        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                          <div className="text-xs uppercase tracking-[0.2em] text-slate-500">US Time</div>
                          <div className="mt-2 text-2xl font-semibold text-white">{marketClock.local_time}</div>
                          <div className="text-sm text-slate-400">{marketClock.local_label}</div>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            <Card className="border-slate-800 bg-slate-950/70">
              <CardHeader>
                <CardTitle className="text-white">Setup Summary</CardTitle>
              </CardHeader>
              <CardContent>
                {latestSignal ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                      <span className="text-slate-400">Direction</span>
                      <Badge className={getSignalClasses(latestSignal.signal)}>{latestSignal.signal}</Badge>
                    </div>
                    <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                      <span className="text-slate-400">Rating</span>
                      <span className="font-semibold text-white">{latestSignal.analysis_summary?.rating || 'Watch'}</span>
                    </div>
                    <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                      <span className="text-slate-400">Scanner categories</span>
                      <span className="font-semibold text-white">{latestSignal.categories.join(', ') || 'None'}</span>
                    </div>
                    <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                      <span className="text-slate-400">Breakout level</span>
                      <span className="font-semibold text-white">{latestSignal.breakout_level ?? '--'}</span>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                      <div className="mb-2 text-sm text-slate-400">Trading plan</div>
                      <div className="space-y-3">
                        <div className="flex items-center justify-between text-sm text-slate-300"><span className="flex items-center gap-2"><TrendingUp className="h-4 w-4 text-slate-500" /> Entry</span><span className="font-semibold text-white">{latestSignal.entry_zone ?? '--'}</span></div>
                        <div className="flex items-center justify-between text-sm text-slate-300"><span className="flex items-center gap-2"><ShieldAlert className="h-4 w-4 text-slate-500" /> Stop loss</span><span className="font-semibold text-white">{latestSignal.stop_loss ?? '--'}</span></div>
                        <div className="flex items-center justify-between text-sm text-slate-300"><span className="flex items-center gap-2"><Target className="h-4 w-4 text-slate-500" /> Target</span><span className="font-semibold text-white">{latestSignal.target ?? '--'}</span></div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-slate-400">No active signals currently recorded for {symbol}.</div>
                )}
              </CardContent>
            </Card>

            <Card className="border-slate-800 bg-slate-950/70">
              <CardHeader>
                <CardTitle className="text-white">Recent Analysis</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {signals.map((signal) => (
                  <div key={`${signal.strategy}-${signal.timestamp}`} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                    <div className="flex items-center justify-between gap-2">
                      <div className="font-medium text-white">{signal.strategy}</div>
                      <Badge className={getSignalClasses(signal.signal)}>{signal.signal}</Badge>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-300">{signal.analysis_summary?.why_now || signal.reasons[0]}</p>
                    <div className="mt-3 text-xs text-slate-500">
                      {formatDisplayDate(signal.timestamp)} • {formatDisplayTime(signal.timestamp)} IST
                    </div>
                  </div>
                ))}
                {signals.length === 0 && <div className="text-sm text-slate-500">No historical analysis available.</div>}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
