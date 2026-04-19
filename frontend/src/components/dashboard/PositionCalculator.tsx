'use client';

import { useState } from 'react';
import { ArrowRight, Calculator, DollarSign, Percent, Target } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface PositionCalculatorProps {
  entryPrice: number;
  stopLoss: number;
  maxAllocation?: number;
}

export function PositionCalculator({ entryPrice, stopLoss, maxAllocation = 0.15 }: PositionCalculatorProps) {
  const [accountSize, setAccountSize] = useState<number>(100000);
  const [riskPercent, setRiskPercent] = useState<number>(1);

  const riskAmount = (accountSize * riskPercent) / 100;
  const riskPerUnit = Math.abs(entryPrice - stopLoss);
  const rawQuantity = riskPerUnit > 0 ? riskAmount / riskPerUnit : 0;
  const maxPositionNotional = accountSize * maxAllocation;
  const cappedQuantity = entryPrice > 0 ? Math.floor(Math.min(rawQuantity, maxPositionNotional / entryPrice)) : 0;
  const totalPositionSize = cappedQuantity * entryPrice;

  return (
    <Card className="h-full border-slate-800 bg-slate-950/70">
      <CardHeader className="border-b border-slate-800 pb-3">
        <CardTitle className="flex items-center gap-2 text-sm uppercase tracking-widest text-slate-400">
          <Calculator className="h-4 w-4 text-cyan-400" /> Crypto Risk Engine
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5 pt-5">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase text-slate-500">Account Size ($)</label>
            <div className="relative">
              <DollarSign className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-600" />
              <input
                type="number"
                value={accountSize}
                onChange={(e) => setAccountSize(Number(e.target.value) || 0)}
                className="w-full rounded border border-slate-700 bg-slate-900 px-8 py-2 text-sm text-slate-200 outline-none transition-all focus:ring-1 focus:ring-cyan-500"
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-[10px] font-semibold uppercase text-slate-500">Risk per Trade (%)</label>
            <div className="relative">
              <Percent className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-600" />
              <input
                type="number"
                min="0.1"
                step="0.1"
                value={riskPercent}
                onChange={(e) => setRiskPercent(Number(e.target.value) || 0)}
                className="w-full rounded border border-slate-700 bg-slate-900 px-8 py-2 text-sm text-slate-200 outline-none transition-all focus:ring-1 focus:ring-cyan-500"
              />
            </div>
          </div>
        </div>

        <div className="relative overflow-hidden rounded-xl border border-cyan-500/30 bg-cyan-500/10 p-4">
          <div className="absolute right-0 top-0 p-2 opacity-10"><Target className="h-16 w-16 text-cyan-400" /></div>
          <h4 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-cyan-300">
            Position Protocol
          </h4>
          <div className="relative z-10 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-400">Target Entry</span>
              <span className="font-semibold text-slate-200">${entryPrice.toFixed(2)}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-400">Fail-Safe Stop</span>
              <span className="font-semibold text-rose-400">${stopLoss.toFixed(2)}</span>
            </div>
            <div className="mt-2 flex items-center justify-between rounded border border-slate-700/50 bg-slate-900/50 p-2">
              <span className="font-medium text-slate-300">Safe Quantity</span>
              <span className="flex items-center gap-2 text-lg font-bold text-cyan-300">
                {cappedQuantity} units <ArrowRight className="h-4 w-4" />
              </span>
            </div>
            <div className="flex items-center justify-between pt-1 text-[10px] uppercase tracking-wider text-slate-500">
              <span>Capital Risk: ${riskAmount.toFixed(0)}</span>
              <span>Cap Notional: ${maxPositionNotional.toFixed(0)}</span>
            </div>
            <div className="text-[11px] text-slate-400">
              Final size is clipped by the max allocation guard before execution.
            </div>
            <div className="text-sm text-white">
              Estimated notional: ${totalPositionSize.toFixed(2)}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
