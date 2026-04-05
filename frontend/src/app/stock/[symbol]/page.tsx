'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, Clock3, Radar, ShieldAlert, Target, Search, CheckSquare, Square, Layers, Option, Zap } from 'lucide-react';

import { Sidebar } from '@/components/Sidebar';
import { fetcher } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { get_tv_symbol } from '@/lib/market';
import { PositionCalculator } from '@/components/dashboard/PositionCalculator';

type TradingViewWindow = Window & {
  TradingView?: {
    widget: new (config: Record<string, unknown>) => unknown;
  };
};

export default function StockDetailPage() {
  const params = useParams();
  const symbol = params.symbol as string;
  const [forensicData, setForensicData] = useState<any>(null);
  const chartContainerRef = useRef<HTMLDivElement>(null);

  const market = symbol.toUpperCase().endsWith('.NS') ? 'INDIA' : 'USA';
  const tvSymbol = get_tv_symbol(symbol);

  // Fetch Intensive Forensic Data
  useEffect(() => {
    const loadForensicData = async () => {
      try {
        const response = await fetch(`http://localhost:8000/scan/forensic/${symbol}?market=${market}`);
        if (response.ok) {
           const data = await response.json();
           setForensicData(data);
        }
      } catch (err) {
        console.error("Forensic scan failed", err);
      }
    };
    loadForensicData();
  }, [symbol, market]);

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

  const CheckItem = ({ label, checked }: { label: string, checked: boolean }) => (
      <div className={`flex items-center gap-3 p-3 rounded border ${checked ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-slate-900/50 border-slate-800'}`}>
          {checked ? <CheckSquare className="h-5 w-5 text-emerald-400" /> : <Square className="h-5 w-5 text-slate-600" />}
          <span className={`text-sm font-medium ${checked ? 'text-emerald-100' : 'text-slate-400'}`}>{label}</span>
      </div>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-[radial-gradient(circle_at_top,rgba(30,64,175,0.12),transparent_30%),linear-gradient(180deg,#020617_0%,#07111f_45%,#020617_100%)] text-slate-200">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8 border-l border-slate-800">
        
        <div className="mb-6 flex justify-between items-end">
           <div>
              <Link href="/" className="mb-4 inline-flex items-center text-sm text-slate-400 transition-colors hover:text-emerald-300">
                <ArrowLeft className="mr-1 h-4 w-4" /> Back to Terminal
              </Link>
              <div className="flex flex-wrap items-center gap-3">
                <h2 className="text-4xl font-bold tracking-tight text-white">{symbol.toUpperCase()}</h2>
                <Badge className="bg-rose-500/20 text-rose-400 border border-rose-500/30 font-bold tracking-widest hover:bg-rose-500/20">FORENSIC ANALYSIS MODE</Badge>
              </div>
           </div>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3 mb-6">
           <div className="xl:col-span-2 relative h-[450px]">
             {/* TV Chart */}
             <Card className="h-full w-full overflow-hidden border-slate-800 bg-slate-950/70 shadow-[0_0_20px_rgba(0,0,0,0.5)]">
               <div id="tv_chart_container" className="h-full w-full" ref={chartContainerRef} />
             </Card>
           </div>
           
           <div className="xl:col-span-1 h-[450px]">
               {forensicData ? (
                   <PositionCalculator entryPrice={forensicData.entry} stopLoss={forensicData.stop_loss} />
               ) : (
                   <Card className="h-full border-slate-800 bg-slate-950/70 flex items-center justify-center animate-pulse">
                      <span className="text-slate-500 font-semibold tracking-widest text-sm">CALCULATING RISK PARAMS...</span>
                   </Card>
               )}
           </div>
        </div>

        {forensicData && (
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
                
                {/* Checklist */}
                <div className="xl:col-span-1">
                    <Card className="border-slate-800 bg-slate-950/70 h-full">
                      <CardHeader className="border-b border-slate-800 pb-3">
                          <CardTitle className="text-sm font-semibold tracking-widest text-white flex items-center gap-2">
                             <Layers className="h-4 w-4 text-cyan-400" /> Actionable Checklist
                          </CardTitle>
                      </CardHeader>
                      <CardContent className="pt-4 space-y-3">
                          <CheckItem label="HTF Trend Aligned?" checked={forensicData.checklist.htf_aligned} />
                          <CheckItem label="Liquidity Pools Swept?" checked={forensicData.checklist.liquidity_swept} />
                          <CheckItem label="Unmitigated FVG Created?" checked={forensicData.checklist.fvg_created} />
                          <CheckItem label="Price in Deep Discount?" checked={forensicData.checklist.in_discount} />
                      </CardContent>
                    </Card>
                </div>

                {/* Narrative Summary */}
                <div className="xl:col-span-1">
                    <Card className="border-slate-800 bg-slate-950/70 h-full relative overflow-hidden">
                      <div className="absolute opacity-5 -right-5 -bottom-5"><Search className="w-48 h-48" /></div>
                      <CardHeader className="border-b border-slate-800 pb-3 relative z-10">
                          <CardTitle className="text-sm font-semibold tracking-widest text-white flex items-center gap-2">
                             <Radar className="h-4 w-4 text-rose-400" /> Forensic "Why & Where"
                          </CardTitle>
                      </CardHeader>
                      <CardContent className="pt-5 space-y-5 relative z-10">
                          <div>
                              <div className="text-[10px] uppercase text-slate-500 font-bold mb-1 tracking-widest">The Narrative Engine</div>
                              <div className="text-sm text-slate-300 bg-slate-900/50 p-3 rounded border border-slate-800 leading-relaxed italic border-l-2 border-l-rose-500">
                                  "{forensicData.catalyst}"
                              </div>
                          </div>
                          <div>
                              <div className="text-[10px] uppercase text-slate-500 font-bold mb-1 tracking-widest">Structural Location</div>
                              <div className="text-sm text-slate-300 bg-slate-900/50 p-3 rounded border border-slate-800 leading-relaxed">
                                  {forensicData.formation}
                              </div>
                          </div>
                          <div>
                              <div className="text-[10px] uppercase text-cyan-500 font-bold mb-1 tracking-widest flex items-center gap-1"><Zap className="h-3 w-3"/> Verification Step</div>
                              <div className="text-sm text-cyan-200 bg-cyan-900/20 p-3 rounded border border-cyan-500/20 leading-relaxed">
                                  {forensicData.instruction}
                              </div>
                          </div>
                      </CardContent>
                    </Card>
                </div>

                {/* Open Interest Overlay */}
                <div className="xl:col-span-1">
                    <Card className="border-amber-500/20 bg-[#f59e0b]/5 h-full relative overflow-hidden">
                      <CardHeader className="border-b border-amber-500/20 pb-3">
                          <CardTitle className="text-sm font-semibold tracking-widest text-amber-500 flex items-center gap-2">
                             Activity Overlay
                          </CardTitle>
                      </CardHeader>
                      <CardContent className="pt-5 flex flex-col gap-5">
                          <div className="bg-amber-500/10 border border-amber-500/20 p-4 rounded-xl relative">
                              <div className="text-[10px] uppercase text-amber-400 font-bold mb-2 tracking-widest">Derivative OI Analysis</div>
                              <div className="text-lg text-amber-100 font-semibold">{forensicData.derivative_stats.oi_interpretation}</div>
                              <div className="text-xs text-amber-500/80 mt-2">*Simulated via Vol/Price proxy algorithm.</div>
                          </div>

                          <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex items-center justify-between">
                              <div>
                                  <div className="text-[10px] uppercase text-slate-500 font-bold mb-1 tracking-widest">Max Pain Proxy</div>
                                  <div className="text-3xl font-bold text-slate-200">₹ {forensicData.derivative_stats.max_pain_proxy.toLocaleString()}</div>
                              </div>
                              <Target className="h-10 w-10 text-slate-700" />
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
