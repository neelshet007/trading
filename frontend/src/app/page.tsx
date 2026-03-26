'use client';

import { useEffect, useState } from 'react';
import { Sidebar } from '@/components/Sidebar';
import { useStore } from '@/store/useStore';
import { fetcher } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { SignalCard } from '@/components/SignalCard';
import { Activity } from 'lucide-react';

export default function Home() {
  const { timeframe, setTimeframe, market, setMarket, marketSummary, setMarketSummary } = useStore();
  const [signals, setSignals] = useState<any[]>([]);

  const loadData = async () => {
    const summary = await fetcher(`/market-summary?market=${market}`);
    if (summary) setMarketSummary(summary);
    
    const signalsData = await fetcher(`/signals?timeframe=${timeframe}&market=${market}`);
    if (signalsData) setSignals(signalsData);
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000); // Polling
    return () => clearInterval(interval);
  }, [timeframe, market]);

  const displaySignals = market === 'INDIA' ? signals : signals.slice(0, 5);
  const marketIcons: Record<string, string> = {
    USA: '🇺🇸',
    INDIA: '🇮🇳',
    CRYPTO: '🪙',
    COMMODITIES: '🛢'
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-200">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
          <div>
            <h2 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
              <span>{marketIcons[market]}</span> {market} Dashboard
            </h2>
            <p className="text-slate-400 mt-1">Real-time market analysis and setups</p>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-lg border border-slate-800">
              {(['USA', 'INDIA', 'CRYPTO', 'COMMODITIES'] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setMarket(m)}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${market === m ? 'bg-slate-700 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  {m}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-lg border border-slate-800">
              <button 
                onClick={() => setTimeframe('intraday')}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${timeframe === 'intraday' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
              >
                Intraday
              </button>
              <button 
                onClick={() => setTimeframe('swing')}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${timeframe === 'swing' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
              >
                Swing
              </button>
            </div>
          </div>
        </div>

        {/* Market Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-400">Market Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white flex items-center gap-2">
                {marketSummary?.status || 'Loading...'}
                {marketSummary?.status === 'Bullish' && <Badge className="bg-emerald-500/20 text-emerald-400">Bull</Badge>}
                {marketSummary?.status === 'Bearish' && <Badge className="bg-red-500/20 text-red-400">Bear</Badge>}
              </div>
            </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-400">Top Sectors</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-lg font-medium text-white">IT (Strong)</div>
              <div className="text-sm text-slate-400">Banks (Neutral)</div>
            </CardContent>
          </Card>
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-400">Last Updated</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">
                {marketSummary ? new Date(marketSummary.timestamp).toLocaleTimeString() : '--:--'}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
          {/* Top Setups */}
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader>
              <CardTitle className="text-white flex justify-between items-center">
                <span>{market === 'INDIA' ? 'All' : 'Top 5'} {market} {timeframe === 'intraday' ? 'Intraday' : 'Swing'} Setups</span>
                <Badge variant="outline" className="border-slate-700 text-slate-400 font-normal">
                  {displaySignals.length} found
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {displaySignals.length === 0 ? (
                <div className="text-slate-400 py-12 text-center">
                  <Activity className="w-12 h-12 mx-auto mb-4 text-slate-800 animate-pulse" />
                  No high-probability setups found right now for {market}.
                </div>
              ) : (
                <div className="flex flex-col gap-2 pt-2">
                  {displaySignals.map((sig, i) => (
                    <SignalCard key={i} signal={sig} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
