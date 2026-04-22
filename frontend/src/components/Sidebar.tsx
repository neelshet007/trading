'use client';

import { Activity, Compass, FlaskConical, Radar, Search } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';

import { fetcher } from '@/lib/api';
import { Badge } from './ui/badge';
import { type SearchResult } from '@/lib/market';

export function Sidebar() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (query.length < 1) {
      return;
    }
    const timer = window.setTimeout(async () => {
      const res = await fetcher(`/api/search/suggestions?q=${encodeURIComponent(query)}`);
      setResults((res as SearchResult[]) || []);
    }, 180);
    return () => clearTimeout(timer);
  }, [query]);

  const handleSelect = (symbol: string) => {
    setQuery('');
    setResults([]);
    router.push(`/stock/${symbol}?market=CRYPTO`);
  };

  const handleQueryChange = (value: string) => {
    setQuery(value);
    if (value.length < 1) {
      setResults([]);
    }
  };

  const navClass = (href: string) =>
    `flex items-center gap-3 rounded-md px-3 py-2 transition-colors ${
      pathname === href ? 'bg-slate-800 text-white' : 'text-slate-300 hover:bg-slate-800 hover:text-white'
    }`;

  return (
    <div className="flex h-full w-64 flex-col border-r border-slate-800 bg-slate-900 p-4">
      <div className="mb-4 flex items-center gap-2 px-2 py-4">
        <Activity className="h-8 w-8 text-cyan-400" />
        <h1 className="text-xl font-bold tracking-tight text-slate-100">
          Crypto<span className="text-cyan-400">Intel</span>
        </h1>
      </div>

      <div className="relative mb-6 px-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search BTC, ETH, SOL..."
            className="w-full rounded-md border border-slate-700 bg-slate-800 py-2 pl-9 pr-3 text-sm text-white outline-none transition-colors focus:border-cyan-500"
            value={query}
            onChange={(e) => handleQueryChange(e.target.value)}
          />
        </div>
        {results.length > 0 && (
          <div className="absolute left-3 right-3 top-full z-50 mt-1 overflow-hidden rounded-md border border-slate-700 bg-slate-800 shadow-xl">
            {results.map((result) => (
              <button
                key={result.symbol}
                className="block w-full border-b border-slate-700/50 px-3 py-2 text-left last:border-0 hover:bg-slate-700"
                onClick={() => handleSelect(result.fetch_symbol || result.symbol)}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="font-medium text-white">{result.symbol}</div>
                  <Badge variant="outline" className="border-slate-600 text-slate-300">
                    {result.exchange || 'CRYPTO'}
                  </Badge>
                </div>
                <div className="text-xs text-slate-400">{result.name}</div>
              </button>
            ))}
          </div>
        )}
      </div>

      <nav className="flex flex-col gap-2">
        <Link href="/" className={navClass('/')}>
          <Compass className="h-5 w-5" />
          <span className="font-medium">Dashboard</span>
        </Link>
        <Link href="/markets/crypto" className={navClass('/markets/crypto')}>
          <Radar className="h-5 w-5" />
          <span className="font-medium">Crypto Terminal</span>
        </Link>
        <Link href="/backtest" className={navClass('/backtest')}>
          <FlaskConical className="h-5 w-5" />
          <span className="font-medium">Backtest</span>
        </Link>
      </nav>

      <div className="mt-auto px-2 py-4 text-xs text-slate-500">
        Crypto-only decision support. Human confirmation required before execution.
      </div>
    </div>
  );
}
