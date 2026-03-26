import logging
import re
from datetime import timedelta
from typing import Any, Dict, List, Optional

import requests
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from data_fetcher import refresh_indian_ticker_universe, validate_symbol
from database import market_summary_collection, setup_db, signals_collection, ticker_universe_collection, watchlist_collection
from indicators import add_indicators
from market_utils import ensure_utc, get_market_clock, ist_now, normalize_symbol, utc_now
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
    if upper.endswith(".NS") or upper.endswith(".BO") or upper.startswith("^NSE") or upper.startswith("^BSE"):
        return "INDIA"
    if "-USD" in upper:
        return "CRYPTO"
    return "USA"


def _market_summary_default(market: str):
    now_ist = ist_now()
    return {
        "market": market,
        "status": "Unknown",
        "bullish_count": 0,
        "bearish_count": 0,
        "sector_strength": {},
        "timestamp": now_ist,
        "updated_at": now_ist,
        "timestamp_display_ist": get_market_clock(market, now_ist)["india_time"],
        "market_clock": get_market_clock(market, now_ist),
        "tracked_symbols": [],
        "top_opportunities": [],
    }


def _intraday_params(timeframe: str) -> tuple[str, str]:
    return ("1d", "1y") if timeframe == "swing" else ("1m", "1d")


def _signal_sort_order() -> list[tuple[str, int]]:
    return [("confluence_score", -1), ("score", -1), ("timestamp", -1)]


def _build_live_detail(resolved_symbol: str, market: str, df: pd.DataFrame) -> Dict[str, Any]:
    enriched = add_indicators(df)
    latest = enriched.iloc[-1] if not enriched.empty else df.iloc[-1]
    previous_close = float(df["Close"].iloc[-2]) if len(df) > 1 else float(df["Close"].iloc[-1])
    current_price = float(df["Close"].iloc[-1])
    change_pct = ((current_price - previous_close) / previous_close * 100) if previous_close else 0.0
    updated_at = ist_now()
    return {
        "symbol": resolved_symbol,
        "market": market,
        "price": round(current_price, 2),
        "change_percent": round(change_pct, 2),
        "rsi": round(float(latest["RSI"]), 2) if "RSI" in latest and pd.notna(latest["RSI"]) else None,
        "volume": int(float(df["Volume"].iloc[-1])) if "Volume" in df.columns and pd.notna(df["Volume"].iloc[-1]) else None,
        "updated_at": updated_at,
    }


def _build_setup_summary(rsi: float | None, volume_surge_ratio: float, price: float, sma_50: float | None, sma_200: float | None) -> str:
    if rsi is not None and rsi < 30 and volume_surge_ratio >= 2:
        return "Strong Oversold Setup with high conviction volume."
    if rsi is not None and rsi > 70 and volume_surge_ratio >= 2:
        return "Strong Overbought Setup with heavy volume participation."
    if sma_50 is not None and sma_200 is not None and price > sma_50 > sma_200:
        return "Bullish trend structure with price holding above the 50 and 200 SMA."
    if sma_50 is not None and sma_200 is not None and price < sma_50 < sma_200:
        return "Bearish trend structure with price trading below the 50 and 200 SMA."
    if volume_surge_ratio >= 2:
        return "Volume-led setup forming with unusual participation."
    if rsi is not None and rsi < 30:
        return "Oversold setup forming with rebound potential."
    if rsi is not None and rsi > 70:
        return "Overbought setup forming with exhaustion risk."
    return "Neutral setup. Momentum and volume are not showing a high-conviction edge yet."


def _build_on_demand_metrics(resolved_symbol: str, market: str, df: pd.DataFrame) -> Dict[str, Any]:
    enriched = add_indicators(df.copy())
    latest = enriched.iloc[-1] if not enriched.empty else df.iloc[-1]
    previous_close = float(df["Close"].iloc[-2]) if len(df) > 1 else float(df["Close"].iloc[-1])
    price = float(df["Close"].iloc[-1])
    change_pct = ((price - previous_close) / previous_close * 100) if previous_close else 0.0
    updated_at = ist_now()
    avg_20_day_volume = float(df["Volume"].tail(20).mean()) if "Volume" in df.columns else 0.0
    volume = float(df["Volume"].iloc[-1]) if "Volume" in df.columns and pd.notna(df["Volume"].iloc[-1]) else 0.0
    volume_surge_ratio = round(volume / avg_20_day_volume, 2) if avg_20_day_volume else 0.0
    sma_50 = float(df["Close"].rolling(window=50).mean().iloc[-1]) if len(df) >= 50 else None
    sma_200 = float(df["Close"].rolling(window=200).mean().iloc[-1]) if len(df) >= 200 else None
    rsi = round(float(latest["RSI"]), 2) if "RSI" in latest and pd.notna(latest["RSI"]) else None
    setup_summary = _build_setup_summary(rsi, volume_surge_ratio, price, sma_50, sma_200)

    return {
        "symbol": resolved_symbol,
        "market": market,
        "price": round(price, 2),
        "change_percent": round(change_pct, 2),
        "rsi": rsi,
        "sma_50": round(sma_50, 2) if sma_50 is not None and pd.notna(sma_50) else None,
        "sma_200": round(sma_200, 2) if sma_200 is not None and pd.notna(sma_200) else None,
        "avg_20_day_volume": int(avg_20_day_volume) if avg_20_day_volume else 0,
        "volume": int(volume) if volume else 0,
        "volume_surge_ratio": volume_surge_ratio,
        "updated_at": updated_at,
        "setup_summary": setup_summary,
    }


def _is_fresh(timestamp_value: Any, max_age_minutes: int = 5) -> bool:
    if not timestamp_value:
        return False
    try:
        timestamp = ensure_utc(timestamp_value)
    except Exception:
        return False
    return (utc_now() - timestamp) <= timedelta(minutes=max_age_minutes)


async def _cache_symbol_for_market(market: str, symbol: str):
    defaults = _market_summary_default(market)
    defaults.pop("updated_at", None)
    defaults.pop("timestamp", None)
    defaults.pop("timestamp_display_ist", None)
    defaults.pop("market_clock", None)
    defaults.pop("tracked_symbols", None)
    now_ist = ist_now()
    await market_summary_collection.update_one(
        {"market": market},
        {
            "$setOnInsert": defaults,
            "$set": {
                "updated_at": now_ist,
                "timestamp": now_ist,
                "timestamp_display_ist": get_market_clock(market, now_ist)["india_time"],
                "market_clock": get_market_clock(market, now_ist),
            },
            "$addToSet": {"tracked_symbols": symbol},
        },
        upsert=True,
    )


async def _cache_live_signals(symbol: str, market: str, signals: List[Dict[str, Any]], detail: Dict[str, Any]):
    if not signals:
        return
    await signals_collection.delete_many({"symbol": symbol, "market": market, "timeframe": "intraday"})
    updated_at = detail["updated_at"]
    payload = [{**signal, "updated_at": updated_at} for signal in signals]
    await signals_collection.insert_many(payload)


async def _cache_live_detail(symbol: str, market: str, detail: Dict[str, Any]):
    now_ist = detail["updated_at"]
    await market_summary_collection.update_one(
        {"market": market},
        {
            "$set": {
                "updated_at": now_ist,
                "timestamp": now_ist,
                "timestamp_display_ist": get_market_clock(market, now_ist)["india_time"],
                "market_clock": get_market_clock(market, now_ist),
                f"on_demand_profiles.{symbol}": detail,
            },
            "$addToSet": {"tracked_symbols": symbol},
        },
        upsert=True,
    )


async def _resolve_live_stock(symbol: str, market: str, timeframe: str = "intraday") -> Optional[Dict[str, Any]]:
    normalized_symbol = normalize_symbol(symbol, market if market == "INDIA" else None)
    interval, period = _intraday_params(timeframe)
    resolved_symbol, df = validate_symbol(normalized_symbol, market=market, interval=interval, period=period)
    if not resolved_symbol or df.empty:
        return None

    detail = _build_live_detail(resolved_symbol, market, df)
    generated = analyze_stock(resolved_symbol, market, df, timeframe)
    await _cache_symbol_for_market(market, resolved_symbol)
    await _cache_live_signals(resolved_symbol, market, generated, detail)
    return {"detail": detail, "signals": generated, "resolved_symbol": resolved_symbol}


async def _resolve_on_demand_stock(symbol: str, market: str) -> Optional[Dict[str, Any]]:
    normalized_symbol = normalize_symbol(symbol, market if market == "INDIA" else None)
    resolved_symbol, df = validate_symbol(normalized_symbol, market=market, interval="5m", period="5d")
    if not resolved_symbol or df.empty:
        return None

    detail = _build_on_demand_metrics(resolved_symbol, market, df)
    signals = analyze_stock(resolved_symbol, market, df, "intraday")
    if signals:
        signals[0]["analysis_summary"]["why_now"] = detail["setup_summary"]
    await _cache_symbol_for_market(market, resolved_symbol)
    await _cache_live_signals(resolved_symbol, market, signals, detail)
    await _cache_live_detail(resolved_symbol, market, detail)
    return {"detail": detail, "signals": signals, "resolved_symbol": resolved_symbol}


async def _latest_or_live_signal(symbol: str, market: str, timeframe: str = "swing"):
    normalized_symbol = normalize_symbol(symbol, market if market == "INDIA" else None)
    latest_signal = await signals_collection.find_one(
        {"symbol": normalized_symbol},
        sort=_signal_sort_order(),
    )
    if latest_signal:
        return latest_signal

    live_stock = await _resolve_live_stock(normalized_symbol, market, timeframe)
    if not live_stock:
        return None
    generated = live_stock["signals"]
    return generated[0] if generated else None


@app.on_event("startup")
async def startup_event():
    await setup_db()
    try:
        await refresh_indian_ticker_universe()
    except Exception as exc:
        logging.warning("Ticker universe refresh skipped during startup: %s", exc)
    start_scheduler()


@app.get("/signals", response_model=List[SignalModel])
async def get_signals(timeframe: Optional[str] = "intraday", market: Optional[str] = "USA", symbol: Optional[str] = None):
    query = {"timeframe": timeframe, "market": market}
    if symbol:
        query["symbol"] = normalize_symbol(symbol, market if market == "INDIA" else None)
    cursor = signals_collection.find(query).sort(_signal_sort_order())
    return await cursor.to_list(length=100)


@app.get("/signals/strategy/{strategy}", response_model=List[SignalModel])
async def get_signals_by_strategy(strategy: str, market: Optional[str] = "USA", timeframe: Optional[str] = "intraday"):
    cursor = signals_collection.find({"strategy": strategy, "timeframe": timeframe, "market": market}).sort(
        _signal_sort_order()
    )
    return await cursor.to_list(length=100)


@app.get("/stock/{symbol}", response_model=List[SignalModel])
async def get_stock_detail(symbol: str, market: Optional[str] = None):
    inferred_market = market or _infer_market_from_symbol(symbol)
    normalized_symbol = normalize_symbol(symbol, inferred_market if inferred_market == "INDIA" else None)
    cursor = signals_collection.find({"symbol": normalized_symbol}).sort(_signal_sort_order())
    signals = await cursor.to_list(length=20)
    if signals:
        return signals

    live_stock = await _resolve_live_stock(normalized_symbol, inferred_market, "intraday")
    if not live_stock:
        return []
    return live_stock["signals"]


@app.get("/api/stock/{symbol}")
async def get_stock_profile(symbol: str, market: Optional[str] = None):
    inferred_market = market or _infer_market_from_symbol(symbol)
    normalized_symbol = normalize_symbol(symbol, inferred_market if inferred_market == "INDIA" else None)
    summary_doc = await market_summary_collection.find_one({"market": inferred_market}, sort=[("timestamp", -1)])
    cached_profile = ((summary_doc or {}).get("on_demand_profiles") or {}).get(normalized_symbol)
    cached_signals = await signals_collection.find({"symbol": normalized_symbol, "market": inferred_market}).sort(_signal_sort_order()).to_list(length=20)

    if cached_profile and _is_fresh(cached_profile.get("updated_at")) and cached_signals:
        signals = cached_signals
        latest_signal = signals[0] if signals else None
        return {
            "symbol": normalized_symbol,
            "market": inferred_market,
            "detail": cached_profile,
            "latest_signal": latest_signal,
            "signals": signals,
        }

    live_stock = await _resolve_on_demand_stock(normalized_symbol, inferred_market)
    if not live_stock:
        raise HTTPException(status_code=404, detail="Unable to fetch stock profile")

    signals = live_stock["signals"]
    latest_signal = signals[0] if signals else None
    return {
        "symbol": live_stock["resolved_symbol"],
        "market": inferred_market,
        "detail": live_stock["detail"],
        "latest_signal": latest_signal,
        "signals": signals,
    }


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
                summary_doc = await market_summary_collection.find_one({"market": inferred_market}, sort=[("timestamp", -1)])
                tracked_symbols = set(summary_doc.get("tracked_symbols", [])) if summary_doc else set()
                cached_signals = await signals_collection.find({"symbol": normalized_symbol, "market": inferred_market}).sort(_signal_sort_order()).to_list(length=10)
                live_stock = await _resolve_live_stock(normalized_symbol, inferred_market, "intraday")
                if live_stock:
                    cached_signals = live_stock["signals"] or cached_signals
                elif summary_doc:
                    await market_summary_collection.update_one(
                        {"market": inferred_market},
                        {"$set": {"updated_at": ist_now(), "timestamp": ist_now()}, "$addToSet": {"tracked_symbols": normalized_symbol}},
                    )
                elif normalized_symbol not in tracked_symbols or not cached_signals:
                    await _cache_symbol_for_market(inferred_market, normalized_symbol)
                latest_signal = cached_signals[0] if cached_signals else await _latest_or_live_signal(normalized_symbol, inferred_market, "intraday")
                detail = live_stock["detail"] if live_stock else None
                results.append(
                    {
                        "symbol": normalized_symbol,
                        "name": quote.get("shortname", quote.get("longname", normalized_symbol)),
                        "market": inferred_market,
                        "signal": latest_signal["signal"] if latest_signal else "neutral",
                        "analysis": latest_signal.get("analysis_summary") if latest_signal else None,
                        "categories": latest_signal.get("categories", []) if latest_signal else [],
                        "rating": latest_signal.get("analysis_summary", {}).get("rating", "N/A") if latest_signal else "N/A",
                        "price": detail.get("price") if detail else latest_signal.get("entry_zone") if latest_signal else None,
                        "change_percent": detail.get("change_percent") if detail else None,
                        "rsi": detail.get("rsi") if detail else None,
                        "volume": detail.get("volume") if detail else None,
                        "updated_at": detail.get("updated_at") if detail else latest_signal.get("updated_at") if latest_signal else None,
                    }
                )
            return results
    except Exception as exc:
        logging.error("Search API error: %s", exc)
    return []


@app.get("/api/search/suggestions")
async def search_suggestions(q: str):
    query = q.strip().upper()
    if len(query) < 1:
        return []
    escaped_query = re.escape(query)
    if await ticker_universe_collection.count_documents({"market": "INDIA"}, limit=1) == 0:
        try:
            await refresh_indian_ticker_universe()
        except Exception as exc:
            logging.warning("Ticker universe refresh failed during suggestion lookup: %s", exc)

    cursor = ticker_universe_collection.find(
        {
            "market": "INDIA",
            "$or": [
                {"symbol": {"$regex": f"^{escaped_query}"}},
                {"clean_symbol": {"$regex": f"^{escaped_query}"}},
                {"name": {"$regex": escaped_query, "$options": "i"}},
                {"search_text": {"$regex": escaped_query}},
            ],
        }
    ).sort([("symbol", 1)])
    suggestions = await cursor.to_list(length=15)
    return [
        {
            "symbol": item["symbol"],
            "clean_symbol": item.get("clean_symbol", item["symbol"]),
            "fetch_symbol": item.get("fetch_symbol", item["symbol"]),
            "name": item.get("name", item["symbol"]),
            "exchange": item.get("exchange", "NSE"),
            "market": item.get("market", "INDIA"),
        }
        for item in suggestions
    ]


@app.get("/market-clock")
async def get_market_clock_endpoint(market: Optional[str] = "USA"):
    return get_market_clock(market or "USA")


@app.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str):
    is_india_symbol = symbol.upper().endswith(".NS") or symbol.upper().endswith(".BO")
    await watchlist_collection.delete_one({"symbol": normalize_symbol(symbol, "INDIA" if is_india_symbol else None)})
    return {"msg": "Removed from watchlist"}
