import { useEffect, useState } from 'react';
import { Sidebar } from '@/components/Sidebar';
import { useStore } from '@/store/useStore';
import { fetcher } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { SignalCard } from '@/components/SignalCard';

export default function Home() {
  const { timeframe, setTimeframe, marketSummary, setMarketSummary } = useStore();
  const [topSignals, setTopSignals] = useState<any[]>([]);

  const loadData = async () => {
    const summary = await fetcher('/market-summary');
    if (summary) setMarketSummary(summary);
    
    // Also load top signals for dashboard
    const signals = await fetcher(`/signals?timeframe=${timeframe}`);
    if (signals) setTopSignals(signals.slice(0, 5));
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-200">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h2 className="text-3xl font-bold text-white tracking-tight">Main Dashboard</h2>
            <p className="text-slate-400 mt-1">Real-time market analysis and setups</p>
          </div>
          <div className="flex items-center gap-4 bg-slate-900 p-1 rounded-lg">
            <button 
              onClick={() => setTimeframe('intraday')}
              className={`px-4 py-2 rounded-md font-medium transition-colors ${timeframe === 'intraday' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Intraday (5m)
            </button>
            <button 
              onClick={() => setTimeframe('swing')}
              className={`px-4 py-2 rounded-md font-medium transition-colors ${timeframe === 'swing' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
            >
              Swing (Daily)
            </button>
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
              <CardTitle className="text-white">Top 5 {timeframe === 'intraday' ? 'Intraday' : 'Swing'} Setups</CardTitle>
            </CardHeader>
            <CardContent>
              {topSignals.length === 0 ? (
                <div className="text-slate-400 pb-4">Loading top setups from the pipeline...</div>
              ) : (
                <div className="flex flex-col gap-2 pt-2">
                  {topSignals.map((sig, i) => (
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
