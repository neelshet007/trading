import Link from 'next/link';
import { ArrowRight, Radar, ShieldAlert, Target, Waves } from 'lucide-react';

import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { formatDisplayTime, getSignalClasses, getWhyNow, type SetupSignal } from '@/lib/market';

export function SignalCard({ signal }: { signal: SetupSignal }) {
  return (
    <Card className="group border border-slate-800 bg-[linear-gradient(145deg,rgba(15,23,42,0.98),rgba(2,6,23,0.94))] shadow-[0_24px_80px_rgba(2,6,23,0.35)] transition-all hover:border-slate-600">
      <Link href={`/stock/${signal.symbol}?market=CRYPTO`} className="block h-full">
        <CardContent className="space-y-4 p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-xl font-bold tracking-tight text-white">{signal.symbol}</h3>
                <Badge className={getSignalClasses(signal.bias)}>
                  {signal.bias === 'bullish' ? 'Long Bias' : 'Short Bias'}
                </Badge>
                <Badge variant="outline" className="border-cyan-500/30 text-cyan-300">
                  HMM {signal.context.hmm_state}
                </Badge>
              </div>
              <p className="text-sm text-slate-400">{signal.trigger.entry_model} • {signal.trigger.execution_timeframe}</p>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-white">{signal.confluence.total_score.toFixed(1)}</div>
              <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Confluence</div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
            <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-slate-500">
              <Radar className="h-3.5 w-3.5" /> Context
            </div>
            <p className="text-sm leading-6 text-slate-100">{getWhyNow(signal)}</p>
            <p className="mt-2 text-xs text-slate-400">{signal.context.ipda_cycle}</p>
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
            <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-slate-300">
              <div className="flex items-center gap-1 text-slate-500"><Target className="h-4 w-4" /> Entry</div>
              <div className="mt-1 font-semibold text-white">{signal.trigger.entry_price.toFixed(2)}</div>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-slate-300">
              <div className="flex items-center gap-1 text-slate-500"><ShieldAlert className="h-4 w-4" /> VaR</div>
              <div className="mt-1 font-semibold text-white">{signal.risk.var_95.toFixed(2)}</div>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-slate-300">
              <div className="flex items-center gap-1 text-slate-500"><Waves className="h-4 w-4" /> Slippage</div>
              <div className="mt-1 font-semibold text-white">{signal.risk.expected_slippage_bps.toFixed(2)} bps</div>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-slate-300">
              <div className="text-slate-500">Updated</div>
              <div className="mt-1 font-semibold text-white">{formatDisplayTime(signal.timestamp)}</div>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Badge variant="outline" className="border-slate-700 text-slate-300">
              {signal.footprint.structure_signal}
            </Badge>
            <Badge variant="outline" className="border-slate-700 text-slate-300">
              {signal.footprint.cvd_divergence}
            </Badge>
            <Badge variant="outline" className="border-slate-700 text-slate-300">
              Expectancy {signal.risk.expectancy.toFixed(2)}R
            </Badge>
          </div>

          <div className="flex items-center justify-between border-t border-slate-800 pt-4 text-sm text-slate-400">
            <span>{signal.hitl.inducement_traps[0]}</span>
            <ArrowRight className="h-4 w-4 transition-colors group-hover:text-cyan-300" />
          </div>
        </CardContent>
      </Link>
    </Card>
  );
}
