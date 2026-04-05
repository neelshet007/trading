'use client';

import { useEffect, useState } from 'react';
import { Activity, Clock3, Radar, TrendingUp } from 'lucide-react';

import { Sidebar } from '@/components/Sidebar';
import { useStore } from '@/store/useStore';
import { fetcher } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { SignalCard } from '@/components/SignalCard';
import { TradeCards, SetupData } from '@/components/dashboard/TradeCards';
import { TerminalFeed } from '@/components/dashboard/TerminalFeed';
import { MTFChart } from '@/components/dashboard/MTFChart';
import { TradeDetailsModal } from '@/components/dashboard/TradeDetailsModal';
import {
  formatDisplayDate,
  formatDisplayTime,
  getStatusBadgeClasses,
  type MarketSummary,
  type Signal,
} from '@/lib/market';

const MARKET_ICONS: Record<string, string> = {
  USA: 'US',
  INDIA: 'IN',
  CRYPTO: 'CR',
  COMMODITIES: 'CM',
};

export default function Home() {
  const { timeframe, setTimeframe, market, setMarket, marketSummary, setMarketSummary } = useStore();
  const [signals, setSignals] = useState<Signal[]>([]);
  
  // SMC Terminal State
  const [smcSetups, setSmcSetups] = useState<SetupData[]>([]);
  const [selectedSetup, setSelectedSetup] = useState<SetupData | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const [showDetailsModal, setShowDetailsModal] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    const loadData = async () => {
      const [summary, signalsData] = await Promise.all([
        fetcher(`/market-summary?market=${market}`),
        fetcher(`/signals?timeframe=${timeframe}&market=${market}`),
      ]);

      if (summary) setMarketSummary(summary as MarketSummary);
      if (signalsData) setSignals(signalsData as Signal[]);
    };

    const initialLoad = window.setTimeout(() => {
      void loadData();
    }, 0);
    const interval = window.setInterval(() => {
      void loadData();
    }, 30000);
    return () => {
      clearTimeout(initialLoad);
      clearInterval(interval);
    };
  }, [timeframe, market, setMarketSummary]);

  const handleScanSMC = async () => {
    setIsScanning(true);
    try {
      // For demo purposes, we scan a basket of Nifty 50 and popular symbols
      const symbolsToScan = market === 'INDIA' 
        ? ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS', 'ITC.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS', 'LT.NS']
        : market === 'CRYPTO'
        ? ['BTC-USD', 'ETH-USD', 'SOL-USD', 'XRP-USD', 'ADA-USD', 'BNB-USD', 'DOGE-USD', 'MATIC-USD', 'LINK-USD', 'DOT-USD', 'AVAX-USD', 'UNI-USD']
        : ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'META', 'GOOGL', 'NFLX', 'AMD', 'SPY'];
        
      const response = await fetch('http://localhost:8000/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(symbolsToScan),
      });
      
      const data = await response.json();
      if (data && data.opportunities) {
        setSmcSetups(data.opportunities);
        if (data.opportunities.length > 0) {
          setSelectedSetup(data.opportunities[0]);
        }
      }
    } catch (e) {
      console.error('Scan failed', e);
    } finally {
      setIsScanning(false);
    }
  };

  const topSignals = signals.slice(0, 10);
  const marketClock = marketSummary?.market_clock;

  if (!isMounted) {
    return null; // Avoid hydration mismatch on the server
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[radial-gradient(circle_at_top,rgba(22,78,99,0.18),transparent_30%),linear-gradient(180deg,#020617_0%,#07111f_45%,#020617_100%)] text-slate-200">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mb-8 flex flex-col gap-5 border-b border-slate-800/80 pb-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <span className="rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1 text-xs font-semibold tracking-[0.3em] text-slate-300">
                {MARKET_ICONS[market]}
              </span>
              <Badge className={getStatusBadgeClasses(marketClock?.status_color)}>{marketClock?.status_text || 'Loading session'}</Badge>
            </div>
            <div>
              <h2 className="text-4xl font-bold tracking-tight text-white">{market} Intelligence Terminal</h2>
              <p className="mt-2 max-w-3xl text-slate-400">
                Clean signal ranking with market hours, timezone context, scanner categories, and a direct answer to why each stock matters right now.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-950/70 p-1">
              {(['USA', 'INDIA', 'CRYPTO', 'COMMODITIES'] as const).map((item) => (
                <button
                  key={item}
                  onClick={() => setMarket(item)}
                  className={`rounded-lg px-3 py-2 text-sm font-medium transition-all ${market === item ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  {item}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-950/70 p-1">
              <button
                onClick={() => setTimeframe('intraday')}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition-all ${timeframe === 'intraday' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
              >
                Intraday
              </button>
              <button
                onClick={() => setTimeframe('swing')}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition-all ${timeframe === 'swing' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
              >
                Swing
              </button>
            </div>
          </div>
        </div>

        <div className="mb-8 grid grid-cols-1 gap-6 xl:grid-cols-4">
          <div className="xl:col-span-1 border border-slate-800 rounded-xl bg-slate-950/80 overflow-hidden shadow-[0_0_15px_rgba(0,0,0,0.4)] flex flex-col h-[600px]">
            <div className="p-4 border-b border-slate-800/80 bg-slate-900 flex justify-between items-center">
              <h3 className="font-bold tracking-widest text-[#22d3ee] uppercase text-sm">Control Panel</h3>
              <button 
                onClick={handleScanSMC}
                disabled={isScanning}
                className="px-4 py-1.5 bg-[#22d3ee]/20 hover:bg-[#22d3ee]/30 text-[#22d3ee] rounded shadow-[0_0_10px_rgba(34,211,238,0.4)] transition-all flex items-center gap-2 border border-[#22d3ee]/50 text-xs font-bold disabled:opacity-50"
              >
                {isScanning ? <Activity className="w-4 h-4 animate-spin"/> : <Radar className="w-4 h-4" />}
                {isScanning ? 'SCANNING...' : 'SCAN SMC'}
              </button>
            </div>
            <div className="flex-1 overflow-hidden">
             <TerminalFeed setups={smcSetups} onSelectSetup={setSelectedSetup} selectedSymbol={selectedSetup?.symbol} />
            </div>
          </div>
          
          <div className="xl:col-span-3 flex flex-col gap-6">
            {selectedSetup ? (
               <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 relative">
                 <div className="hidden lg:block absolute inset-0 bg-[#22d3ee]/5 rounded-xl blur-2xl z-0 pointer-events-none" />
                 <div className="lg:col-span-1 z-10 relative cursor-pointer hover:ring-2 ring-cyan-500/50 rounded-xl transition-all" onClick={() => setShowDetailsModal(true)}>
                   <TradeCards setup={selectedSetup} />
                   <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 bg-slate-900 border border-slate-700 text-[10px] uppercase text-cyan-400 px-3 py-1 rounded-full shadow-lg z-20">Click for Detailed Analysis</div>
                 </div>
                 <div className="lg:col-span-2 h-[380px] z-10 relative">
                   <MTFChart setup={selectedSetup} />
                 </div>
               </div>
            ) : (
               <div className="h-[380px] border border-dashed border-slate-800 rounded-xl bg-slate-900/30 flex items-center justify-center">
                  <div className="text-center">
                    <Activity className="mx-auto h-12 w-12 text-slate-700 mb-3" />
                    <p className="text-slate-500 font-mono">Terminal Standby. Initiate Scan.</p>
                  </div>
               </div>
            )}
          </div>
        </div>

        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader>
            <CardTitle className="flex items-center justify-between gap-3 text-white">
              <span>Standard Market Overview</span>
              <Badge variant="outline" className="border-slate-700 text-slate-300">{topSignals.length} visible</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {topSignals.length === 0 ? (
              <div className="py-12 text-center text-slate-400">
                <Activity className="mx-auto mb-4 h-12 w-12 text-slate-700" />
                No standard setups found right now for {market}.
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
                {topSignals.map((signal) => (
                  <SignalCard key={`${signal.symbol}-${signal.strategy}-${signal.timeframe}`} signal={signal} />
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
