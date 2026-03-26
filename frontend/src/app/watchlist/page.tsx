'use client';

import { useEffect, useState } from 'react';
import { Sidebar } from '@/components/Sidebar';
import { fetcher } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Trash2 } from 'lucide-react';

interface WatchlistItem {
  symbol: string;
  added_at: string;
}

export default function WatchlistPage() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [newSymbol, setNewSymbol] = useState('');

  const loadWatchlist = async () => {
    const res = await fetcher('/watchlist');
    if (res) setWatchlist(res);
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
      body: JSON.stringify({ symbol: newSymbol })
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
          <h2 className="text-3xl font-bold text-white tracking-tight">Family Watchlist</h2>
          <p className="text-slate-400 mt-1">Shared tickers to monitor for potential setups.</p>
        </div>

        <form onSubmit={handleAdd} className="flex gap-4 mb-8">
          <input 
            type="text" 
            placeholder="Enter symbol (e.g. AAPL)" 
            className="bg-slate-900 border border-slate-800 rounded-md px-4 py-2 text-white outline-none focus:border-emerald-500 transition-colors w-64 uppercase"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value)}
          />
          <Button type="submit" className="bg-emerald-600 hover:bg-emerald-700 text-white">Add to Watchlist</Button>
        </form>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {watchlist.map(item => (
            <div key={item.symbol} className="bg-slate-900 border border-slate-800 rounded-lg p-5 flex justify-between items-center group hover:border-slate-700 transition-colors">
              <div>
                <h3 className="text-xl font-bold text-white mb-1">{item.symbol}</h3>
                <span className="text-xs text-slate-500">Added: {new Date(item.added_at).toLocaleDateString()}</span>
              </div>
              <button 
                onClick={() => handleRemove(item.symbol)}
                className="text-slate-600 hover:text-red-400 transition-colors p-2 rounded-full hover:bg-slate-800 opacity-0 group-hover:opacity-100"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            </div>
          ))}
          
          {watchlist.length === 0 && (
            <div className="col-span-full py-8 text-center text-slate-500 border border-dashed border-slate-800 rounded-lg bg-slate-900/50">
              Watchlist is currently empty. Add symbols above.
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
