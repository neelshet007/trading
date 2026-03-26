import asyncio
import logging
from threading import Lock
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from data_fetcher import fetch_multiple, update_india_market_scan, update_market_data
from signal_engine import analyze_stock
from database import signals_collection, market_summary_collection
from market_utils import get_market_clock, ist_now

logger = logging.getLogger(__name__)
_scheduler_lock = Lock()
_scheduler = AsyncIOScheduler()

MARKETS = {
    "USA": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "SPY", "QQQ"],
    "INDIA": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "^NSEI"],
    "CRYPTO": ["BTC-USD", "ETH-USD", "SOL-USD"],
    "COMMODITIES": ["GC=F", "SI=F", "CL=F"] # Gold, Silver, Crude Oil
}


def can_run_intraday_scan(market: str) -> bool:
    clock = get_market_clock(market)
    return clock["is_open"] or market in {"CRYPTO", "COMMODITIES"}


async def process_signals(market: str, timeframe: str, interval: str, period: str):
    logger.info(f"Starting {market} {timeframe} market scan...")
    existing_summary = await market_summary_collection.find_one({"market": market}, sort=[("timestamp", -1)])
    tracked_symbols = existing_summary.get("tracked_symbols", []) if existing_summary else []
    symbols = list(dict.fromkeys([*MARKETS[market], *tracked_symbols]))
    data_map = fetch_multiple(symbols, interval=interval, period=period, market=market)
    
    all_signals = []
    bullish_count = 0
    bearish_count = 0
    
    for symbol, df in data_map.items():
        signals = analyze_stock(symbol, market, df, timeframe)
        for s in signals:
            if s["signal"] == "bullish": bullish_count += 1
            if s["signal"] == "bearish": bearish_count += 1
            all_signals.append(s)
            
    if all_signals:
        # Clear old signals for this market and timeframe
        await signals_collection.delete_many({"market": market, "timeframe": timeframe})
        await signals_collection.insert_many(all_signals)
        logger.info(f"Inserted {len(all_signals)} {market} {timeframe} signals.")

    # Update Market Summary (Per Market)
    total = bullish_count + bearish_count
    status = "Neutral"
    if total > 0:
        if bullish_count / total > 0.6: status = "Bullish"
        elif bearish_count / total > 0.6: status = "Bearish"

    updated_at = ist_now()
    top_opportunities = [
        {
            "symbol": signal["symbol"],
            "signal": signal["signal"],
            "score": signal.get("confluence_score") or signal["score"],
            "strategy": signal["strategy"],
        }
        for signal in sorted(
            all_signals,
            key=lambda item: (item.get("confluence_score") or item["score"], item["score"]),
            reverse=True,
        )[:10]
    ]
    summary = {
        "market": market,
        "status": status,
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "sector_strength": {},
        "timestamp": updated_at,
        "updated_at": updated_at,
        "timestamp_display_ist": get_market_clock(market, updated_at)["india_time"],
        "market_clock": get_market_clock(market, updated_at),
        "tracked_symbols": symbols,
        "top_opportunities": top_opportunities,
    }
    
    await market_summary_collection.replace_one({"market": market}, summary, upsert=True)
    logger.info(f"{market} Summary updated. Status: {status}")

def run_market_scan(market: str, is_intraday: bool):
    if is_intraday and not can_run_intraday_scan(market):
        logger.info("Skipping %s intraday scan because session is not open.", market)
        return

    tf = "intraday" if is_intraday else "swing"
    interval = "1m" if is_intraday else "1d"
    period = "1d" if is_intraday else "1y"
    asyncio.create_task(process_signals(market, tf, interval, period))

def start_scheduler():
    with _scheduler_lock:
        if _scheduler.running:
            logger.info("Scheduler already running. Skipping duplicate start.")
            return _scheduler

        # 60-second background polling for live market data
        _scheduler.add_job(update_market_data, "interval", seconds=60, id="market_polling", replace_existing=True, max_instances=1)

        # USA: Every 5 min intraday, daily swing
        _scheduler.add_job(lambda: run_market_scan("USA", True), 'interval', minutes=5, id="usa_intraday", replace_existing=True)
        _scheduler.add_job(lambda: run_market_scan("USA", False), 'interval', days=1, id="usa_swing", replace_existing=True)

        # INDIA: Full Nifty 500 scan every 10 minutes plus daily swing refresh
        _scheduler.add_job(update_india_market_scan, "interval", minutes=10, id="india_nifty500_scan", replace_existing=True, max_instances=1)
        _scheduler.add_job(lambda: run_market_scan("INDIA", False), 'interval', days=1, id="india_swing", replace_existing=True)

        # CRYPTO: Every 3 min (crypto is 24/7 and fast)
        _scheduler.add_job(lambda: run_market_scan("CRYPTO", True), 'interval', minutes=3, id="crypto_intraday", replace_existing=True)
        _scheduler.add_job(lambda: run_market_scan("CRYPTO", False), 'interval', days=1, id="crypto_swing", replace_existing=True)

        # COMMODITIES: Every 10 min
        _scheduler.add_job(lambda: run_market_scan("COMMODITIES", True), 'interval', minutes=10, id="commodities_intraday", replace_existing=True)
        _scheduler.add_job(lambda: run_market_scan("COMMODITIES", False), 'interval', days=1, id="commodities_swing", replace_existing=True)

        _scheduler.start()
        logger.info("Multi-market Scheduler started.")

        asyncio.create_task(update_market_data())
        asyncio.create_task(update_india_market_scan())

        # Initial scans
        for m in MARKETS.keys():
            if m != "INDIA":
                run_market_scan(m, True)
            run_market_scan(m, False)

        return _scheduler
