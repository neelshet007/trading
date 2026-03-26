'use client';

import { Activity, BarChart2, Compass, Layers, List, Search } from 'lucide-react';
import Link from 'next/link';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { fetcher } from '@/lib/api';
import { Badge } from './ui/badge';
import { getSignalClasses } from '@/lib/market';

interface SearchResult {
  symbol: string;
  name: string;
  signal: string;
  rating: string;
  categories: string[];
  analysis?: {
    why_now?: string;
  } | null;
}

export function Sidebar() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const router = useRouter();

  useEffect(() => {
    if (query.length < 2) {
      const clearResults = window.setTimeout(() => setResults([]), 0);
      return () => clearTimeout(clearResults);
    }

    const delay = window.setTimeout(async () => {
      const res = await fetcher(`/search/${query}`);
      if (res) setResults(res as SearchResult[]);
      else setResults([]);
    }, 500);

    return () => clearTimeout(delay);
  }, [query]);

  useEffect(() => {
    if (query.length !== 0) {
      return;
    }
    const clearResults = window.setTimeout(() => setResults([]), 0);
    return () => clearTimeout(clearResults);
  }, [query.length]);

  const handleSelect = (symbol: string) => {
    setQuery('');
    setResults([]);
    router.push(`/stock/${symbol}`);
  };
  return (
    <div className="w-64 h-full bg-slate-900 border-r border-slate-800 flex flex-col p-4">
      <div className="flex items-center gap-2 px-2 py-4 mb-4">
        <Activity className="text-emerald-500 w-8 h-8" />
        <h1 className="text-xl font-bold tracking-tight text-slate-100">Trade<span className="text-emerald-500">Intel</span></h1>
      </div>
      
      <div className="px-3 mb-6 relative">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input 
            type="text" 
            placeholder="Search company (e.g. Infosys)" 
            className="w-full bg-slate-800 border border-slate-700 text-sm text-white rounded-md pl-9 pr-3 py-2 outline-none focus:border-emerald-500 transition-colors"
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
        </div>
        {results.length > 0 && (
          <div className="absolute top-full left-3 right-3 mt-1 bg-slate-800 border border-slate-700 rounded-md shadow-xl z-50 overflow-hidden">
            {results.map((r) => (
              <div 
                key={r.symbol} 
                className="px-3 py-2 hover:bg-slate-700 cursor-pointer border-b border-slate-700/50 last:border-0"
                onClick={() => handleSelect(r.symbol)}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="text-white font-medium">{r.symbol}</div>
                  <Badge className={getSignalClasses(r.signal)}>{r.signal}</Badge>
                </div>
                <div className="text-xs text-slate-400 truncate">{r.name}</div>
                {r.analysis && (
                  <div className="mt-1 space-y-1">
                    <div className="text-[11px] text-slate-300 truncate">{r.analysis.why_now}</div>
                    <div className="flex flex-wrap gap-1">
                      {r.categories?.slice(0, 2).map((category: string) => (
                        <Badge key={category} variant="outline" className="border-slate-600 text-slate-300 text-[10px]">
                          {category}
                        </Badge>
                      ))}
                      <Badge variant="outline" className="border-slate-600 text-slate-300 text-[10px]">
                        Rating {r.rating}
                      </Badge>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      
      <nav className="flex flex-col gap-2">
        <Link href="/" className="flex items-center gap-3 px-3 py-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-md transition-colors">
          <Compass className="w-5 h-5" />
          <span className="font-medium">Dashboard</span>
        </Link>
        <Link href="/strategies" className="flex items-center gap-3 px-3 py-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-md transition-colors">
          <Layers className="w-5 h-5" />
          <span className="font-medium">Strategies</span>
        </Link>
        <Link href="/watchlist" className="flex items-center gap-3 px-3 py-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-md transition-colors">
          <List className="w-5 h-5" />
          <span className="font-medium">Watchlist</span>
        </Link>
        <Link href="/market" className="flex items-center gap-3 px-3 py-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-md transition-colors">
          <BarChart2 className="w-5 h-5" />
          <span className="font-medium">Market Overview</span>
        </Link>
      </nav>
      <div className="mt-auto px-2 py-4 text-xs text-slate-500">
        AI-driven market scanning. Not financial advice.
      </div>
    </div>
  );
}
