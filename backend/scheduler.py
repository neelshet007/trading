import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from data_fetcher import fetch_multiple
from signal_engine import analyze_stock
from database import signals_collection, market_summary_collection
from datetime import datetime, time
import pytz

logger = logging.getLogger(__name__)

IST = pytz.timezone('Asia/Kolkata')

def is_indian_market_open():
    now_ist = datetime.now(IST)
    # Market open: Mon-Fri, 9:15 AM - 3:30 PM
    if now_ist.weekday() >= 5: # Saturday/Sunday
        return False
    
    start_time = time(9, 15)
    end_time = time(15, 30)
    return start_time <= now_ist.time() <= end_time

MARKETS = {
    "USA": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "SPY", "QQQ"],
    "INDIA": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "^NSEI"],
    "CRYPTO": ["BTC-USD", "ETH-USD", "SOL-USD"],
    "COMMODITIES": ["GC=F", "SI=F", "CL=F"] # Gold, Silver, Crude Oil
}

async def process_signals(market: str, timeframe: str, interval: str, period: str):
    logger.info(f"Starting {market} {timeframe} market scan...")
    symbols = MARKETS[market]
    data_map = fetch_multiple(symbols, interval=interval, period=period)
    
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
        
    summary = {
        "market": market,
        "status": status,
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "timestamp": datetime.utcnow()
    }
    
    await market_summary_collection.delete_many({"market": market})
    await market_summary_collection.insert_one(summary)
    logger.info(f"{market} Summary updated. Status: {status}")

def run_market_scan(market: str, is_intraday: bool):
    if market == "INDIA" and is_intraday and not is_indian_market_open():
        logger.info("Skipping Indian Intraday scan (Market Closed).")
        return

    tf = "intraday" if is_intraday else "swing"
    interval = "5m" if is_intraday else "1d"
    period = "1mo" if is_intraday else "1y"
    asyncio.create_task(process_signals(market, tf, interval, period))

def start_scheduler():
    scheduler = AsyncIOScheduler()
    
    # USA: Every 5 min intraday, daily swing
    scheduler.add_job(lambda: run_market_scan("USA", True), 'interval', minutes=5)
    scheduler.add_job(lambda: run_market_scan("USA", False), 'interval', days=1)
    
    # INDIA: Every 5 min intraday, daily swing
    scheduler.add_job(lambda: run_market_scan("INDIA", True), 'interval', minutes=5)
    scheduler.add_job(lambda: run_market_scan("INDIA", False), 'interval', days=1)
    
    # CRYPTO: Every 3 min (crypto is 24/7 and fast)
    scheduler.add_job(lambda: run_market_scan("CRYPTO", True), 'interval', minutes=3)
    scheduler.add_job(lambda: run_market_scan("CRYPTO", False), 'interval', days=1)
    
    # COMMODITIES: Every 10 min
    scheduler.add_job(lambda: run_market_scan("COMMODITIES", True), 'interval', minutes=10)
    scheduler.add_job(lambda: run_market_scan("COMMODITIES", False), 'interval', days=1)
    
    scheduler.start()
    logger.info("Multi-market Scheduler started.")
    
    # Initial scans
    for m in MARKETS.keys():
        run_market_scan(m, True)
        run_market_scan(m, False)
