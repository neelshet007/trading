import yfinance as yf
import asyncio
import pandas as pd
import logging
import random
import re
import time
from io import StringIO
from typing import Any, Optional, Tuple
import requests

from market_utils import candidate_symbols, normalize_symbol
from database import db_updated_at, market_summary_collection, signals_collection, ticker_universe_collection
from market_utils import get_market_clock
from indicators import add_indicators

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NSE_NIFTY_500_PAGE = "https://www.nseindia.com/products-services/indices-nifty500-index"
NSE_NIFTY_500_CSV = "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"
NSE_NIFTY_500_CSV_FALLBACK = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
NSE_SECURITIES_PAGE = "https://www.nseindia.com/static/market-data/securities-available-for-trading"
NSE_EQUITY_CSV = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
NSE_SME_CSV = "https://nsearchives.nseindia.com/content/equities/SME_EQUITY_L.csv"
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Accept": "text/csv,application/json,text/plain,*/*",
    "Referer": NSE_NIFTY_500_PAGE,
}
BATCH_SIZE = 50
INDIA_SCAN_INTERVAL_SECONDS = 600
INDIA_TOP_OPPORTUNITY_LIMIT = 15
PENNY_STOCK_SYMBOLS = (
    "SUZLON",
    "YESBANK",
    "IDEA",
    "JPPOWER",
    "RPOWER",
    "GTLINFRA",
    "ZEEL",
    "UJJIVANSFB",
    "TRIDENT",
    "SAIL",
)
VALID_INDIAN_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9&\-]{0,24}$")
UNSUPPORTED_SUFFIXES = (
    "-RE",
    "-BE",
    "-BZ",
    "-BL",
    "-BT",
    "-IL",
    "-IV",
    "-PP",
    "-P1",
    "-P2",
)
ALLOWED_SERIES = {"EQ", "BE", "BZ", "SM", "ST", "MT", "NQ"}

POLLING_MARKETS = {
    "USA": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "SPY", "QQQ"],
    "INDIA": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "^NSEI"],
    "CRYPTO": ["BTC-USD", "ETH-USD", "SOL-USD"],
    "COMMODITIES": ["GC=F", "SI=F", "CL=F"],
}


def _clean_history(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if isinstance(df.index, pd.DatetimeIndex):
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        else:
            df.index = df.index.tz_convert("UTC")
    return df.dropna(how="all")


def _download_history(symbol: str, interval: str, period: str) -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    history = ticker.history(
        period=period,
        interval=interval,
        auto_adjust=False,
        actions=False,
        prepost=True,
    )
    return _clean_history(history)


def _download_csv_with_session(session: requests.Session, url: str, *, referer: str) -> pd.DataFrame:
    headers = dict(NSE_HEADERS)
    headers["Referer"] = referer
    response = session.get(url, headers=headers, timeout=30)
    if response.status_code == 429:
        logger.warning("[LIMIT REACHED] Cooling down...")
        time.sleep(60)
        response = session.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "").lower()
    body_start = response.text[:256].lstrip().lower()
    if "text/html" in content_type or body_start.startswith("<!doctype") or body_start.startswith("<html") or body_start.startswith("# upgraded to sitefinity"):
        raise ValueError(f"Expected CSV from {url}, received HTML")
    return pd.read_csv(StringIO(response.text))


def _normalize_company_name(row: pd.Series) -> str:
    for key in ("Company Name", "NAME OF COMPANY", "Company", "Issuer Name"):
        if key in row and pd.notna(row[key]):
            return str(row[key]).strip()
    return ""


def _is_supported_indian_symbol(symbol: str, row: pd.Series) -> bool:
    if not symbol or not VALID_INDIAN_SYMBOL_RE.fullmatch(symbol):
        return False
    if any(symbol.endswith(suffix) for suffix in UNSUPPORTED_SUFFIXES):
        return False

    series_value = str(row.get(" SERIES", row.get("SERIES", ""))).strip().upper()
    if series_value and series_value not in ALLOWED_SERIES:
        return False

    name = _normalize_company_name(row).upper()
    if any(flag in name for flag in ("RIGHT", "WARRANT", "DEBENTURE", "PREFERENCE", "ENTITLEMENT")):
        return False
    return True


def _normalize_symbol_records(frame: pd.DataFrame, exchange: str) -> list[dict[str, str]]:
    symbol_column = next((column for column in frame.columns if column.strip().lower() in {"symbol", "ticker"}), None)
    if not symbol_column:
        return []

    records: list[dict[str, str]] = []
    suffix = ".BO" if exchange == "BSE" else ".NS"
    for _, row in frame.iterrows():
        raw_symbol = row.get(symbol_column)
        if pd.isna(raw_symbol):
            continue
        clean_symbol = str(raw_symbol).strip().upper()
        if not _is_supported_indian_symbol(clean_symbol, row):
            continue
        company_name = _normalize_company_name(row) or clean_symbol
        fetch_symbol = clean_symbol if clean_symbol.startswith("^") else f"{clean_symbol}{suffix}"
        records.append(
            {
                "symbol": clean_symbol,
                "clean_symbol": clean_symbol,
                "fetch_symbol": fetch_symbol,
                "exchange": exchange,
                "name": company_name,
            }
        )
    return records


def get_nse_universe() -> list[dict[str, str]]:
    session = requests.Session()
    session.headers.update(NSE_HEADERS)
    landing = session.get(NSE_NIFTY_500_PAGE, timeout=20)
    if landing.status_code == 429:
        logger.warning("NSE rate limit hit while priming session. Cooling down for 60 seconds.")
        time.sleep(60)
        landing = session.get(NSE_NIFTY_500_PAGE, timeout=20)
    landing.raise_for_status()

    try:
        frame = _download_csv_with_session(session, NSE_NIFTY_500_CSV, referer=NSE_NIFTY_500_PAGE)
        records = _normalize_symbol_records(frame, "NSE")
        if len(records) < 400:
            raise ValueError("Primary Nifty 500 source returned too few valid symbols")
    except Exception as exc:
        logger.warning("Primary Nifty 500 source unavailable, using fallback: %s", exc)
        frame = _download_csv_with_session(session, NSE_NIFTY_500_CSV_FALLBACK, referer=NSE_NIFTY_500_PAGE)
        records = _normalize_symbol_records(frame, "NSE")
        if len(records) < 400:
            raise ValueError("Fallback Nifty 500 source returned too few valid symbols")
    return [{"clean_symbol": record["clean_symbol"], "fetch_symbol": record["fetch_symbol"], "name": record["name"]} for record in records]


def get_full_indian_universe() -> list[dict[str, str]]:
    session = requests.Session()
    session.headers.update(NSE_HEADERS)
    session.get(NSE_SECURITIES_PAGE, timeout=20)

    universe_by_key: dict[str, dict[str, str]] = {}

    for record in get_nse_universe():
        universe_by_key[f"NSE:{record['clean_symbol']}"] = {
            "symbol": record["clean_symbol"],
            "clean_symbol": record["clean_symbol"],
            "fetch_symbol": record["fetch_symbol"],
            "exchange": "NSE",
            "name": record.get("name", record["clean_symbol"]),
        }

    equity_frame = _download_csv_with_session(session, NSE_EQUITY_CSV, referer=NSE_SECURITIES_PAGE)
    sme_frame = _download_csv_with_session(session, NSE_SME_CSV, referer=NSE_SECURITIES_PAGE)

    for record in [*_normalize_symbol_records(equity_frame, "NSE"), *_normalize_symbol_records(sme_frame, "NSE")]:
        universe_by_key[f"NSE:{record['clean_symbol']}"] = record

    for penny_symbol in PENNY_STOCK_SYMBOLS:
        universe_by_key[f"NSE:{penny_symbol}"] = {
            "symbol": penny_symbol,
            "clean_symbol": penny_symbol,
            "fetch_symbol": f"{penny_symbol}.NS",
            "exchange": "NSE",
            "name": penny_symbol,
        }

    universe = list(universe_by_key.values())
    universe.sort(key=lambda item: (item["exchange"], item["symbol"]))
    return universe


def _polling_params(market: str) -> tuple[str, str]:
    if market in {"USA", "CRYPTO", "COMMODITIES"}:
        return "1m", "1d"
    return "1m", "1d"


def _latest_price(df: pd.DataFrame) -> Optional[float]:
    if df.empty or "Close" not in df.columns:
        return None
    close_series = df["Close"].dropna()
    if close_series.empty:
        return None
    return float(close_series.iloc[-1])


def _build_quote_snapshot(symbol: str, market: str, df: pd.DataFrame, previous_quote: dict[str, Any] | None) -> dict[str, Any]:
    updated_at = db_updated_at()
    market_clock = get_market_clock(market, updated_at)
    price = _latest_price(df)
    status = "Live" if market == "CRYPTO" else ("Live" if market_clock["is_open"] else "Closed")
    if price is None and previous_quote:
        price = previous_quote.get("price")
        status = "Live" if market == "CRYPTO" else "Closed"

    return {
        "symbol": symbol,
        "price": round(price, 2) if price is not None else None,
        "status": status,
        "updated_at": updated_at,
    }


def validate_symbol(symbol: str, market: Optional[str] = None, interval: str = "1m", period: str = "1d") -> Tuple[Optional[str], pd.DataFrame]:
    last_error: Optional[Exception] = None
    for candidate in candidate_symbols(symbol, market):
        for attempt in range(2):
            try:
                df = _download_history(candidate, interval, period)
                if not df.empty:
                    if candidate != symbol:
                        logger.info("Standardized %s to %s", symbol, candidate)
                    return candidate, df
                logger.warning("No data fetched for symbol: %s (attempt %s)", candidate, attempt + 1)
            except Exception as exc:
                last_error = exc
                logger.warning("Fetch attempt failed for %s (attempt %s): %s", candidate, attempt + 1, exc)

    normalized = normalize_symbol(symbol, market)
    if normalized != symbol:
        logger.error("Symbol validation failed for %s after trying %s", symbol, candidate_symbols(symbol, market))
    if last_error:
        logger.error("Final fetch error for %s: %s", symbol, last_error)
    return None, pd.DataFrame()


def fetch_data(symbol: str, interval: str = "1m", period: str = "1d", market: Optional[str] = None) -> pd.DataFrame:
    _, df = validate_symbol(symbol, market=market, interval=interval, period=period)
    return df


def fetch_multiple(symbols: list, interval: str = "1m", period: str = "1d", market: Optional[str] = None) -> dict:
    data = {}
    for sym in symbols:
        resolved_symbol, df = validate_symbol(sym, market=market, interval=interval, period=period)
        if resolved_symbol and not df.empty:
            data[resolved_symbol] = df
        else:
            logger.warning("Skipping invalid or empty symbol: %s", sym)
    return data


def _extract_symbol_frame(batch_frame: pd.DataFrame, symbol: str, is_multi: bool) -> pd.DataFrame:
    if batch_frame.empty:
        return pd.DataFrame()
    symbol_frame = batch_frame[symbol] if is_multi else batch_frame
    if isinstance(symbol_frame, pd.Series):
        symbol_frame = symbol_frame.to_frame().T
    return _clean_history(symbol_frame.dropna(how="all"))


def _download_batch_history(symbols: list[str], period: str = "1y", interval: str = "1d", market: Optional[str] = None) -> dict[str, pd.DataFrame]:
    batch_data: dict[str, pd.DataFrame] = {}
    retry_count = 0

    while retry_count < 3:
        try:
            downloaded = yf.download(
                tickers=" ".join(symbols),
                period=period,
                interval=interval,
                auto_adjust=False,
                actions=False,
                progress=False,
                threads=False,
                group_by="ticker",
            )
            is_multi = isinstance(downloaded.columns, pd.MultiIndex)
            for symbol in symbols:
                batch_data[symbol] = _extract_symbol_frame(downloaded, symbol, is_multi)
            return batch_data
        except Exception as exc:
            message = str(exc)
            if "429" in message:
                retry_count += 1
                logger.warning("[LIMIT REACHED] Cooling down...")
                time.sleep(60)
                continue
            raise

    return {symbol: pd.DataFrame() for symbol in symbols}


def _ma_crossed(close_now: float, close_prev: float, ma_now: float, ma_prev: float) -> bool:
    if pd.isna(ma_now) or pd.isna(ma_prev):
        return False
    crossed_up = close_prev <= ma_prev and close_now > ma_now
    crossed_down = close_prev >= ma_prev and close_now < ma_now
    return crossed_up or crossed_down


def _build_india_metric(fetch_symbol: str, clean_symbol: str, df: pd.DataFrame) -> Optional[dict[str, Any]]:
    if df.empty or len(df) < 200:
        return None

    enriched = add_indicators(df.copy())
    if enriched.empty or len(enriched) < 2:
        return None

    last = enriched.iloc[-1]
    previous = enriched.iloc[-2]
    avg_20_volume = float(df["Volume"].tail(20).mean()) if "Volume" in df.columns else 0.0
    sma_20 = float(df["Close"].rolling(window=20).mean().iloc[-1])
    sma_50 = float(df["Close"].rolling(window=50).mean().iloc[-1])
    sma_200 = float(df["Close"].rolling(window=200).mean().iloc[-1])
    price = float(last["Close"])
    volume = float(last["Volume"]) if "Volume" in enriched.columns and pd.notna(last["Volume"]) else 0.0
    rsi = float(last["RSI"]) if "RSI" in enriched.columns and pd.notna(last["RSI"]) else None
    price_prev = float(previous["Close"])
    sma_50_prev = float(df["Close"].rolling(window=50).mean().iloc[-2])
    sma_200_prev = float(df["Close"].rolling(window=200).mean().iloc[-2])

    flags: list[str] = []
    if avg_20_volume and volume > avg_20_volume * 2:
        flags.append("volume_spike")
    if rsi is not None and (rsi < 30 or rsi > 70):
        flags.append("rsi_extreme")
    if _ma_crossed(price, price_prev, sma_50, sma_50_prev):
        flags.append("sma50_cross")
    if _ma_crossed(price, price_prev, sma_200, sma_200_prev):
        flags.append("sma200_cross")

    signal_bias = "bullish" if (rsi is not None and rsi < 30) or price >= sma_50 else "bearish"
    strength = 0.0
    if avg_20_volume:
        strength += min(volume / avg_20_volume, 4.0)
    if rsi is not None:
        strength += abs(rsi - 50) / 10
    if "sma50_cross" in flags:
        strength += 2.0
    if "sma200_cross" in flags:
        strength += 2.5
    if price < 50:
        strength += 0.25

    return {
        "symbol": fetch_symbol,
        "fetch_symbol": fetch_symbol,
        "clean_symbol": clean_symbol,
        "market": "INDIA",
        "price": round(price, 2),
        "price_20ma": round(sma_20, 2) if not pd.isna(sma_20) else None,
        "rsi_14": round(rsi, 2) if rsi is not None else None,
        "avg_20_day_volume": int(avg_20_volume) if avg_20_volume else 0,
        "current_volume": int(volume) if volume else 0,
        "sma_50": round(sma_50, 2) if not pd.isna(sma_50) else None,
        "sma_200": round(sma_200, 2) if not pd.isna(sma_200) else None,
        "patterns": flags,
        "signal": signal_bias,
        "score": round(strength, 2),
        "timestamp": db_updated_at(),
    }


def scan_india_universe() -> dict[str, Any]:
    universe = get_full_indian_universe()
    all_metrics: list[dict[str, Any]] = []

    for batch_start in range(0, len(universe), BATCH_SIZE):
        batch = universe[batch_start: batch_start + BATCH_SIZE]
        batch_symbols = [item["fetch_symbol"] for item in batch]
        batch_lookup = {item["fetch_symbol"]: item for item in batch}
        batch_frames = _download_batch_history(batch_symbols, period="1y", interval="1d", market="INDIA")

        for fetch_symbol, df in batch_frames.items():
            lookup = batch_lookup[fetch_symbol]
            metric = _build_india_metric(fetch_symbol, lookup["clean_symbol"], df)
            if metric:
                metric["name"] = lookup.get("name", lookup["clean_symbol"])
                metric["exchange"] = lookup.get("exchange", "NSE")
                all_metrics.append(metric)

        if batch_start + BATCH_SIZE < len(universe):
            time.sleep(random.uniform(1.5, 3.5))

    high_opportunity_metrics = [
        metric
        for metric in all_metrics
        if (metric["current_volume"] > metric["avg_20_day_volume"] * 2 if metric["avg_20_day_volume"] else False)
        or (metric["rsi_14"] is not None and metric["rsi_14"] < 30)
    ]
    top_candidates = sorted(
        high_opportunity_metrics,
        key=lambda item: (
            item["current_volume"] / max(item["avg_20_day_volume"], 1),
            50 - item["rsi_14"] if item["rsi_14"] is not None else 0,
            item["score"],
        ),
        reverse=True,
    )[:INDIA_TOP_OPPORTUNITY_LIMIT]
    return {"all_metrics": all_metrics, "top_10": top_candidates, "tracked_symbols": [item["fetch_symbol"] for item in universe]}


async def refresh_indian_ticker_universe():
    universe = await asyncio.to_thread(get_full_indian_universe)
    if not universe:
        return 0

    await ticker_universe_collection.delete_many({"market": "INDIA"})
    documents = []
    for item in universe:
        aliases = list(dict.fromkeys([item["symbol"], item["clean_symbol"], item["fetch_symbol"]]))
        documents.append(
            {
                "market": "INDIA",
                "symbol": item["symbol"],
                "clean_symbol": item["clean_symbol"],
                "fetch_symbol": item["fetch_symbol"],
                "exchange": item["exchange"],
                "name": item["name"],
                "aliases": aliases,
                "search_text": " ".join([item["symbol"], item["clean_symbol"], item["fetch_symbol"], item["name"], item["exchange"]]).upper(),
            }
        )
    await ticker_universe_collection.insert_many(documents)
    logger.info("Ticker universe refreshed with %s Indian records.", len(documents))
    return len(documents)


async def update_market_data():
    for market, base_symbols in POLLING_MARKETS.items():
        summary = await market_summary_collection.find_one({"market": market}, sort=[("timestamp", -1)])
        tracked_symbols = summary.get("tracked_symbols", []) if summary else []
        symbols = list(dict.fromkeys([*base_symbols, *tracked_symbols]))
        previous_quotes = {quote.get("symbol"): quote for quote in (summary.get("live_quotes", []) if summary else [])}
        interval, period = _polling_params(market)
        live_quotes: list[dict[str, Any]] = []

        for symbol in symbols:
            resolved_symbol, df = validate_symbol(symbol, market=market, interval=interval, period=period)
            quote_symbol = resolved_symbol or normalize_symbol(symbol, market if market == "INDIA" else None)
            live_quotes.append(_build_quote_snapshot(quote_symbol, market, df, previous_quotes.get(quote_symbol)))

        updated_at = db_updated_at()
        market_clock = get_market_clock(market, updated_at)
        next_summary = dict(summary or {})
        next_summary.update(
            {
                "market": market,
                "status": next_summary.get("status", "Unknown"),
                "bullish_count": next_summary.get("bullish_count", 0),
                "bearish_count": next_summary.get("bearish_count", 0),
                "sector_strength": next_summary.get("sector_strength", {}),
                "timestamp": updated_at,
                "updated_at": updated_at,
                "timestamp_display_ist": market_clock["india_time"],
                "market_clock": market_clock,
                "tracked_symbols": symbols,
                "live_quotes": live_quotes,
            }
        )
        next_summary.pop("_id", None)
        await market_summary_collection.replace_one({"market": market}, next_summary, upsert=True)

    logger.info("[POLLING SUCCESS] Market data updated at %s IST.", db_updated_at().strftime("%H:%M"))


async def update_india_market_scan():
    scan_result = await asyncio.to_thread(scan_india_universe)
    updated_at = db_updated_at()
    market_clock = get_market_clock("INDIA", updated_at)
    summary = await market_summary_collection.find_one({"market": "INDIA"}, sort=[("timestamp", -1)]) or {}

    top_opportunities = [
        {
            "symbol": item["fetch_symbol"],
            "fetch_symbol": item["fetch_symbol"],
            "clean_symbol": item["clean_symbol"],
            "signal": item["signal"],
            "score": item["score"],
            "price": item["price"],
            "patterns": item["patterns"],
        }
        for item in scan_result["top_10"]
    ]

    summary.update(
        {
            "market": "INDIA",
            "status": "Scanned",
            "timestamp": updated_at,
            "updated_at": updated_at,
            "timestamp_display_ist": updated_at.strftime("%I:%M %p").lstrip("0"),
            "market_clock": market_clock,
            "tracked_symbols": scan_result["tracked_symbols"],
            "universe_size": len(scan_result["tracked_symbols"]),
            "analyzed_count": len(scan_result["all_metrics"]),
            "top_opportunities": top_opportunities,
        }
    )
    summary.pop("_id", None)
    await market_summary_collection.replace_one({"market": "INDIA"}, summary, upsert=True)

    await signals_collection.delete_many({"market": "INDIA", "timeframe": "intraday"})
    if scan_result["top_10"]:
        india_signals = [
            {
                "symbol": item["fetch_symbol"],
                "fetch_symbol": item["fetch_symbol"],
                "clean_symbol": item["clean_symbol"],
                "market": "INDIA",
                "strategy": "Nifty 500 Scanner",
                "signal": item["signal"],
                "score": item["score"],
                "reasons": item["patterns"],
                "timeframe": "intraday",
                "entry_zone": item["price"],
                "stop_loss": None,
                "target": None,
                "risk_reward": None,
                "timestamp": updated_at,
                "timestamp_display_ist": updated_at.strftime("%I:%M %p").lstrip("0"),
                "patterns": item["patterns"],
                "pattern_strength": float(len(item["patterns"])),
                "breakout_level": item["sma_50"],
                "categories": ["Nifty 500 Scanner"],
                "confluence_score": item["score"],
                "pattern_details": [],
                "probability": None,
                "analysis_summary": {
                    "headline": "Nifty 500 scan hit",
                    "explanation": f"{item['clean_symbol']} matched {', '.join(item['patterns'])}.",
                    "why_now": f"RSI {item['rsi_14']}, 20d avg volume {item['avg_20_day_volume']}, 50 SMA {item['sma_50']}, 200 SMA {item['sma_200']}.",
                    "rating": "High" if item["score"] >= 8 else "Medium",
                    "categories": ["Nifty 500 Scanner"],
                    "pattern_descriptions": item["patterns"],
                    "probability": {"breakout": "Medium", "trend_continuation": "Medium"},
                },
            }
            for item in scan_result["top_10"]
        ]
        await signals_collection.insert_many(india_signals)

    logger.info("Nifty 500 scan completed. Analyzed %s symbols, stored top %s at %s IST.", len(scan_result["all_metrics"]), len(scan_result["top_10"]), updated_at.strftime("%H:%M"))
