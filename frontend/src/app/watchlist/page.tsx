'use client';

import { useEffect, useState } from 'react';
import { Sidebar } from '@/components/Sidebar';
import { fetcher } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Trash2 } from 'lucide-react';
import type { SetupSignal } from '@/lib/market';

interface WatchlistItem {
  symbol: string;
  added_at: string;
}

interface WatchlistAuditResponse {
  opportunities: SetupSignal[];
}

export default function WatchlistPage() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [audit, setAudit] = useState<SetupSignal[]>([]);
  const [newSymbol, setNewSymbol] = useState('');

  const loadWatchlist = async () => {
    const [watchlistRes, auditRes] = await Promise.all([
      fetcher('/watchlist'),
      fetcher('/watchlist/audit'),
    ]);
    if (watchlistRes) setWatchlist(watchlistRes);
    if (auditRes) setAudit((auditRes as WatchlistAuditResponse).opportunities || []);
  };

  useEffect(() => {
    const initialLoad = window.setTimeout(() => {
      void loadWatchlist();
    }, 0);
    return () => clearTimeout(initialLoad);
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSymbol) return;
    await fetcher('/watchlist', {
      method: 'POST',
      body: JSON.stringify({ symbol: newSymbol }),
    });
    setNewSymbol('');
    void loadWatchlist();
  };

  const handleRemove = async (symbol: string) => {
    await fetcher(`/watchlist/${symbol}`, { method: 'DELETE' });
    void loadWatchlist();
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-200">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold tracking-tight text-white">Forensic Audit Watchlist</h2>
          <p className="mt-1 text-slate-400">BTC, ETH, and SOL always anchor the audit. Every other crypto is scored beneath that market beta lens.</p>
        </div>

        <form onSubmit={handleAdd} className="mb-8 flex gap-4">
          <input
            type="text"
            placeholder="Enter symbol (e.g. XRP, AVAX, DOT)"
            className="w-64 rounded-md border border-slate-800 bg-slate-900 px-4 py-2 text-white uppercase outline-none transition-colors focus:border-cyan-500"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value)}
          />
          <Button type="submit" className="bg-cyan-600 text-white hover:bg-cyan-700">Add to Watchlist</Button>
        </form>

        <div className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {watchlist.map((item) => (
            <div key={item.symbol} className="group flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900 p-5 transition-colors hover:border-slate-700">
              <div>
                <h3 className="mb-1 text-xl font-bold text-white">{item.symbol}</h3>
                <span className="text-xs text-slate-500">Added: {new Date(item.added_at).toLocaleDateString()}</span>
              </div>
              <button
                onClick={() => handleRemove(item.symbol)}
                className="rounded-full p-2 text-slate-600 opacity-0 transition-colors hover:bg-slate-800 hover:text-red-400 group-hover:opacity-100"
              >
                <Trash2 className="h-5 w-5" />
              </button>
            </div>
          ))}
          {watchlist.length === 0 && (
            <div className="col-span-full rounded-lg border border-dashed border-slate-800 bg-slate-900/50 py-8 text-center text-slate-500">
              Watchlist is currently empty. Add crypto symbols above.
            </div>
          )}
        </div>

        <div className="space-y-6">
          {audit.map((item) => (
            <Card key={item.symbol} className="border-slate-800 bg-slate-950/70">
              <CardHeader className="border-b border-slate-800">
                <CardTitle className="flex flex-wrap items-center justify-between gap-3 text-white">
                  <span>Asset: {item.symbol} | Probability Score: {item.probability_score}</span>
                  <div className="flex gap-2">
                    <Badge variant="outline" className="border-cyan-500/30 text-cyan-300">Market Regime (HMM): State {item.context.hmm_state}</Badge>
                    <Badge variant="outline" className="border-slate-700 text-slate-300">{item.verdict}</Badge>
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-5 pt-5">
                <div>
                  <div className="mb-2 text-xs uppercase tracking-widest text-slate-500">Forensic Evidence</div>
                  <div className="space-y-2 text-sm text-slate-300">
                    {item.forensic_evidence.map((point, idx) => (
                      <div key={idx}>- {point}</div>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                  <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                    <div className="mb-2 text-xs uppercase tracking-widest text-emerald-300">Why Buy</div>
                    <div className="text-sm text-slate-200">{item.why_buy}</div>
                  </div>
                  <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-4">
                    <div className="mb-2 text-xs uppercase tracking-widest text-rose-300">Why Sell/Wait</div>
                    <div className="text-sm text-slate-200">{item.why_sell_wait}</div>
                  </div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-sm text-slate-300">
                  <div className="mb-2 text-xs uppercase tracking-widest text-slate-500">Trade Parameters</div>
                  <div>Entry: {item.trigger.entry_price.toFixed(4)}</div>
                  <div>Stop Loss: {item.trigger.stop_loss.toFixed(4)}</div>
                  <div>Take Profit: {item.trigger.take_profit.toFixed(4)}</div>
                  <div>Beta Note: {item.market_beta_note}</div>
                  <div>Primary Failure: {item.primary_failure || 'None'}</div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </main>
    </div>
  );
}
