from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from typing import List, Optional
from database import setup_db, signals_collection, market_summary_collection, watchlist_collection
from models import SignalModel, MarketSummaryModel, WatchlistModel
from scheduler import start_scheduler
from pydantic import BaseModel
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Trading Intelligence Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await setup_db()
    start_scheduler()

@app.get("/signals", response_model=List[SignalModel])
async def get_signals(timeframe: Optional[str] = "intraday", market: Optional[str] = "USA", symbol: Optional[str] = None):
    query = {"timeframe": timeframe, "market": market}
    if symbol:
        query["symbol"] = symbol.upper()
    cursor = signals_collection.find(query).sort("score", -1)
    signals = await cursor.to_list(length=100)
    return signals

@app.get("/signals/strategy/{strategy}", response_model=List[SignalModel])
async def get_signals_by_strategy(strategy: str, market: Optional[str] = "USA", timeframe: Optional[str] = "intraday"):
    cursor = signals_collection.find({"strategy": strategy, "timeframe": timeframe, "market": market}).sort("score", -1)
    signals = await cursor.to_list(length=100)
    return signals

@app.get("/stock/{symbol}", response_model=List[SignalModel])
async def get_stock_detail(symbol: str):
    cursor = signals_collection.find({"symbol": symbol.upper()}).sort("timestamp", -1)
    signals = await cursor.to_list(length=20)
    return signals

@app.get("/market-summary")
async def get_market_summary(market: Optional[str] = "USA"):
    summary = await market_summary_collection.find_one({"market": market}, sort=[("timestamp", -1)])
    if summary:
        summary["_id"] = str(summary["_id"])
        return summary
    return {"market": market, "status": "Unknown", "bullish_count": 0, "bearish_count": 0}

class WatchlistAdd(BaseModel):
    symbol: str

@app.get("/watchlist", response_model=List[WatchlistModel])
async def get_watchlist():
    cursor = watchlist_collection.find().sort("added_at", -1)
    return await cursor.to_list(length=100)

@app.post("/watchlist")
async def add_to_watchlist(item: WatchlistAdd):
    # check if exists
    existing = await watchlist_collection.find_one({"symbol": item.symbol.upper()})
    if existing:
        return {"msg": "Already in watchlist"}
    new_item = {"symbol": item.symbol.upper(), "added_at": __import__("datetime").datetime.utcnow()}
    await watchlist_collection.insert_one(new_item)
    return {"msg": "Added to watchlist"}

@app.get("/search/{query}")
def search_ticker(query: str):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=5&newsCount=0"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            quotes = data.get("quotes", [])
            return [{"symbol": q["symbol"], "name": q.get("shortname", q.get("longname", q["symbol"]))} for q in quotes if "symbol" in q]
    except Exception as e:
        logging.error(f"Search API error: {e}")
    return []

@app.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str):
    await watchlist_collection.delete_one({"symbol": symbol.upper()})
    return {"msg": "Removed from watchlist"}
