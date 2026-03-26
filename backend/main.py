import logging
from typing import List, Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from data_fetcher import validate_symbol
from database import market_summary_collection, setup_db, signals_collection, watchlist_collection
from market_utils import ensure_utc, get_market_clock, normalize_symbol, utc_now
from models import MarketSummaryModel, SignalModel, WatchlistModel
from scheduler import start_scheduler
from signal_engine import analyze_stock

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Trading Intelligence Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _infer_market_from_symbol(symbol: str) -> str:
    upper = symbol.upper()
    if upper.endswith(".NS") or upper.startswith("^NSE"):
        return "INDIA"
    if "-USD" in upper:
        return "CRYPTO"
    return "USA"


def _market_summary_default(market: str):
    now_utc = utc_now()
    return {
        "market": market,
        "status": "Unknown",
        "bullish_count": 0,
        "bearish_count": 0,
        "sector_strength": {},
        "timestamp": now_utc,
        "timestamp_display_ist": get_market_clock(market, now_utc)["india_time"],
        "market_clock": get_market_clock(market, now_utc),
    }


def _intraday_params(timeframe: str) -> tuple[str, str]:
    return ("1d", "1y") if timeframe == "swing" else ("5m", "1mo")


async def _latest_or_live_signal(symbol: str, market: str, timeframe: str = "swing"):
    normalized_symbol = normalize_symbol(symbol, market if market == "INDIA" else None)
    latest_signal = await signals_collection.find_one(
        {"symbol": normalized_symbol},
        sort=[("timestamp", -1), ("confluence_score", -1), ("score", -1)],
    )
    if latest_signal:
        return latest_signal

    interval, period = _intraday_params(timeframe)
    resolved_symbol, df = validate_symbol(normalized_symbol, market=market, interval=interval, period=period)
    if not resolved_symbol or df.empty:
        return None
    generated = analyze_stock(resolved_symbol, market, df, timeframe)
    return generated[0] if generated else None


@app.on_event("startup")
async def startup_event():
    await setup_db()
    start_scheduler()


@app.get("/signals", response_model=List[SignalModel])
async def get_signals(timeframe: Optional[str] = "intraday", market: Optional[str] = "USA", symbol: Optional[str] = None):
    query = {"timeframe": timeframe, "market": market}
    if symbol:
        query["symbol"] = normalize_symbol(symbol, market if market == "INDIA" else None)
    cursor = signals_collection.find(query).sort([("confluence_score", -1), ("score", -1), ("timestamp", -1)])
    return await cursor.to_list(length=100)


@app.get("/signals/strategy/{strategy}", response_model=List[SignalModel])
async def get_signals_by_strategy(strategy: str, market: Optional[str] = "USA", timeframe: Optional[str] = "intraday"):
    cursor = signals_collection.find({"strategy": strategy, "timeframe": timeframe, "market": market}).sort(
        [("confluence_score", -1), ("score", -1), ("timestamp", -1)]
    )
    return await cursor.to_list(length=100)


@app.get("/stock/{symbol}", response_model=List[SignalModel])
async def get_stock_detail(symbol: str, market: Optional[str] = None):
    inferred_market = market or _infer_market_from_symbol(symbol)
    normalized_symbol = normalize_symbol(symbol, inferred_market if inferred_market == "INDIA" else None)
    cursor = signals_collection.find({"symbol": normalized_symbol}).sort([("timestamp", -1), ("confluence_score", -1), ("score", -1)])
    signals = await cursor.to_list(length=20)
    if signals:
        return signals

    interval, period = _intraday_params("swing")
    resolved_symbol, df = validate_symbol(normalized_symbol, market=inferred_market, interval=interval, period=period)
    if not resolved_symbol or df.empty:
        return []
    return analyze_stock(resolved_symbol, inferred_market, df, "swing")


@app.get("/stock-analysis/{symbol}", response_model=List[SignalModel])
async def get_stock_analysis(symbol: str, market: Optional[str] = None, timeframe: Optional[str] = "swing"):
    inferred_market = market or _infer_market_from_symbol(symbol)
    normalized_symbol = normalize_symbol(symbol, inferred_market if inferred_market == "INDIA" else None)
    interval, period = _intraday_params(timeframe or "swing")
    resolved_symbol, df = validate_symbol(normalized_symbol, market=inferred_market, interval=interval, period=period)
    if not resolved_symbol or df.empty:
        raise HTTPException(status_code=404, detail="Unable to fetch data for symbol")
    return analyze_stock(resolved_symbol, inferred_market, df, timeframe or "swing")


@app.get("/market-summary", response_model=MarketSummaryModel)
async def get_market_summary(market: Optional[str] = "USA"):
    summary = await market_summary_collection.find_one({"market": market}, sort=[("timestamp", -1)])
    if summary:
        summary["_id"] = str(summary["_id"])
        return summary
    return _market_summary_default(market or "USA")


class WatchlistAdd(BaseModel):
    symbol: str


@app.get("/watchlist", response_model=List[WatchlistModel])
async def get_watchlist():
    cursor = watchlist_collection.find().sort("added_at", -1)
    return await cursor.to_list(length=100)


@app.post("/watchlist")
async def add_to_watchlist(item: WatchlistAdd):
    inferred_market = _infer_market_from_symbol(item.symbol)
    normalized_symbol = normalize_symbol(item.symbol, inferred_market if inferred_market == "INDIA" else None)
    existing = await watchlist_collection.find_one({"symbol": normalized_symbol})
    if existing:
        return {"msg": "Already in watchlist"}
    new_item = {"symbol": normalized_symbol, "added_at": ensure_utc()}
    await watchlist_collection.insert_one(new_item)
    return {"msg": "Added to watchlist"}


@app.get("/search/{query}")
async def search_ticker(query: str):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=5&newsCount=0"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            quotes = data.get("quotes", [])
            results = []
            for quote in quotes:
                symbol = quote.get("symbol")
                if not symbol:
                    continue
                inferred_market = _infer_market_from_symbol(symbol)
                normalized_symbol = normalize_symbol(symbol, inferred_market if inferred_market == "INDIA" else None)
                latest_signal = await _latest_or_live_signal(normalized_symbol, inferred_market)
                results.append(
                    {
                        "symbol": normalized_symbol,
                        "name": quote.get("shortname", quote.get("longname", normalized_symbol)),
                        "market": inferred_market,
                        "signal": latest_signal["signal"] if latest_signal else "neutral",
                        "analysis": latest_signal.get("analysis_summary") if latest_signal else None,
                        "categories": latest_signal.get("categories", []) if latest_signal else [],
                        "rating": latest_signal.get("analysis_summary", {}).get("rating", "N/A") if latest_signal else "N/A",
                    }
                )
            return results
    except Exception as exc:
        logging.error("Search API error: %s", exc)
    return []


@app.get("/market-clock")
async def get_market_clock_endpoint(market: Optional[str] = "USA"):
    return get_market_clock(market or "USA")


@app.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str):
    await watchlist_collection.delete_one({"symbol": normalize_symbol(symbol, "INDIA" if symbol.upper().endswith(".NS") else None)})
    return {"msg": "Removed from watchlist"}
