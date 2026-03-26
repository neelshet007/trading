'use client';

import { useEffect, useState, useRef } from 'react';
import { Sidebar } from '@/components/Sidebar';
import { fetcher } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Target, ShieldAlert, Activity } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';

export default function StockDetailPage() {
  const params = useParams();
  const symbol = params.symbol as string;
  const [signals, setSignals] = useState<any[]>([]);
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const loadSignals = async () => {
      const data = await fetcher(`/stock/${symbol}`);
      if (data) setSignals(data);
    };
    loadSignals();
  }, [symbol]);

  useEffect(() => {
    if (!chartContainerRef.current) return;
    
    // Clean up old script if re-rendering
    chartContainerRef.current.innerHTML = '';
    
    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/tv.js';
    script.async = true;
    script.onload = () => {
      if (typeof window !== 'undefined' && (window as any).TradingView) {
        new (window as any).TradingView.widget({
          autosize: true,
          symbol: symbol,
          interval: 'D',
          timezone: 'Etc/UTC',
          theme: 'dark',
          style: '1',
          locale: 'en',
          enable_publishing: false,
          backgroundColor: '#0f172a',
          gridColor: '#1e293b',
          hide_top_toolbar: false,
          hide_legend: false,
          save_image: false,
          container_id: 'tv_chart_container',
        });
      }
    };
    chartContainerRef.current.appendChild(script);
  }, [symbol]);

  const latestSignal = signals[0];

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-200">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mb-6">
          <Link href="/" className="inline-flex items-center text-sm text-slate-400 hover:text-emerald-400 mb-4 transition-colors">
            <ArrowLeft className="w-4 h-4 mr-1" /> Back to Dashboard
          </Link>
          <h2 className="text-3xl font-bold text-white tracking-tight flex items-center gap-4">
            {symbol.toUpperCase()}
          </h2>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          <div className="xl:col-span-2 flex flex-col gap-6">
            <Card className="bg-slate-900 border-slate-800 overflow-hidden h-[500px]">
              <div id="tv_chart_container" className="h-full w-full" ref={chartContainerRef} />
            </Card>
            
            {latestSignal && (
              <Card className="bg-slate-900 border-slate-800">
                <CardHeader>
                  <CardTitle className="text-xl text-white">Latest Signal Detailed Analysis</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div>
                      <h4 className="text-slate-400 uppercase text-xs font-bold tracking-wider mb-3">Why Consider This?</h4>
                      <ul className="space-y-3">
                        {latestSignal.reasons.map((r: string, i: number) => (
                          <li key={i} className="flex items-start gap-2 text-slate-200 bg-slate-800/50 p-3 rounded-md">
                            <span className="text-emerald-500 font-bold">•</span>
                            <span>{r}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <h4 className="text-slate-400 uppercase text-xs font-bold tracking-wider mb-3">Suggested Trading Plan</h4>
                      <div className="space-y-4 bg-slate-800/30 p-5 rounded-lg border border-slate-800">
                        <div className="flex justify-between items-center border-b border-slate-800 pb-3">
                          <span className="flex items-center gap-2 text-slate-400"><Activity className="w-4 h-4"/> Entry Zone</span>
                          <span className="text-white font-mono font-bold text-lg">{latestSignal.entry_zone}</span>
                        </div>
                        <div className="flex justify-between items-center border-b border-slate-800 pb-3">
                          <span className="flex items-center gap-2 text-red-400"><ShieldAlert className="w-4 h-4"/> Stop Loss</span>
                          <span className="text-white font-mono font-bold text-lg">{latestSignal.stop_loss}</span>
                        </div>
                        <div className="flex justify-between items-center pb-1">
                          <span className="flex items-center gap-2 text-emerald-400"><Target className="w-4 h-4"/> Target Zone</span>
                          <span className="text-white font-mono font-bold text-lg">{latestSignal.target}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
          
          <div className="flex flex-col gap-6">
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader>
                <CardTitle className="text-white">Setup Summary</CardTitle>
              </CardHeader>
              <CardContent>
                {latestSignal ? (
                  <div className="flex flex-col gap-4">
                    <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-md">
                      <span className="text-slate-400">Direction</span>
                      <Badge className={latestSignal.signal === 'bullish' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}>
                        {latestSignal.signal === 'bullish' ? 'BULLISH' : 'BEARISH'}
                      </Badge>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-md">
                      <span className="text-slate-400">Strategy</span>
                      <span className="font-medium text-white">{latestSignal.strategy}</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-md">
                      <span className="text-slate-400">Timeframe</span>
                      <span className="font-medium text-white">{latestSignal.timeframe}</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-md">
                      <span className="text-slate-400">Smart Score</span>
                      <span className={`font-bold text-lg ${latestSignal.score >= 8 ? 'text-emerald-400' : 'text-slate-300'}`}>
                        {latestSignal.score}/10
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="text-slate-400">No active signals currently recorded for {symbol}.</div>
                )}
              </CardContent>
            </Card>
            
            <Card className="bg-slate-900 border-slate-800">
              <CardHeader>
                <CardTitle className="text-white">Historical Signals</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {signals.slice(1, 6).map((sig, i) => (
                   <div key={i} className="flex justify-between items-center p-3 border-b border-slate-800 last:border-0">
                     <div>
                       <div className="text-sm font-medium text-white">{sig.strategy}</div>
                       <div className="text-xs text-slate-500">{new Date(sig.timestamp).toLocaleDateString()}</div>
                     </div>
                     <Badge variant="outline" className={sig.signal === 'bullish' ? 'text-emerald-400 border-emerald-900' : 'text-red-400 border-red-900'}>
                        {sig.signal}
                      </Badge>
                   </div>
                  ))}
                  {signals.length <= 1 && <div className="text-sm text-slate-500">No historical signals.</div>}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
