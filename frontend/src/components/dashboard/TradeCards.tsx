'use client';

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Activity, Target, ArrowDownRight, ArrowUpRight, Crosshair } from 'lucide-react';

interface ConfluenceScore {
  trend_alignment: number;
  fvg_mitigation: number;
  idm_sweep: number;
  discount_premium: number;
  total_score: number;
}

export interface NarrativeDetail {
  reason: string;
  location: string;
  context: string;
  score_breakdown: string[];
  timeline: string[];
}

export interface SetupData {
  symbol: string;
  bias: string;
  status: string;
  entry: number;
  stop_loss: number;
  take_profit: number;
  risk_reward: number;
  confluence: ConfluenceScore;
  narrative?: NarrativeDetail;
  ob_top?: number;
  ob_bottom?: number;
}

interface TradeCardsProps {
  setup: SetupData;
}

export function TradeCards({ setup }: TradeCardsProps) {
  const isBullish = setup.bias === 'bullish';
  const neonColor = isBullish ? 'text-emerald-400' : 'text-rose-400';
  const neonBg = isBullish ? 'bg-emerald-400/10' : 'bg-rose-400/10';
  const Icon = isBullish ? ArrowUpRight : ArrowDownRight;

  return (
    <Card className="border-slate-800 bg-slate-950/80 backdrop-blur-md shadow-[0_0_15px_rgba(0,0,0,0.5)]">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
          {setup.symbol}
          <span className={`text-xs px-2 py-0.5 rounded-full ${neonBg} ${neonColor} border border-current`}>
            {setup.status}
          </span>
        </CardTitle>
        <Icon className={`h-6 w-6 ${neonColor}`} />
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 mt-2">
          <div className="space-y-1">
            <span className="text-xs uppercase tracking-wider text-slate-500">Entry</span>
            <div className={`text-2xl font-mono font-bold ${neonColor}`}>
              {setup.entry.toFixed(2)}
            </div>
          </div>
          <div className="space-y-1">
            <span className="text-xs uppercase tracking-wider text-slate-500">Risk/Reward</span>
            <div className="text-2xl font-mono font-bold text-amber-400 flex items-center gap-1">
              <Crosshair className="h-4 w-4" />
              1:{setup.risk_reward.toFixed(1)}
            </div>
          </div>
        </div>

        <div className="mt-6 flex divide-x divide-slate-800 rounded-lg border border-slate-800 bg-slate-900/50">
          <div className="flex-1 p-3 text-center">
            <div className="text-xs text-slate-500 uppercase">Stop Loss</div>
            <div className="mt-1 font-mono text-sm text-rose-400 font-semibold">{setup.stop_loss.toFixed(2)}</div>
          </div>
          <div className="flex-1 p-3 text-center">
            <div className="text-xs text-slate-500 uppercase">Take Profit</div>
            <div className="mt-1 font-mono text-sm text-emerald-400 font-semibold">{setup.take_profit.toFixed(2)}</div>
          </div>
        </div>

        {/* Confluence Score Breakdown */}
        <div className="mt-5 space-y-2">
          <div className="flex justify-between items-center text-sm">
            <span className="text-slate-400 flex items-center gap-1"><Activity className="h-4 w-4" /> Confluence Score</span>
            <span className="font-bold text-cyan-400">{setup.confluence.total_score}/10</span>
          </div>
          <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
            <div 
              className="h-full bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.8)] transition-all duration-1000" 
              style={{ width: `${(setup.confluence.total_score / 10) * 100}%` }} 
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
