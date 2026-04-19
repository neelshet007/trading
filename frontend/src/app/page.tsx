'use client';

import { useEffect, useState } from 'react';
import { Activity, Radar } from 'lucide-react';

import { Sidebar } from '@/components/Sidebar';
import { fetcher } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { SignalCard } from '@/components/SignalCard';
import { TradeCards, type SetupData } from '@/components/dashboard/TradeCards';
import { TerminalFeed } from '@/components/dashboard/TerminalFeed';
import { MTFChart } from '@/components/dashboard/MTFChart';
import { TradeDetailsModal } from '@/components/dashboard/TradeDetailsModal';
import { formatDisplayDate, formatDisplayTime, getStatusBadgeClasses, isDataPulseStale, type MarketSummary, type SegmentScanResponse } from '@/lib/market';

export default function Home() {
  const [segmentData, setSegmentData] = useState<SegmentScanResponse | null>(null);
  const [marketSummary, setMarketSummary] = useState<MarketSummary | null>(null);
  const [selectedSetup, setSelectedSetup] = useState<SetupData | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [showDetailsModal, setShowDetailsModal] = useState(false);

  const loadData = async () => {
    const [summary, segment] = await Promise.all([
      fetcher('/market-summary?market=CRYPTO'),
      fetcher('/scan/crypto'),
    ]);
    if (summary) setMarketSummary(summary as MarketSummary);
    if (segment) {
      const payload = segment as SegmentScanResponse;
      setSegmentData(payload);
      setSelectedSetup((current) => {
        if (isDataPulseStale(payload.data_pulse)) return null;
        const matching = current ? payload.opportunities.find((item) => item.symbol === current.symbol) : null;
        return matching || payload.opportunities[0] || null;
      });
    }
  };

  useEffect(() => {
    void loadData();
    const interval = window.setInterval(() => {
      void loadData();
    }, 20000);
    return () => clearInterval(interval);
  }, []);

  const handleScan = async () => {
    setIsScanning(true);
    try {
      const response = await fetcher('/scan/crypto?force=true');
      if (response) {
        const payload = response as SegmentScanResponse;
        setSegmentData(payload);
        setSelectedSetup(isDataPulseStale(payload.data_pulse) ? null : payload.opportunities[0] || null);
      }
    } finally {
      setIsScanning(false);
    }
  };

  const dataPulse = segmentData?.data_pulse || marketSummary?.data_pulse;
  const isStale = isDataPulseStale(dataPulse);
  const topSignals = isStale ? [] : segmentData?.opportunities || [];
  const marketClock = marketSummary?.market_clock;

  return (
    <div className="flex h-screen overflow-hidden bg-[radial-gradient(circle_at_top,rgba(12,74,110,0.16),transparent_30%),linear-gradient(180deg,#020617_0%,#07111f_45%,#020617_100%)] text-slate-200">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mb-8 flex flex-col gap-5 border-b border-slate-800/80 pb-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <span className="rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1 text-xs font-semibold tracking-[0.3em] text-slate-300">
                CR
              </span>
              <Badge className={getStatusBadgeClasses(marketClock?.status_color)}>{marketClock?.status_text || 'Loading session'}</Badge>
            </div>
            <div>
              <h2 className="text-4xl font-bold tracking-tight text-white">Crypto-Only HITL Engine</h2>
              <p className="mt-2 max-w-3xl text-slate-400">
                HMM regime filter, IPDA range state, OTE gating, order-flow confluence, and human-reviewed inducement traps for liquid crypto.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500">Market Clock</div>
              <div className="mt-2 text-sm text-slate-200">{marketClock?.local_time || '--'} UTC</div>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500">Bias Split</div>
              <div className="mt-2 text-sm text-slate-200">{marketSummary?.bullish_count || 0} long / {marketSummary?.bearish_count || 0} short</div>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500">Last Sync</div>
              <div className="mt-2 text-sm text-slate-200">{formatDisplayTime(segmentData?.last_completed)} on {formatDisplayDate(segmentData?.last_completed)}</div>
            </div>
          </div>
        </div>

        {isStale ? (
          <div className="mb-8 rounded-2xl border border-rose-500/40 bg-rose-500/10 p-5 text-rose-100 shadow-[0_0_30px_rgba(244,63,94,0.12)]">
            <div className="text-sm font-semibold tracking-[0.18em] text-rose-300">STALE DATA: RECONNECTING</div>
            <div className="mt-2 text-sm text-rose-100/90">
              The Yahoo pulse is older than {dataPulse?.stale_after_seconds || 300} seconds, so the dashboard has cleared all entries until a fresh BTC, ETH, and SOL packet arrives.
            </div>
          </div>
        ) : null}

        <div className="mb-8 grid grid-cols-1 gap-6 xl:grid-cols-4">
          <div className="flex h-[600px] flex-col overflow-hidden rounded-xl border border-slate-800 bg-slate-950/80 shadow-[0_0_15px_rgba(0,0,0,0.4)] xl:col-span-1">
            <div className="flex items-center justify-between border-b border-slate-800/80 bg-slate-900 p-4">
              <h3 className="text-sm font-bold uppercase tracking-widest text-cyan-400">Control Panel</h3>
              <button
                onClick={handleScan}
                disabled={isScanning}
                className="flex items-center gap-2 rounded border border-cyan-500/50 bg-cyan-500/20 px-4 py-1.5 text-xs font-bold text-cyan-300 transition-all disabled:opacity-50"
              >
                {isScanning ? <Activity className="h-4 w-4 animate-spin" /> : <Radar className="h-4 w-4" />}
                {isScanning ? 'SCANNING...' : 'REFRESH'}
              </button>
            </div>
            <div className="flex-1 overflow-hidden">
              <TerminalFeed setups={topSignals} onSelectSetup={setSelectedSetup} selectedSymbol={selectedSetup?.symbol} dataPulse={dataPulse} />
            </div>
          </div>

          <div className="flex flex-col gap-6 xl:col-span-3">
            {selectedSetup ? (
              <div className="relative grid grid-cols-1 gap-6 lg:grid-cols-3">
                <div className="pointer-events-none absolute inset-0 z-0 hidden rounded-xl bg-cyan-400/5 blur-2xl lg:block" />
                <div className="relative z-10 cursor-pointer rounded-xl transition-all hover:ring-2 hover:ring-cyan-500/50 lg:col-span-1" onClick={() => setShowDetailsModal(true)}>
                  <TradeCards setup={selectedSetup} />
                </div>
                <div className="relative z-10 h-[380px] lg:col-span-2">
                  <MTFChart setup={selectedSetup} />
                </div>
              </div>
            ) : (
              <div className="flex h-[380px] items-center justify-center rounded-xl border border-dashed border-slate-800 bg-slate-900/30">
                <div className="text-center">
                  <Activity className="mx-auto mb-3 h-12 w-12 text-slate-700" />
                  <p className="font-mono text-slate-500">Terminal standby. No qualified setup.</p>
                </div>
              </div>
            )}
          </div>
        </div>

        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader>
            <CardTitle className="flex items-center justify-between gap-3 text-white">
              <span>Qualified Crypto Setups</span>
              <Badge variant="outline" className="border-slate-700 text-slate-300">{topSignals.length} visible</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {topSignals.length === 0 ? (
              <div className="py-12 text-center text-slate-400">
                <Activity className="mx-auto mb-4 h-12 w-12 text-slate-700" />
                No setups passed the HMM, sweep, and order-flow filters.
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
                {topSignals.map((signal, index) => (
                  <SignalCard key={`${signal.symbol}-${signal.trigger.entry_model}-${index}`} signal={signal} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>
      {showDetailsModal && selectedSetup && (
        <TradeDetailsModal setup={selectedSetup} onClose={() => setShowDetailsModal(false)} />
      )}
    </div>
  );
}
