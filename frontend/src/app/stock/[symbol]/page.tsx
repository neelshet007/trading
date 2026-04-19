'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, Layers, Radar, Search, Zap } from 'lucide-react';

import { Sidebar } from '@/components/Sidebar';
import { buildApiUrl } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { get_tv_symbol, type ForensicReport } from '@/lib/market';
import { PositionCalculator } from '@/components/dashboard/PositionCalculator';

type TradingViewWindow = Window & {
  TradingView?: {
    widget: new (config: Record<string, unknown>) => unknown;
  };
};

export default function StockDetailPage() {
  const params = useParams();
  const symbol = params.symbol as string;
  const [forensicData, setForensicData] = useState<ForensicReport | null>(null);
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const tvSymbol = get_tv_symbol(symbol);

  useEffect(() => {
    const loadForensicData = async () => {
      try {
        const response = await fetch(buildApiUrl(`/scan/crypto/forensic/${symbol}`));
        if (response.ok) {
          const data: ForensicReport = await response.json();
          setForensicData(data);
        }
      } catch (err) {
        console.error('Forensic scan failed', err);
      }
    };
    void loadForensicData();
  }, [symbol]);

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
          interval: '15',
          timezone: 'Etc/UTC',
          theme: 'dark',
          style: '1',
          locale: 'en',
          enable_publishing: false,
          backgroundColor: '#020617',
          gridColor: '#172033',
          save_image: false,
          container_id: 'tv_chart_container',
        });
      }
    };
    chartContainerRef.current.appendChild(script);
  }, [tvSymbol]);

  return (
    <div className="flex h-screen overflow-hidden bg-[radial-gradient(circle_at_top,rgba(8,145,178,0.15),transparent_30%),linear-gradient(180deg,#020617_0%,#07111f_45%,#020617_100%)] text-slate-200">
      <Sidebar />
      <main className="flex-1 overflow-y-auto border-l border-slate-800 p-8">
        <div className="mb-6 flex items-end justify-between">
          <div>
            <Link href="/markets/crypto" className="mb-4 inline-flex items-center text-sm text-slate-400 transition-colors hover:text-cyan-300">
              <ArrowLeft className="mr-1 h-4 w-4" /> Back to Terminal
            </Link>
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-4xl font-bold tracking-tight text-white">{symbol.toUpperCase()}</h2>
              <Badge className="border border-cyan-500/30 bg-cyan-500/20 font-bold tracking-widest text-cyan-300 hover:bg-cyan-500/20">
                FORENSIC ANALYSIS MODE
              </Badge>
            </div>
          </div>
        </div>

        <div className="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
          <div className="relative h-[450px] xl:col-span-2">
            <Card className="h-full w-full overflow-hidden border-slate-800 bg-slate-950/70">
              <div id="tv_chart_container" className="h-full w-full" ref={chartContainerRef} />
            </Card>
          </div>
          <div className="h-[450px] xl:col-span-1">
            {forensicData ? (
              <PositionCalculator
                entryPrice={forensicData.entry}
                stopLoss={forensicData.stop_loss}
                maxAllocation={forensicData.risk.max_equity_allocation}
              />
            ) : (
              <Card className="flex h-full items-center justify-center border-slate-800 bg-slate-950/70">
                <span className="text-sm font-semibold tracking-widest text-slate-500">CALCULATING RISK PARAMS...</span>
              </Card>
            )}
          </div>
        </div>

        {forensicData && (
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
            <div className="xl:col-span-1">
              <Card className="h-full border-slate-800 bg-slate-950/70">
                <CardHeader className="border-b border-slate-800 pb-3">
                  <CardTitle className="flex items-center gap-2 text-sm font-semibold tracking-widest text-white">
                    <Layers className="h-4 w-4 text-cyan-400" /> Context & Checklist
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 pt-4 text-sm text-slate-300">
                  <div className="rounded border border-slate-800 bg-slate-900/50 p-3">{forensicData.context.hmm_regime}</div>
                  <div className="rounded border border-slate-800 bg-slate-900/50 p-3">{forensicData.context.ipda_cycle}</div>
                  <div className="rounded border border-slate-800 bg-slate-900/50 p-3">Liquidity swept: {forensicData.checklist.liquidity_swept ? 'Yes' : 'No'}</div>
                  <div className="rounded border border-slate-800 bg-slate-900/50 p-3">CVD supportive: {forensicData.checklist.cvd_supportive ? 'Yes' : 'No'}</div>
                  <div className="rounded border border-slate-800 bg-slate-900/50 p-3">OTE respected: {forensicData.checklist.in_ote_zone ? 'Yes' : 'No'}</div>
                </CardContent>
              </Card>
            </div>

            <div className="xl:col-span-1">
              <Card className="relative h-full overflow-hidden border-slate-800 bg-slate-950/70">
                <div className="absolute -bottom-5 -right-5 opacity-5"><Search className="h-48 w-48" /></div>
                <CardHeader className="relative z-10 border-b border-slate-800 pb-3">
                  <CardTitle className="flex items-center gap-2 text-sm font-semibold tracking-widest text-white">
                    <Radar className="h-4 w-4 text-rose-400" /> Trigger & Footprint
                  </CardTitle>
                </CardHeader>
                <CardContent className="relative z-10 space-y-5 pt-5">
                  <div className="rounded border border-slate-800 bg-slate-900/50 p-3 text-sm text-slate-300">
                    {forensicData.catalyst}
                  </div>
                  <div className="rounded border border-slate-800 bg-slate-900/50 p-3 text-sm text-slate-300">
                    {forensicData.formation}
                  </div>
                  <div className="rounded border border-cyan-500/20 bg-cyan-900/20 p-3 text-sm leading-relaxed text-cyan-200">
                    <div className="mb-1 flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest text-cyan-400">
                      <Zap className="h-3 w-3" /> Verification Step
                    </div>
                    {forensicData.instruction}
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="xl:col-span-1">
              <Card className="h-full border-amber-500/20 bg-amber-500/5">
                <CardHeader className="border-b border-amber-500/20 pb-3">
                  <CardTitle className="text-sm font-semibold tracking-widest text-amber-400">Risk & HITL</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-5 pt-5">
                  <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-4">
                    <div className="mb-2 text-[10px] font-bold uppercase tracking-widest text-amber-400">Derivative Stats</div>
                    <div className="text-lg font-semibold text-amber-100">{forensicData.derivative_stats.liquidation_bias}</div>
                    <div className="mt-2 text-sm text-amber-200">Funding clamp: {forensicData.derivative_stats.funding_rate_clamp_bps.toFixed(2)} bps</div>
                    <div className="text-sm text-amber-200">CVD: {forensicData.derivative_stats.cvd_divergence}</div>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                    <div className="mb-1 text-[10px] font-bold uppercase tracking-widest text-slate-500">Risk Envelope</div>
                    <div className="text-sm text-slate-300">VaR95: {forensicData.risk.var_95.toFixed(2)}</div>
                    <div className="text-sm text-slate-300">Slippage: {forensicData.risk.expected_slippage_bps.toFixed(2)} bps</div>
                    <div className="text-sm text-slate-300">Expectancy: {forensicData.risk.expectancy.toFixed(2)}R</div>
                  </div>
                  <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 p-4">
                    <div className="mb-2 text-[10px] font-bold uppercase tracking-widest text-rose-300">Inducement Traps</div>
                    {forensicData.hitl.inducement_traps.map((trap, idx) => (
                      <div key={idx} className="mb-2 text-sm text-slate-300 last:mb-0">
                        {trap}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
