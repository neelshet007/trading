'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Target, Calculator, DollarSign, Percent, ArrowRight } from 'lucide-react';

interface PositionCalculatorProps {
  entryPrice: number;
  stopLoss: number;
}

export function PositionCalculator({ entryPrice, stopLoss }: PositionCalculatorProps) {
  const [accountSize, setAccountSize] = useState<number>(500000); // Default 5 Lakhs
  const [riskPercent, setRiskPercent] = useState<number>(1); // Default 1%

  // Calculations
  const riskAmount = (accountSize * riskPercent) / 100;
  const riskPerShare = Math.abs(entryPrice - stopLoss);
  
  const rawQuantity = riskPerShare > 0 ? riskAmount / riskPerShare : 0;
  const quantity = Math.floor(rawQuantity); // Round down for safety
  
  const totalPositionSize = quantity * entryPrice;
  const leverageRequired = totalPositionSize > accountSize ? (totalPositionSize / accountSize).toFixed(1) : 1;

  return (
    <Card className="border-slate-800 bg-slate-950/70 h-full">
      <CardHeader className="pb-3 border-b border-slate-800">
        <CardTitle className="text-sm uppercase tracking-widest text-slate-400 flex items-center gap-2">
          <Calculator className="h-4 w-4 text-emerald-400" /> Math & Risk Engine
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-5 space-y-5">
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-[10px] uppercase text-slate-500 font-semibold mb-1 block">Account Size (₹)</label>
            <div className="relative">
              <DollarSign className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-600" />
              <input 
                type="number" 
                value={accountSize}
                onChange={(e) => setAccountSize(Number(e.target.value) || 0)}
                className="w-full bg-slate-900 border border-slate-700 text-slate-200 rounded text-sm px-8 py-2 focus:ring-1 focus:ring-emerald-500 outline-none transition-all"
              />
            </div>
          </div>
          <div>
            <label className="text-[10px] uppercase text-slate-500 font-semibold mb-1 block">Risk per Trade (%)</label>
            <div className="relative">
              <Percent className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-600" />
              <input 
                type="number" 
                min="0.1"
                step="0.1"
                value={riskPercent}
                onChange={(e) => setRiskPercent(Number(e.target.value) || 0)}
                className="w-full bg-slate-900 border border-slate-700 text-slate-200 rounded text-sm px-8 py-2 focus:ring-1 focus:ring-emerald-500 outline-none transition-all"
              />
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-emerald-500/30 bg-[#064e3b]/20 p-4 relative overflow-hidden">
             <div className="absolute top-0 right-0 p-2 opacity-10"><Target className="w-16 h-16 text-emerald-400"/></div>
             <h4 className="text-xs uppercase tracking-widest text-emerald-500 mb-3 font-semibold flex items-center gap-2">
                 Execution Protocol
             </h4>
             
             <div className="space-y-2 relative z-10">
                 <div className="flex justify-between items-center text-sm">
                     <span className="text-slate-400">Target Entry</span>
                     <span className="font-semibold text-slate-200">₹ {entryPrice.toFixed(2)}</span>
                 </div>
                 <div className="flex justify-between items-center text-sm">
                     <span className="text-slate-400">Fail-Safe Stop Loss</span>
                     <span className="font-semibold text-rose-400">₹ {stopLoss.toFixed(2)}</span>
                 </div>
                 <div className="flex justify-between items-center bg-slate-900/50 p-2 rounded mt-2 border border-slate-700/50">
                     <span className="text-slate-300 font-medium">Safe Quantity</span>
                     <span className="font-bold text-emerald-400 text-lg flex items-center gap-2">
                        {quantity} Shares <ArrowRight className="h-4 w-4" />
                     </span>
                 </div>
                 <div className="flex justify-between items-center text-[10px] text-slate-500 pt-1 uppercase tracking-wider">
                     <span>Capital Risk: ₹ {riskAmount.toFixed(0)}</span>
                     <span>Req Leverage: {leverageRequired}x</span>
                 </div>
             </div>
        </div>

      </CardContent>
    </Card>
  );
}
