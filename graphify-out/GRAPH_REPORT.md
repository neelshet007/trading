# Graph Report - C:\Web Devlopment\NextJs\finance\trading-platform  (2026-04-20)

## Corpus Check
- 48 files · ~42,194 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 248 nodes · 441 edges · 34 communities detected
- Extraction: 74% EXTRACTED · 26% INFERRED · 0% AMBIGUOUS · INFERRED: 116 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]

## God Nodes (most connected - your core abstractions)
1. `build_setup()` - 30 edges
2. `TimeframeBundle` - 17 edges
3. `utc_now()` - 11 edges
4. `ensure_utc()` - 11 edges
5. `normalize_symbol()` - 11 edges
6. `get_market_clock()` - 10 edges
7. `run_smc_backtest()` - 9 edges
8. `LazyScannerManager` - 9 edges
9. `_build_forensic_side()` - 8 edges
10. `build_data_pulse()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `validate_symbol()` --calls--> `candidate_symbols()`  [INFERRED]
  C:\Web Devlopment\NextJs\finance\trading-platform\backend\data_fetcher.py → C:\Web Devlopment\NextJs\finance\trading-platform\backend\market_utils.py
- `run_smc_backtest()` --calls--> `get_backtest_stats()`  [INFERRED]
  C:\Web Devlopment\NextJs\finance\trading-platform\backend\backtest.py → C:\Web Devlopment\NextJs\finance\trading-platform\backend\main.py
- `db_updated_at()` --calls--> `_build_quote_snapshot()`  [INFERRED]
  C:\Web Devlopment\NextJs\finance\trading-platform\backend\database.py → C:\Web Devlopment\NextJs\finance\trading-platform\backend\data_fetcher.py
- `db_updated_at()` --calls--> `_build_india_metric()`  [INFERRED]
  C:\Web Devlopment\NextJs\finance\trading-platform\backend\database.py → C:\Web Devlopment\NextJs\finance\trading-platform\backend\data_fetcher.py
- `_collect_market_quotes()` --calls--> `normalize_symbol()`  [INFERRED]
  C:\Web Devlopment\NextJs\finance\trading-platform\backend\data_fetcher.py → C:\Web Devlopment\NextJs\finance\trading-platform\backend\market_utils.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.11
Nodes (25): _asset_pulse(), _beta_headwind(), build_data_pulse(), _item_value(), run_scan(), LazyScannerManager, SegmentScanState, add_to_watchlist() (+17 more)

### Community 1 - "Community 1"
Cohesion: 0.17
Nodes (28): BaseModel, run_forensic_scan(), TimeframeBundle, WatchlistAdd, AnalysisSummary, MarketSummaryModel, ProbabilityInsight, ScoreResponse (+20 more)

### Community 2 - "Community 2"
Cohesion: 0.17
Nodes (25): _atr(), _build_forensic_side(), _build_hitl(), build_setup(), _cvd_divergence(), _detect_choch_and_displacement(), _entry_model(), fetch_symbol_bundle() (+17 more)

### Community 3 - "Community 3"
Cohesion: 0.09
Nodes (11): buildApiUrl(), fetcher(), formatDisplayDate(), isDataPulseStale(), activate(), formatDisplayTime(), getStatusBadgeClasses(), handleScan() (+3 more)

### Community 4 - "Community 4"
Cohesion: 0.19
Nodes (20): _build_india_metric(), _build_quote_snapshot(), _clean_history(), _collect_market_quotes(), _download_batch_history(), _download_csv_with_session(), _download_history(), _extract_symbol_frame() (+12 more)

### Community 5 - "Community 5"
Cohesion: 0.18
Nodes (13): update_india_market_scan(), update_market_data(), db_updated_at(), setup_db(), get_market_clock_endpoint(), startup_event(), get_market_clock(), ist_now() (+5 more)

### Community 6 - "Community 6"
Cohesion: 0.27
Nodes (12): add_indicators(), _compute_stats(), _download(), fib_pos(), generate_excel_report(), SMC + Technical Confluence Blind Backtester Strategy:   SMC Core   : Liquidity, Return (score, reasons). Max score = 8., Return (score, reasons). Max score = 8. (+4 more)

### Community 7 - "Community 7"
Cohesion: 0.33
Nodes (8): add_indicators(), _add_pattern_scanners(), analyze_stock(), _build_analysis_summary(), _build_signal(), detect_patterns(), _probability_label(), _safe_ratio()

### Community 8 - "Community 8"
Cohesion: 0.29
Nodes (0): 

### Community 9 - "Community 9"
Cohesion: 0.33
Nodes (2): MarketSegmentPage(), getSegmentDefinition()

### Community 10 - "Community 10"
Cohesion: 0.4
Nodes (0): 

### Community 11 - "Community 11"
Cohesion: 0.4
Nodes (0): 

### Community 12 - "Community 12"
Cohesion: 0.5
Nodes (2): Badge(), cn()

### Community 13 - "Community 13"
Cohesion: 0.67
Nodes (0): 

### Community 14 - "Community 14"
Cohesion: 0.67
Nodes (0): 

### Community 15 - "Community 15"
Cohesion: 0.67
Nodes (0): 

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (0): 

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (0): 

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (0): 

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (0): 

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (0): 

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (0): 

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (0): 

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (0): 

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (0): 

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (0): 

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (0): 

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (0): 

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (0): 

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (0): 

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (0): 

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (0): 

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (0): 

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **3 isolated node(s):** `SMC + Technical Confluence Blind Backtester Strategy:   SMC Core   : Liquidity`, `Return (score, reasons). Max score = 8.`, `Return (score, reasons). Max score = 8.`
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 16`** (2 nodes): `layout.tsx`, `RootLayout()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (2 nodes): `page.tsx`, `WatchlistPage()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (2 nodes): `SignalCard.tsx`, `SignalCard()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (2 nodes): `MTFChart.tsx`, `MTFChart()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (2 nodes): `TradeCards.tsx`, `TradeCards()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (2 nodes): `TradeDetailsModal.tsx`, `TradeDetailsModal()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (2 nodes): `cn()`, `button.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (2 nodes): `tabs.tsx`, `cn()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (2 nodes): `useInterval.ts`, `useInterval()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `app.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `start-dev.ps1`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `eslint.config.mjs`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `next-env.d.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `next.config.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `postcss.config.mjs`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `PositionCalculator.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `TerminalFeed.tsx`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `useStore.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `start_segment_scanner()` connect `Community 0` to `Community 3`?**
  _High betweenness centrality (0.143) - this node is a cross-community bridge._
- **Why does `activate()` connect `Community 3` to `Community 0`?**
  _High betweenness centrality (0.137) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `build_setup()` (e.g. with `ensure_utc()` and `utc_now()`) actually correct?**
  _`build_setup()` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `TimeframeBundle` (e.g. with `AssetPulse` and `ChecklistDetails`) actually correct?**
  _`TimeframeBundle` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `utc_now()` (e.g. with `_asset_pulse()` and `build_data_pulse()`) actually correct?**
  _`utc_now()` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `ensure_utc()` (e.g. with `_silver_bullet_window()` and `_asset_pulse()`) actually correct?**
  _`ensure_utc()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `SMC + Technical Confluence Blind Backtester Strategy:   SMC Core   : Liquidity`, `Return (score, reasons). Max score = 8.`, `Return (score, reasons). Max score = 8.` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._