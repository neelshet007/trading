'use client';

import { useEffect, useState } from 'react';
import { Sidebar } from '@/components/Sidebar';
import { useStore } from '@/store/useStore';
import { fetcher } from '@/lib/api';
import { SignalCard } from '@/components/SignalCard';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

const STRATEGIES = [
  "Trend Continuation",
  "Pullback Setup",
  "Breakout Scanner",
  "Reversal",
  "High Confluence"
];

export default function StrategiesPage() {
  const { timeframe } = useStore();
  const [signals, setSignals] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadSignals = async () => {
      setLoading(true);
      const data = await fetcher(`/signals?timeframe=${timeframe}`);
      if (data) setSignals(data);
      setLoading(false);
    };
    loadSignals();
  }, [timeframe]);

  const renderSignalsForStrategy = (strategy: string) => {
    const filtered = signals.filter(s => s.strategy === strategy);
    if (loading) return <div className="text-slate-400 py-8">Scanning for {strategy} setups...</div>;
    if (filtered.length === 0) return <div className="text-slate-400 py-8">No setups found for {strategy} in the current timeframe.</div>;
    
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
        {filtered.map((sig, i) => (
          <SignalCard key={i} signal={sig} />
        ))}
      </div>
    );
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-200">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-white tracking-tight">Strategy Scanner</h2>
          <p className="text-slate-400 mt-1">Filtering patterns for {timeframe} mode.</p>
        </div>

        <Tabs defaultValue="Trend Continuation" className="w-full">
          <TabsList className="bg-slate-900 border-slate-800 flex overflow-x-auto justify-start p-1 h-12">
            {STRATEGIES.map(st => (
              <TabsTrigger 
                key={st} 
                value={st}
                className="data-[state=active]:bg-emerald-600 data-[state=active]:text-white text-slate-400 px-6"
              >
                {st}
              </TabsTrigger>
            ))}
          </TabsList>
          
          {STRATEGIES.map(st => (
            <TabsContent key={st} value={st} className="mt-6">
              <div className="bg-slate-900/50 p-6 rounded-lg border border-slate-800 mb-6">
                <h3 className="text-lg font-semibold text-white mb-2">{st} Logic</h3>
                <p className="text-sm text-slate-400">
                  {st === 'Trend Continuation' && "Looks for stocks moving strongly in a primary direction, resting above key moving averages (EMA/VWAP) and forming higher highs/lows."}
                  {st === 'Pullback Setup' && "Identifies stocks in an established trend that are experiencing a short-term correction to dynamic support (like a 20 EMA) with cooling RSI."}
                  {st === 'Breakout Scanner' && "Scans for sudden price movements breaking above/below recent tightly consolidated ranges, accompanied by a surge in trading volume."}
                  {st === 'Reversal' && "Detects exhausted moves where RSI reaches extreme oversold/overbought levels, and the immediate price structure begins to shift."}
                  {st === 'High Confluence' && "Filters out noise. Only shows setups where multiple strategies trigger simultaneously for robust confirmation."}
                </p>
              </div>
              
              {renderSignalsForStrategy(st)}
            </TabsContent>
          ))}
        </Tabs>
      </main>
    </div>
  );
}
