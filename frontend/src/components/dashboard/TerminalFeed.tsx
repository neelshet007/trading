'use client';

import React from 'react';
import { SetupData } from './TradeCards';
import { Badge } from '@/components/ui/badge';
import { Activity } from 'lucide-react';

interface TerminalFeedProps {
  setups: SetupData[];
  onSelectSetup: (setup: SetupData) => void;
  selectedSymbol?: string;
}

export function TerminalFeed({ setups, onSelectSetup, selectedSymbol }: TerminalFeedProps) {
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-slate-800 bg-slate-950/60 backdrop-blur-xl">
      <div className="flex items-center gap-2 border-b border-slate-800 bg-slate-900/50 px-4 py-3">
        <Activity className="h-4 w-4 text-cyan-400" />
        <h3 className="font-semibold text-white tracking-widest uppercase text-sm">Live Scanner Feed</h3>
        <Badge variant="outline" className="ml-auto bg-slate-900 text-cyan-400 border-cyan-500/30">
          {setups.length} Qualified
        </Badge>
      </div>

      <div className="flex-1 overflow-y-auto w-full">
        {setups.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-slate-500 italic">
            Awaiting scan results...
          </div>
        ) : (
          <div className="divide-y divide-slate-800/50">
            {setups.map((setup, idx) => {
              const isBullish = setup.bias === 'bullish';
              const isSelected = selectedSymbol === setup.symbol;
              
              return (
                <button
                  key={`${setup.symbol}-${idx}`}
                  onClick={() => onSelectSetup(setup)}
                  className={`w-full text-left px-4 py-3 transition-colors hover:bg-slate-800/40 flex items-center justify-between ${
                    isSelected ? 'bg-slate-800/60 border-l-2 border-cyan-400' : 'border-l-2 border-transparent'
                  }`}
                >
                  <div className="flex flex-col">
                    <span className="font-bold text-slate-200">{setup.symbol}</span>
                    <span className="text-xs text-slate-500 mt-0.5">{setup.context.hmm_regime}</span>
                  </div>
                  
                  <div className="flex flex-col items-end">
                    <span className={`text-sm font-mono font-bold ${isBullish ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {isBullish ? 'LONG' : 'SHORT'}
                    </span>
                    <span className="text-xs text-slate-400 font-mono mt-0.5">
                      @ {setup.trigger.entry_price.toFixed(2)}
                    </span>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  );
}
