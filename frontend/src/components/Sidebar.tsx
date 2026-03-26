'use client';

import { Activity, BarChart2, Compass, Layers, List } from 'lucide-react';
import Link from 'next/link';

export function Sidebar() {
  return (
    <div className="w-64 h-full bg-slate-900 border-r border-slate-800 flex flex-col p-4">
      <div className="flex items-center gap-2 px-2 py-4 mb-8">
        <Activity className="text-emerald-500 w-8 h-8" />
        <h1 className="text-xl font-bold tracking-tight text-slate-100">Trade<span className="text-emerald-500">Intel</span></h1>
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
