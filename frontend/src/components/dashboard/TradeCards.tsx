'use client';

import { ArrowDownRight, ArrowUpRight, Crosshair, ShieldAlert, Waves } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { type SetupSignal } from '@/lib/market';

export type SetupData = SetupSignal;

interface TradeCardsProps {
  setup: SetupData;
}

export function TradeCards({ setup }: TradeCardsProps) {
  const isBullish = setup.bias === 'bullish';
  const neonColor = isBullish ? 'text-emerald-400' : 'text-rose-400';
  const neonBg = isBullish ? 'bg-emerald-400/10' : 'bg-rose-400/10';
  const Icon = isBullish ? ArrowUpRight : ArrowDownRight;
  const { live_price: livePrice, short, long } = setup.forensic_levels;

  return (
    <Card className="border-slate-800 bg-slate-950/80 shadow-[0_0_15px_rgba(0,0,0,0.5)]">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="flex items-center gap-2 text-xl font-bold tracking-tight text-white">
          {setup.symbol}
          <span className={`rounded-full border border-current px-2 py-0.5 text-xs ${neonBg} ${neonColor}`}>
            {setup.status}
          </span>
        </CardTitle>
        <Icon className={`h-6 w-6 ${neonColor}`} />
      </CardHeader>
      <CardContent>
        <div className="mt-2 grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <span className="text-xs uppercase tracking-wider text-slate-500">Live Price</span>
            <div className={`text-2xl font-mono font-bold ${neonColor}`}>{livePrice.toFixed(2)}</div>
          </div>
          <div className="space-y-1">
            <span className="text-xs uppercase tracking-wider text-slate-500">Expectancy</span>
            <div className="flex items-center gap-1 text-2xl font-mono font-bold text-amber-400">
              <Crosshair className="h-4 w-4" />
              {setup.risk.expectancy.toFixed(2)}R
            </div>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-3 divide-x divide-slate-800 rounded-lg border border-slate-800 bg-slate-900/50">
          <div className="p-3 text-center">
            <div className="text-xs uppercase text-slate-500">Short Range</div>
            <div className="mt-1 font-mono text-sm font-semibold text-rose-400">{short.entry_range_low.toFixed(2)} - {short.entry_range_high.toFixed(2)}</div>
          </div>
          <div className="p-3 text-center">
            <div className="text-xs uppercase text-slate-500">Long Range</div>
            <div className="mt-1 font-mono text-sm font-semibold text-emerald-400">{long.entry_range_low.toFixed(2)} - {long.entry_range_high.toFixed(2)}</div>
          </div>
          <div className="p-3 text-center">
            <div className="text-xs uppercase text-slate-500">OTE</div>
            <div className="mt-1 font-mono text-sm font-semibold text-cyan-400">{setup.footprint.ote_level?.toFixed(2) || '--'}</div>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3">
            <div className="text-xs uppercase text-slate-500">Short SL / TP</div>
            <div className="mt-1 font-mono text-sm text-rose-300">SL {short.stop_loss.toFixed(2)}</div>
            <div className="mt-1 font-mono text-sm text-emerald-300">TP {short.take_profit.toFixed(2)}</div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3">
            <div className="text-xs uppercase text-slate-500">Long SL / TP</div>
            <div className="mt-1 font-mono text-sm text-rose-300">SL {long.stop_loss.toFixed(2)}</div>
            <div className="mt-1 font-mono text-sm text-emerald-300">TP {long.take_profit.toFixed(2)}</div>
          </div>
        </div>

        <div className="mt-5 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-1 text-slate-400"><ShieldAlert className="h-4 w-4" /> HMM / Risk Gate</span>
            <span className="font-bold text-cyan-400">{setup.context.hmm_regime}</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
            <div className="h-full bg-cyan-400 transition-all duration-1000" style={{ width: `${setup.context.regime_confidence * 100}%` }} />
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3">
            <div className="flex items-center gap-1 text-xs uppercase text-slate-500"><Waves className="h-4 w-4" /> Slippage</div>
            <div className="mt-1 text-sm font-semibold text-white">{setup.risk.expected_slippage_bps.toFixed(2)} bps</div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3">
            <div className="text-xs uppercase text-slate-500">Funding Clamp</div>
            <div className="mt-1 text-sm font-semibold text-white">{setup.risk.funding_rate_clamp_bps.toFixed(2)} bps</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
