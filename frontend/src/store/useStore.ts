import { create } from 'zustand';

interface MarketSummary {
  status: string;
  bullish_count: number;
  bearish_count: number;
  sector_strength: Record<string, string>;
  timestamp: string;
}

interface AppState {
  timeframe: 'intraday' | 'swing';
  setTimeframe: (tf: 'intraday' | 'swing') => void;
  marketSummary: MarketSummary | null;
  setMarketSummary: (summary: MarketSummary) => void;
  watchlist: { symbol: string; added_at: string }[];
  setWatchlist: (list: any[]) => void;
}

export const useStore = create<AppState>((set) => ({
  timeframe: 'intraday',
  setTimeframe: (tf) => set({ timeframe: tf }),
  marketSummary: null,
  setMarketSummary: (summary) => set({ marketSummary: summary }),
  watchlist: [],
  setWatchlist: (list) => set({ watchlist: list }),
}));
