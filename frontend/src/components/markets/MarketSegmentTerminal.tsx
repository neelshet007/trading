'use client';

import { useCallback, useEffect, useState } from 'react';
import { Activity, Clock3, Radar } from 'lucide-react';

import { Sidebar } from '@/components/Sidebar';
import { SignalCard } from '@/components/SignalCard';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useInterval } from '@/hooks/useInterval';
import { buildApiUrl } from '@/lib/api';
import { formatDisplayDate, formatDisplayTime, getStatusBadgeClasses, type SegmentScanResponse } from '@/lib/market';
import { getSegmentDefinition, type MarketSegment } from '@/lib/segments';

interface MarketSegmentTerminalProps {
  segment: MarketSegment;
}

export function MarketSegmentTerminal({ segment }: MarketSegmentTerminalProps) {
  const definition = getSegmentDefinition(segment);
  const [data, setData] = useState<SegmentScanResponse | null>(null);
  const [activating, setActivating] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const activate = async () => {
      if (!definition) return;
      setActivating(true);
      setError(null);

      try {
        const response = await fetch(buildApiUrl(`/api/v1/scanner/start?market=${definition.slug}`), {
          method: 'POST',
        });
        if (!response.ok) throw new Error('Scanner activation failed');
        const payload = await response.json() as SegmentScanResponse;
        if (!cancelled) setData(payload);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Scanner activation failed');
      } finally {
        if (!cancelled) setActivating(false);
      }
    };

    void activate();
    return () => {
      cancelled = true;
    };
  }, [definition]);

  const pollScan = useCallback(async () => {
    if (!definition) return;
    setRefreshing(true);
    try {
      const response = await fetch(buildApiUrl(`/scan/${definition.slug}`));
      if (!response.ok) throw new Error('Segment scan failed');
      const payload = await response.json() as SegmentScanResponse;
      setData(payload);
      setError(payload.last_error || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Segment scan failed');
    } finally {
      setRefreshing(false);
    }
  }, [definition]);

  useEffect(() => {
    if (activating || !definition) return;

    const load = async () => {
      await pollScan();
    };

    void load();
  }, [activating, definition, pollScan]);

  useInterval(() => {
    void pollScan();
  }, data?.poll_interval_seconds ? data.poll_interval_seconds * 1000 : null);

  if (!definition) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 text-slate-300">
        Unknown market segment.
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[radial-gradient(circle_at_top,rgba(12,74,110,0.12),transparent_28%),linear-gradient(180deg,#020617_0%,#07111f_45%,#020617_100%)] text-slate-200">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mb-8 flex flex-col gap-4 border-b border-slate-800 pb-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <span className="rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1 text-xs font-semibold tracking-[0.28em] text-slate-300">
                {definition.icon}
              </span>
              <Badge className={getStatusBadgeClasses(data?.market_clock?.status_color)}>
                {data?.market_clock?.status_text || 'Scanner Activating'}
              </Badge>
              {(activating || refreshing) && (
                <Badge variant="outline" className="border-cyan-500/40 text-cyan-300">
                  Scanner Activating...
                </Badge>
              )}
            </div>
            <div>
              <h1 className="text-4xl font-bold tracking-tight text-white">{definition.label}</h1>
              <p className="mt-2 max-w-3xl text-slate-400">{definition.headline}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500">Scanner Focus</div>
              <div className="mt-2 text-sm text-slate-200">{data?.scanner_focus || 'Preparing segment scanner...'}</div>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500">Default Mode</div>
              <div className="mt-2 text-sm text-slate-200">{data?.default_timeframe || 'intraday'} / {data?.zoom_resolution || '5m'}</div>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500">Execution Lens</div>
              <div className="mt-2 text-sm text-slate-200">{data?.margin_profile || 'Segment specific risk model'}</div>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-6 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            {error}
          </div>
        )}

        <div className="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-4">
          <Card className="border-slate-800 bg-slate-950/60 xl:col-span-1">
            <CardHeader>
              <CardTitle className="text-white">Scanner Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-slate-300">
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                <div className="mb-2 flex items-center gap-2 text-slate-500"><Radar className="h-4 w-4" /> Runtime</div>
                <div className="text-white">{data?.status || 'activating'}</div>
                <div className="mt-2 text-xs text-slate-500">Hibernates after {data?.activation_ttl_seconds || 300}s without frontend polling.</div>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                <div className="mb-2 flex items-center gap-2 text-slate-500"><Clock3 className="h-4 w-4" /> Clock</div>
                <div>UTC: {data?.market_clock?.local_time || '--:--'} {data?.market_clock?.local_label || ''}</div>
                <div>IST mirror: {data?.market_clock?.india_time || '--:--'} IST</div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-slate-950/60 xl:col-span-3">
            <CardHeader>
              <CardTitle className="flex items-center justify-between gap-3 text-white">
                <span>Live Segment Opportunities</span>
                <Badge variant="outline" className="border-slate-700 text-slate-300">
                  {data?.opportunities?.length || 0} ranked
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {activating ? (
                <div className="flex min-h-56 items-center justify-center rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 text-slate-400">
                  <div className="text-center">
                    <Activity className="mx-auto mb-3 h-10 w-10 animate-spin text-cyan-400" />
                    <p>Scanner Activating...</p>
                  </div>
                </div>
              ) : data?.opportunities?.length ? (
                <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
                  {data.opportunities.map((signal) => (
                    <SignalCard key={`${segment}-${signal.symbol}-${signal.trigger.entry_model}-${signal.timestamp}`} signal={signal} />
                  ))}
                </div>
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 py-14 text-center text-slate-400">
                  No setups are active for this segment yet. Keep the route open and the scanner will refresh on its polling cycle.
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <Card className="border-slate-800 bg-slate-950/50">
          <CardContent className="flex flex-col gap-2 p-5 text-sm text-slate-400 md:flex-row md:items-center md:justify-between">
            <div>
              Last scan: {formatDisplayTime(data?.last_completed)} IST on {formatDisplayDate(data?.last_completed)}
            </div>
            <div>
              Polling every {data?.poll_interval_seconds || '--'} seconds for the active segment only.
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
