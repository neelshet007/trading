import yfinance as yf
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_data(symbol: str, interval: str = "1d", period: str = "1y") -> pd.DataFrame:
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            logger.warning(f"No data fetched for symbol: {symbol}")
            return pd.DataFrame()
        # Drop timezone from index if present, to avoid issues
        if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        return df
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()

def fetch_multiple(symbols: list, interval: str = "1d", period: str = "1y") -> dict:
    data = {}
    for sym in symbols:
        df = fetch_data(sym, interval, period)
        if not df.empty:
            data[sym] = df
    return data
