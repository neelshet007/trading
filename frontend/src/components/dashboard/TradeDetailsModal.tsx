'use client';

import React from 'react';
import { SetupData } from './TradeCards';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { X, CheckCircle2, History, LocateFixed } from 'lucide-react';

interface TradeDetailsModalProps {
  setup: SetupData;
  onClose: () => void;
}

export function TradeDetailsModal({ setup, onClose }: TradeDetailsModalProps) {
  const isBullish = setup.bias === 'bullish';
  const neonColor = isBullish ? 'text-emerald-400' : 'text-rose-400';
  
  if (!setup.narrative) return null;
  const narrative = setup.narrative;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/60 backdrop-blur-[2px] transition-all">
      <Card className="h-full w-full max-w-md border-l border-slate-700 bg-slate-950/95 shadow-[-10px_0_30px_rgba(0,0,0,0.8)] animate-in slide-in-from-right duration-300 rounded-none overflow-y-auto">
        <CardHeader className="sticky top-0 z-10 border-b border-slate-800 bg-slate-950/80 backdrop-blur flex flex-row items-center justify-between py-4">
          <CardTitle className="text-xl font-bold text-white tracking-widest flex items-center gap-2">
            {setup.symbol}
            <span className={`text-[10px] px-2 py-0.5 rounded border border-slate-700 bg-slate-900 ${neonColor}`}>DETAILED ANALYSIS</span>
          </CardTitle>
          <button onClick={onClose} className="p-1 hover:bg-slate-800 rounded-full transition-colors">
            <X className="h-5 w-5 text-slate-400" />
          </button>
        </CardHeader>
        
        <CardContent className="p-6 space-y-8">
          
           {/* Executive Summary */}
          <div className="space-y-4">
             <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/5 p-4 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-2 opacity-10"><LocateFixed className="w-16 h-16 text-cyan-400"/></div>
                <h4 className="text-xs uppercase tracking-widest text-cyan-500 mb-1 font-semibold">Execution Rationale</h4>
                <div className="text-lg text-slate-200 font-medium mb-3">{narrative.reason}</div>
                {narrative.zoom_reason && (
                  <div className="text-sm font-semibold text-violet-400 bg-violet-500/10 p-2 rounded border border-violet-500/20">
                    🔬 {narrative.zoom_reason}
                  </div>
                )}
             </div>
             <div>
                <h4 className="text-xs uppercase tracking-widest text-slate-500 mb-1">Market Context</h4>
                <p className="text-sm text-slate-400 leading-relaxed indent-4 border-l-2 border-slate-800 pl-3">
                  {narrative.context}
                </p>
             </div>
          </div>

          {/* Location & Structure */}
          <div className="grid grid-cols-2 gap-4">
             <div className="border border-slate-800 rounded p-3 bg-slate-900/40">
               <div className="text-[10px] text-slate-500 uppercase tracking-widest">HTF Zone</div>
               <div className="text-sm font-semibold text-slate-300 mt-1">{narrative.location}</div>
             </div>
             <div className="border border-slate-800 rounded p-3 bg-slate-900/40">
               <div className="text-[10px] text-slate-500 uppercase tracking-widest">Market Phase</div>
               <div className={`text-sm font-semibold mt-1 ${isBullish ? 'text-emerald-400' : 'text-rose-400'}`}>
                 {isBullish ? 'Accumulation/Markup' : 'Distribution/Markdown'}
               </div>
             </div>
          </div>

          {/* Analysis Breakdown */}
          <div className="space-y-3">
            <h4 className="text-sm uppercase tracking-widest text-slate-500 font-semibold border-b border-slate-800 pb-2">Scoring Breakdown</h4>
            <div className="space-y-2">
              {narrative.score_breakdown.map((score: string, idx: number) => (
                <div key={idx} className="flex items-center gap-3 text-sm text-slate-300 bg-slate-900/20 p-2 rounded">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  {score}
                </div>
              ))}
            </div>
          </div>

          {/* Timeline Execution String */}
          <div className="space-y-4 pt-4 border-t border-slate-800">
            <h4 className="text-sm uppercase tracking-widest text-slate-500 font-semibold flex items-center gap-2">
              <History className="h-4 w-4" /> Trade Timeline
            </h4>
            <div className="pl-2 border-l-2 border-slate-700/50 space-y-5 relative">
              {narrative.timeline.map((event: string, idx: number) => (
                <div key={idx} className="relative pl-4">
                  <div className="absolute w-2 h-2 rounded-full bg-cyan-400 -left-[5px] top-1.5 shadow-[0_0_5px_rgba(34,211,238,0.8)]" />
                  <div className="text-sm text-slate-300">{event}</div>
                </div>
              ))}
            </div>
          </div>

        </CardContent>
      </Card>
    </div>
  );
}
