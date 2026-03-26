import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from data_fetcher import fetch_multiple
from signal_engine import analyze_stock
from database import signals_collection, market_summary_collection
from datetime import datetime

logger = logging.getLogger(__name__)

# Pre-defined list of symbols for scanning
SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "SPY", "QQQ",
    "BTC-USD", "ETH-USD", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS"
]

async def process_signals(timeframe: str, interval: str, period: str):
    logger.info(f"Starting {timeframe} market scan...")
    data_map = fetch_multiple(SYMBOLS, interval=interval, period=period)
    
    all_signals = []
    bullish_count = 0
    bearish_count = 0
    
    for symbol, df in data_map.items():
        signals = analyze_stock(symbol, df, timeframe)
        for s in signals:
            if s["signal"] == "bullish": bullish_count += 1
            if s["signal"] == "bearish": bearish_count += 1
            all_signals.append(s)
            
    if all_signals:
        # Clear old signals for this timeframe and insert new ones
        await signals_collection.delete_many({"timeframe": timeframe})
        await signals_collection.insert_many(all_signals)
        logger.info(f"Inserted {len(all_signals)} {timeframe} signals.")

    # Update Market Summary
    total = bullish_count + bearish_count
    status = "Neutral"
    if total > 0:
        if bullish_count / total > 0.6: status = "Bullish"
        elif bearish_count / total > 0.6: status = "Bearish"
        
    summary = {
        "status": status,
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "sector_strength": {"Tech": "Bullish", "Finance": "Neutral", "Crypto": "Mixed"}, # Mocked sector str
        "timestamp": datetime.utcnow()
    }
    
    await market_summary_collection.delete_many({})
    await market_summary_collection.insert_one(summary)
    logger.info(f"Market Summary updated. Status: {status}")

def run_intraday_scan():
    asyncio.create_task(process_signals("intraday", "5m", "1mo"))
    
def run_swing_scan():
    asyncio.create_task(process_signals("swing", "1d", "1y"))

def start_scheduler():
    scheduler = AsyncIOScheduler()
    # Intraday every 5 minutes
    scheduler.add_job(run_intraday_scan, 'interval', minutes=5)
    # Swing every day
    scheduler.add_job(run_swing_scan, 'interval', days=1)
    
    scheduler.start()
    logger.info("Scheduler started.")
    
    # Run an initial scan
    run_intraday_scan()
    run_swing_scan()
