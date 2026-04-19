'use client';

import React, { useEffect, useRef } from 'react';
import { CandlestickSeries, type CandlestickData, createChart, type IChartApi, type UTCTimestamp } from 'lightweight-charts';
import { SetupData } from './TradeCards';
import { Card, CardContent } from '@/components/ui/card';
import { Maximize2 } from 'lucide-react';

interface MTFChartProps {
  setup: SetupData | null;
}

export function MTFChart({ setup }: MTFChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: 'transparent' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: 'rgba(30, 41, 59, 0.5)' },
        horzLines: { color: 'rgba(30, 41, 59, 0.5)' },
      },
      crosshair: {
        mode: 0,
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981',
      downColor: '#f43f5e',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#f43f5e',
    });

    // Populate fake data just to visualize the SMC setup entry since we don't fetch historical candles yet
    if (setup) {
      const today = new Date();
      const dummyData: CandlestickData<UTCTimestamp>[] = [];
      let currentPrice = setup.trigger.entry_price * 0.95;
      
      for (let i = 20; i > 0; i--) {
        const time = new Date(today);
        time.setHours(time.getHours() - i);
        
        // Random walk
        const open = currentPrice;
        const close = currentPrice + (Math.random() - 0.5) * (setup.trigger.entry_price * 0.02);
        const high = Math.max(open, close) + Math.random() * (setup.trigger.entry_price * 0.01);
        const low = Math.min(open, close) - Math.random() * (setup.trigger.entry_price * 0.01);
        
        dummyData.push({
          time: Math.floor(time.getTime() / 1000) as UTCTimestamp,
          open, high, low, close
        });
        
        currentPrice = close;
      }
      
      // Make sure the last candle is at entry!
      const lastTime = new Date(today);
      dummyData.push({
        time: Math.floor(lastTime.getTime() / 1000) as UTCTimestamp,
        open: currentPrice,
        high: Math.max(currentPrice, setup.trigger.entry_price) * 1.001,
        low: Math.min(currentPrice, setup.trigger.entry_price) * 0.999,
        close: setup.trigger.entry_price,
      });

      series.setData(dummyData);

      // Plot the SMC levels using PriceLines
      series.createPriceLine({
        price: setup.trigger.entry_price,
        color: '#22d3ee', // Cyan
        lineWidth: 2,
        lineStyle: 2,
        axisLabelVisible: true,
        title: 'Entry',
      });
      
      series.createPriceLine({
        price: setup.trigger.stop_loss,
        color: '#f43f5e', // Rose
        lineWidth: 1,
        lineStyle: 1,
        axisLabelVisible: true,
        title: 'SL',
      });
      
      series.createPriceLine({
        price: setup.trigger.take_profit,
        color: '#10b981', // Emerald
        lineWidth: 1,
        lineStyle: 1,
        axisLabelVisible: true,
        title: 'TP',
      });
      
      // Plot Order Block (OB) Zones
      if (setup.ob_top && setup.ob_bottom) {
        series.createPriceLine({
          price: setup.ob_top,
          color: '#8b5cf6', // Violet
          lineWidth: 2,
          lineStyle: 0,
          axisLabelVisible: true,
          title: 'OB Top',
        });
        series.createPriceLine({
          price: setup.ob_bottom,
          color: '#8b5cf6', // Violet
          lineWidth: 2,
          lineStyle: 0,
          axisLabelVisible: true,
          title: 'OB Bottom',
        });
      }
    }

    chartRef.current = chart;

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);
    
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [setup]);

  if (!setup) {
    return (
      <Card className="h-full border-slate-800 bg-slate-950/80 flex items-center justify-center">
        <span className="text-slate-500 italic">Select a setup from the feed to view the chart</span>
      </Card>
    );
  }

  return (
    <Card className="h-full border-slate-800 bg-slate-950/80 overflow-hidden flex flex-col shadow-[0_0_15px_rgba(0,0,0,0.5)]">
      <div className="flex items-center justify-between p-4 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold text-white tracking-widest">{setup.symbol}</h2>
          <span className="text-xs uppercase tracking-widest text-slate-500 bg-slate-900 px-2 py-1 rounded">{setup.trigger.execution_timeframe}</span>
        </div>
        <Maximize2 className="h-4 w-4 text-slate-500 cursor-pointer hover:text-white transition-colors" />
      </div>
      <CardContent className="p-0 flex-1 relative">
        <div ref={chartContainerRef} className="absolute inset-0" />
      </CardContent>
    </Card>
  );
}
