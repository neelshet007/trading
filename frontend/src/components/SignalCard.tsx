import Link from 'next/link';
import { Badge } from './ui/badge';
import { Card, CardContent } from './ui/card';
import { ArrowRight, Target, ShieldAlert, Activity } from 'lucide-react';

export function SignalCard({ signal }: { signal: any }) {
  const isBullish = signal.signal === 'bullish';
  return (
    <Card className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-colors mb-4 cursor-pointer">
      <Link href={`/stock/${signal.symbol}`} className="block h-full">
        <CardContent className="p-5">
          <div className="flex justify-between items-start mb-4">
            <div>
              <div className="flex items-center gap-3">
                <h3 className="text-xl font-bold text-white">{signal.symbol}</h3>
                <Badge className={isBullish ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}>
                  {isBullish ? 'Bullish' : 'Bearish'}
                </Badge>
              </div>
              <p className="text-sm text-slate-400 mt-1">{signal.strategy} | {signal.timeframe}</p>
            </div>
            <div className={`text-xl font-bold ${signal.score >= 8 ? 'text-emerald-400' : 'text-slate-300'}`}>
              {signal.score.toFixed(1)}/10
            </div>
          </div>
          
          <div className="flex flex-wrap gap-2 mb-4">
            {signal.reasons.map((r: string, i: number) => (
              <Badge key={i} variant="outline" className="border-slate-700 text-slate-300">
                {r}
              </Badge>
            ))}
          </div>
          
          <div className="flex items-center gap-6 mt-4 pt-4 border-t border-slate-800 text-sm">
            <div className="flex items-center gap-1 text-slate-300">
              <Activity className="w-4 h-4 text-slate-500" /> Entry: {signal.entry_zone}
            </div>
            <div className="flex items-center gap-1 text-slate-300">
              <ShieldAlert className="w-4 h-4 text-slate-500" /> SL: {signal.stop_loss}
            </div>
            <div className="flex items-center gap-1 text-slate-300">
              <Target className="w-4 h-4 text-slate-500" /> Target: {signal.target}
            </div>
            <ArrowRight className="w-4 h-4 ml-auto text-slate-500 group-hover:text-emerald-400 transition-colors" />
          </div>
        </CardContent>
      </Link>
    </Card>
  );
}
