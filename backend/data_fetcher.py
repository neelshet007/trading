import yfinance as yf
import pandas as pd
import logging
from typing import Optional, Tuple

from market_utils import candidate_symbols, normalize_symbol

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    history = ticker.history(period=period, interval=interval)
    return _clean_history(history)


def validate_symbol(symbol: str, market: Optional[str] = None, interval: str = "1d", period: str = "1y") -> Tuple[Optional[str], pd.DataFrame]:
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


def fetch_data(symbol: str, interval: str = "1d", period: str = "1y", market: Optional[str] = None) -> pd.DataFrame:
    _, df = validate_symbol(symbol, market=market, interval=interval, period=period)
    return df


def fetch_multiple(symbols: list, interval: str = "1d", period: str = "1y", market: Optional[str] = None) -> dict:
    data = {}
    for sym in symbols:
        resolved_symbol, df = validate_symbol(sym, market=market, interval=interval, period=period)
        if resolved_symbol and not df.empty:
            data[resolved_symbol] = df
        else:
            logger.warning("Skipping invalid or empty symbol: %s", sym)
    return data
