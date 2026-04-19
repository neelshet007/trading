from __future__ import annotations

import asyncio
import io
import logging
import time
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from backtest import generate_excel_report, run_smc_backtest
from database import setup_db, watchlist_collection
from engine import build_data_pulse, run_forensic_scan, run_scan
from lazy_scanner import lazy_scanner
from market_segments import MARKET_SEGMENTS, get_market_segment
from market_utils import ensure_utc, get_market_clock, normalize_symbol, utc_now
from models import WatchlistModel
from schemas import ForensicReport, ScanResult, SegmentActivationResponse, SegmentScanResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CRYPTO_SEGMENT = MARKET_SEGMENTS["crypto"]
scan_cache: dict[tuple[str, ...], tuple[list[Any], float]] = {}
SCAN_CACHE_TTL = 300

app = FastAPI(title="Crypto Market Microstructure API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WatchlistAdd(BaseModel):
    symbol: str


def _segment_payload(segment: str) -> dict[str, Any]:
    return lazy_scanner.snapshot(segment)


def _segment_needs_refresh(payload: dict[str, Any]) -> bool:
    last_completed = payload.get("last_completed")
    if payload.get("status") in {"idle", "activating", "hibernated", "error"}:
        return True
    if not payload.get("opportunities") or not last_completed:
        return True
    age_seconds = (utc_now() - ensure_utc(last_completed)).total_seconds()
    return age_seconds >= payload.get("poll_interval_seconds", 20)


@app.on_event("startup")
async def startup_event():
    await setup_db()
    logger.info("Crypto-only scanner initialized.")


@app.post("/scan", response_model=ScanResult)
async def scan_market(symbols: list[str]):
    crypto_symbols = [normalize_symbol(symbol, "CRYPTO") for symbol in symbols]
    cache_key = tuple(sorted(crypto_symbols))
    current_time = time.time()
    cached = scan_cache.get(cache_key)
    if cached and current_time - cached[1] < SCAN_CACHE_TTL:
        return ScanResult(opportunities=cached[0])

    results = run_scan(crypto_symbols)
    scan_cache[cache_key] = (results, current_time)
    return ScanResult(opportunities=results)


@app.post("/api/v1/scanner/start", response_model=SegmentActivationResponse)
async def start_segment_scanner(market: str):
    segment = get_market_segment(market)
    if not segment:
        raise HTTPException(status_code=404, detail="Unknown market segment")
    payload = _segment_payload(segment["slug"])
    if _segment_needs_refresh(payload):
        lazy_scanner.activate(segment["slug"])
        asyncio.create_task(lazy_scanner.refresh(segment["slug"]))
        payload = _segment_payload(segment["slug"])
    return payload


@app.get("/scan/{market_type}", response_model=SegmentScanResponse)
async def scan_market_segment(market_type: str, force: bool = False):
    segment = get_market_segment(market_type)
    if not segment:
        raise HTTPException(status_code=404, detail="Unknown market segment")
    payload = _segment_payload(segment["slug"])
    if force or _segment_needs_refresh(payload):
        payload = await lazy_scanner.refresh(segment["slug"])
    return payload


@app.get("/scan/forensic/{symbol}", response_model=ForensicReport)
async def get_forensic_scan(symbol: str):
    report = run_forensic_scan(normalize_symbol(symbol, "CRYPTO"))
    if not report:
        raise HTTPException(status_code=404, detail="No crypto setup qualified under the regime and order-flow filters.")
    return report


@app.get("/scan/{market_type}/forensic/{symbol}", response_model=ForensicReport)
async def get_segment_forensic_scan(market_type: str, symbol: str):
    segment = get_market_segment(market_type)
    if not segment:
        raise HTTPException(status_code=404, detail="Unknown market segment")
    report = run_forensic_scan(normalize_symbol(symbol, "CRYPTO"))
    if not report:
        raise HTTPException(status_code=404, detail="No crypto setup qualified under the regime and order-flow filters.")
    return report


@app.get("/market-summary")
async def get_market_summary(market: Optional[str] = "CRYPTO"):
    payload = _segment_payload("crypto")
    opportunities = payload.get("opportunities", [])
    data_pulse = payload.get("data_pulse") or build_data_pulse(opportunities)
    bullish_count = sum(1 for item in opportunities if item.get("bias") == "bullish")
    bearish_count = sum(1 for item in opportunities if item.get("bias") == "bearish")
    return {
        "market": market,
        "status": payload.get("status", "active"),
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "sector_strength": {
            "BTC": "leader" if any(item.get("symbol") == "BTC-USD" for item in opportunities) else "neutral",
            "ETH": "leader" if any(item.get("symbol") == "ETH-USD" for item in opportunities) else "neutral",
            "ALTS": "risk-on" if len(opportunities) >= 4 else "selective",
        },
        "data_pulse": data_pulse,
        "timestamp": utc_now(),
        "timestamp_display_ist": get_market_clock("CRYPTO")["india_time"],
        "market_clock": get_market_clock("CRYPTO"),
    }


@app.get("/api/search/suggestions")
async def search_suggestions(q: str):
    query = q.strip().upper()
    if not query:
        return []
    matches = []
    for symbol in CRYPTO_SEGMENT["symbols"]:
        if query in symbol.upper().replace("-USD", "") or query in symbol.upper():
            matches.append(
                {
                    "symbol": symbol,
                    "clean_symbol": symbol.replace("-USD", ""),
                    "fetch_symbol": symbol,
                    "name": f"{symbol.replace('-USD', '')} spot pair",
                    "exchange": "CRYPTO",
                    "market": "CRYPTO",
                }
            )
    return matches[:15]


@app.get("/market-clock")
async def get_market_clock_endpoint(market: Optional[str] = "CRYPTO"):
    return get_market_clock(market or "CRYPTO")


@app.get("/watchlist", response_model=list[WatchlistModel])
async def get_watchlist():
    if watchlist_collection is None:
        return []
    cursor = watchlist_collection.find().sort("added_at", -1)
    return await cursor.to_list(length=100)


@app.get("/watchlist/audit", response_model=ScanResult)
async def get_watchlist_audit():
    watchlist_symbols: list[str] = []
    if watchlist_collection is not None:
        watchlist_items = await watchlist_collection.find().sort("added_at", -1).to_list(length=100)
        watchlist_symbols = [item["symbol"] for item in watchlist_items if item.get("symbol")]
    symbols = ["BTC-USD", "ETH-USD", "SOL-USD", *watchlist_symbols]
    normalized = list(dict.fromkeys(normalize_symbol(symbol, "CRYPTO") for symbol in symbols))
    return ScanResult(opportunities=run_scan(normalized))


@app.post("/watchlist")
async def add_to_watchlist(item: WatchlistAdd):
    if watchlist_collection is None:
        return {"msg": "Watchlist storage unavailable"}
    symbol = normalize_symbol(item.symbol, "CRYPTO")
    existing = await watchlist_collection.find_one({"symbol": symbol})
    if existing:
        return {"msg": "Already in watchlist"}
    await watchlist_collection.insert_one({"symbol": symbol, "added_at": ensure_utc()})
    return {"msg": "Added to watchlist"}


@app.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str):
    if watchlist_collection is None:
        return {"msg": "Watchlist storage unavailable"}
    await watchlist_collection.delete_one({"symbol": normalize_symbol(symbol, "CRYPTO")})
    return {"msg": "Removed from watchlist"}


@app.get("/backtest/download")
async def download_backtest(
    symbol: str = "BTC-USD",
    start: str = "2023-01-01",
    end: str = "2025-12-31",
    initial_capital: float = 10000.0,
):
    try:
        trades, stats = run_smc_backtest(symbol=normalize_symbol(symbol, "CRYPTO"), start=start, end=end, initial_capital=initial_capital)
        if not trades:
            raise HTTPException(status_code=404, detail="No crypto trades found in the given period.")
        excel_bytes = generate_excel_report(trades, stats, symbol)
        filename = f"CRYPTO_Backtest_{symbol.replace('-', '_')}_{start[:4]}_{end[:4]}.xlsx"
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/backtest/stats")
async def get_backtest_stats(
    symbol: str = "BTC-USD",
    start: str = "2023-01-01",
    end: str = "2025-12-31",
    initial_capital: float = 10000.0,
):
    try:
        trades, stats = run_smc_backtest(symbol=normalize_symbol(symbol, "CRYPTO"), start=start, end=end, initial_capital=initial_capital)
        return JSONResponse(content={"stats": stats, "trades": trades})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
