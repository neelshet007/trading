'use client';

import { useEffect, useState } from 'react';

import { Sidebar } from '@/components/Sidebar';
import { useStore } from '@/store/useStore';
import { fetcher } from '@/lib/api';
import { SignalCard } from '@/components/SignalCard';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { MarketKey, Signal } from '@/lib/market';

const CATEGORIES = [
  'VCP Scanner',
  'Rocket Base Scanner',
  'Momentum Scanner',
  'Volume Spike Scanner',
];

const MARKETS: { id: MarketKey; label: string }[] = [
  { id: 'USA', label: 'USA' },
  { id: 'INDIA', label: 'INDIA' },
  { id: 'CRYPTO', label: 'CRYPTO' },
  { id: 'COMMODITIES', label: 'COMMODITIES' },
];

export default function StrategiesPage() {
  const { timeframe, market, setMarket } = useStore();
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadSignals = async () => {
      setLoading(true);
      const data = await fetcher(`/signals?timeframe=${timeframe}&market=${market}`);
      setSignals((data as Signal[]) || []);
      setLoading(false);
    };
    loadSignals();
  }, [timeframe, market]);

  const renderSignalsForCategory = (category: string) => {
    const filtered = signals.filter((signal) => signal.categories?.includes(category));
    if (loading) return <div className="py-8 text-slate-400">Scanning {market} for {category} setups...</div>;
    if (filtered.length === 0) {
      return <div className="rounded-lg border border-dashed border-slate-800 py-8 text-center text-slate-400">No setups found for {category} in {market} ({timeframe}).</div>;
    }
    return (
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {filtered.map((signal) => (
          <SignalCard key={`${signal.symbol}-${signal.strategy}-${signal.timestamp}`} signal={signal} />
        ))}
      </div>
    );
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-200">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-white">Category Scanners</h2>
            <p className="mt-1 text-slate-400">Ranked by confluence so the strongest multi-signal setups appear first.</p>
          </div>
          <div className="flex rounded-lg border border-slate-800 bg-slate-900 p-1">
            {MARKETS.map((item) => (
              <button
                key={item.id}
                onClick={() => setMarket(item.id)}
                className={`rounded-md px-4 py-1.5 text-sm font-medium transition-all ${market === item.id ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-slate-200'}`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        <Tabs defaultValue={CATEGORIES[0]} className="w-full">
          <TabsList className="flex h-12 justify-start overflow-x-auto border border-slate-800 bg-slate-900 p-1">
            {CATEGORIES.map((category) => (
              <TabsTrigger
                key={category}
                value={category}
                className="px-6 text-slate-400 data-[state=active]:bg-emerald-600 data-[state=active]:text-white"
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
                  {category === 'VCP Scanner' && 'Looks for volatility contraction, shrinking volume, and a tight launchpad near a breakout level.'}
                  {category === 'Rocket Base Scanner' && 'Tracks strong impulse moves that pause in a small base before the next decision point.'}
                  {category === 'Momentum Scanner' && 'Finds names already moving with trend alignment, pullbacks, or reversals that can continue.'}
                  {category === 'Volume Spike Scanner' && 'Highlights fresh breakouts where participation expands and price escapes a recent range.'}
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
