'use client';

import { useEffect, useState } from 'react';
import { Sidebar } from '@/components/Sidebar';
import { fetcher } from '@/lib/api';
import { SignalCard } from '@/components/SignalCard';

export default function MarketOverview() {
  const [allSignals, setAllSignals] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      // Fetch both intraday and swing
      const intraday = await fetcher('/signals?timeframe=intraday') || [];
      const swing = await fetcher('/signals?timeframe=swing') || [];
      setAllSignals([...intraday, ...swing]);
      setLoading(false);
    };
    loadData();
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-200">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-white tracking-tight">Market Overview (All Data)</h2>
          <p className="text-slate-400 mt-1">Every currently active signal detected by the background engine across all timeframes.</p>
        </div>

        {loading ? (
          <div className="text-slate-400 py-8">Fetching massive data list from engine...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {allSignals.map((sig, i) => (
              <SignalCard key={i} signal={sig} />
            ))}
            
            {allSignals.length === 0 && (
              <div className="col-span-full py-12 text-center border border-dashed border-slate-800 rounded-xl bg-slate-900/50">
                <div className="text-lg text-white mb-2">No signals generated yet.</div>
                <div className="text-slate-400">The background engine might be running its initial analysis (takes ~30-60 seconds after startup) or no strong setups were found in the current market conditions. Use the Search bar in the sidebar to manually look up specific stock charts!</div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
