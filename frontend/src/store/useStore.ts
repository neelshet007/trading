import { create } from 'zustand';
import type { MarketKey, MarketSummary } from '@/lib/market';

interface AppState {
  market: MarketKey;
  setMarket: (m: MarketKey) => void;
  timeframe: 'intraday' | 'swing';
  setTimeframe: (tf: 'intraday' | 'swing') => void;
  marketSummary: MarketSummary | null;
  setMarketSummary: (summary: MarketSummary) => void;
  watchlist: { symbol: string; added_at: string }[];
  setWatchlist: (list: { symbol: string; added_at: string }[]) => void;
}

export const useStore = create<AppState>((set) => ({
  market: 'USA',
  setMarket: (m) => set({ market: m }),
  timeframe: 'intraday',
  setTimeframe: (tf) => set({ timeframe: tf }),
  marketSummary: null,
  setMarketSummary: (summary) => set({ marketSummary: summary }),
  watchlist: [],
  setWatchlist: (list) => set({ watchlist: list }),
}));
