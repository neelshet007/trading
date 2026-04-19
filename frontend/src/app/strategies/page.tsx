'use client';

import { useEffect, useState } from 'react';

import { Sidebar } from '@/components/Sidebar';
import { fetcher } from '@/lib/api';
import { SignalCard } from '@/components/SignalCard';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { SegmentScanResponse, SetupSignal } from '@/lib/market';

const CATEGORIES = [
  'Unicorn Model (Breaker + FVG)',
  'Silver Bullet Session Sweep',
  'OTE Retracement Tap',
  'Turtle Soup',
];

export default function StrategiesPage() {
  const [signals, setSignals] = useState<SetupSignal[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadSignals = async () => {
      setLoading(true);
      const data = await fetcher('/scan/crypto');
      const opportunities = ((data as SegmentScanResponse) || { opportunities: [] }).opportunities || [];
      setSignals(opportunities);
      setLoading(false);
    };
    void loadSignals();
  }, []);

  const renderSignalsForCategory = (category: string) => {
    const filtered = signals.filter((signal) => signal.trigger.entry_model === category);
    if (loading) return <div className="py-8 text-slate-400">Scanning crypto for {category} setups...</div>;
    if (filtered.length === 0) {
      return <div className="rounded-lg border border-dashed border-slate-800 py-8 text-center text-slate-400">No qualified setups found for {category}.</div>;
    }
    return (
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {filtered.map((signal, index) => (
          <SignalCard key={`${signal.symbol}-${signal.trigger.entry_model}-${index}`} signal={signal} />
        ))}
      </div>
    );
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-200">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold tracking-tight text-white">Execution Models</h2>
          <p className="mt-1 text-slate-400">Grouped by trigger logic so we can compare like-for-like crypto setups.</p>
        </div>

        <Tabs defaultValue={CATEGORIES[0]} className="w-full">
          <TabsList className="flex h-12 justify-start overflow-x-auto border border-slate-800 bg-slate-900 p-1">
            {CATEGORIES.map((category) => (
              <TabsTrigger
                key={category}
                value={category}
                className="px-6 text-slate-400 data-[state=active]:bg-cyan-600 data-[state=active]:text-white"
              >
                {category}
              </TabsTrigger>
            ))}
          </TabsList>

          {CATEGORIES.map((category) => (
            <TabsContent key={category} value={category} className="mt-6">
              <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-6">
                <h3 className="mb-2 text-lg font-semibold text-white">{category}</h3>
                <p className="text-sm text-slate-400">
                  {category === 'Unicorn Model (Breaker + FVG)' && 'Requires a breaker reclaim and fresh imbalance before the engine promotes execution.'}
                  {category === 'Silver Bullet Session Sweep' && 'Looks for defined liquidity windows with a sweep and sharp reclaim.'}
                  {category === 'OTE Retracement Tap' && 'Focuses on 0.705 retracement alignment within the higher-timeframe dealing range.'}
                  {category === 'Turtle Soup' && 'Catches failed breakout inducements that reverse after sweeping obvious stops.'}
                </p>
              </div>
              {renderSignalsForCategory(category)}
            </TabsContent>
          ))}
        </Tabs>
      </main>
    </div>
  );
}
