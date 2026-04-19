'use client';

import { CheckCircle2, History, LocateFixed, X } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { type SetupData } from './TradeCards';

interface TradeDetailsModalProps {
  setup: SetupData;
  onClose: () => void;
}

export function TradeDetailsModal({ setup, onClose }: TradeDetailsModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/60 backdrop-blur-[2px]">
      <Card className="h-full w-full max-w-md overflow-y-auto rounded-none border-l border-slate-700 bg-slate-950/95 shadow-[-10px_0_30px_rgba(0,0,0,0.8)]">
        <CardHeader className="sticky top-0 z-10 flex flex-row items-center justify-between border-b border-slate-800 bg-slate-950/80 py-4 backdrop-blur">
          <CardTitle className="flex items-center gap-2 text-xl font-bold tracking-widest text-white">
            {setup.symbol}
            <span className="rounded border border-slate-700 bg-slate-900 px-2 py-0.5 text-[10px] text-cyan-300">
              HITL ANALYSIS
            </span>
          </CardTitle>
          <button onClick={onClose} className="rounded-full p-1 transition-colors hover:bg-slate-800">
            <X className="h-5 w-5 text-slate-400" />
          </button>
        </CardHeader>

        <CardContent className="space-y-8 p-6">
          <div className="space-y-4">
            <div className="relative overflow-hidden rounded-xl border border-cyan-500/30 bg-cyan-500/5 p-4">
              <div className="absolute right-0 top-0 p-2 opacity-10"><LocateFixed className="h-16 w-16 text-cyan-400" /></div>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-widest text-cyan-500">Execution Rationale</h4>
              <div className="mb-3 text-lg font-medium text-slate-200">{setup.narrative?.reason || setup.trigger.entry_model}</div>
              <div className="rounded border border-violet-500/20 bg-violet-500/10 p-2 text-sm font-semibold text-violet-300">
                {setup.narrative?.zoom_reason || setup.trigger.confirmation}
              </div>
            </div>
            <div>
              <h4 className="mb-1 text-xs uppercase tracking-widest text-slate-500">Market Context</h4>
              <p className="border-l-2 border-slate-800 pl-3 text-sm leading-relaxed text-slate-400">
                {setup.narrative?.context || setup.context.hmm_regime}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="rounded border border-slate-800 bg-slate-900/40 p-3">
              <div className="text-[10px] uppercase tracking-widest text-slate-500">IPDA Cycle</div>
              <div className="mt-1 text-sm font-semibold text-slate-300">{setup.context.ipda_cycle}</div>
            </div>
            <div className="rounded border border-slate-800 bg-slate-900/40 p-3">
              <div className="text-[10px] uppercase tracking-widest text-slate-500">Footprint</div>
              <div className="mt-1 text-sm font-semibold text-slate-300">{setup.footprint.structure_signal}</div>
            </div>
          </div>

          <div className="space-y-3">
            <h4 className="border-b border-slate-800 pb-2 text-sm font-semibold uppercase tracking-widest text-slate-500">Scoring Breakdown</h4>
            <div className="space-y-2">
              {(setup.narrative?.score_breakdown || []).map((score, idx) => (
                <div key={idx} className="flex items-center gap-3 rounded bg-slate-900/20 p-2 text-sm text-slate-300">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  {score}
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-4 border-t border-slate-800 pt-4">
            <h4 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-widest text-slate-500">
              <History className="h-4 w-4" /> Human Checks
            </h4>
            <div className="space-y-3 border-l-2 border-slate-700/50 pl-4">
              {setup.hitl.human_checks.map((item, idx) => (
                <div key={idx} className="text-sm text-slate-300">
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-3 rounded-xl border border-rose-500/20 bg-rose-500/5 p-4">
            <div className="text-xs uppercase tracking-widest text-rose-300">Inducement Traps</div>
            {setup.hitl.inducement_traps.map((trap, idx) => (
              <div key={idx} className="text-sm text-slate-300">
                {trap}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
