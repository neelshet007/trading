import pandas as pd
import ta
import numpy as np

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    try:
        # Avoid SettingWithCopyWarning
        df = df.copy()
        
        # Exponential Moving Averages
        df['EMA_9'] = ta.trend.ema_indicator(close=df['Close'], window=9)
        df['EMA_20'] = ta.trend.ema_indicator(close=df['Close'], window=20)
        df['EMA_50'] = ta.trend.ema_indicator(close=df['Close'], window=50)
        df['EMA_200'] = ta.trend.ema_indicator(close=df['Close'], window=200)

        # RSI
        df['RSI'] = ta.momentum.rsi(close=df['Close'], window=14)

        # VWAP (Needs Volume, High, Low, Close)
        if 'Volume' in df.columns:
            vwap_indicator = ta.volume.VolumeWeightedAveragePrice(
                high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'], window=14
            )
            df['VWAP'] = vwap_indicator.volume_weighted_average_price()
        else:
            df['VWAP'] = np.nan

        # ATR limit calculation for risk reward
        df['ATR'] = ta.volatility.average_true_range(high=df['High'], low=df['Low'], close=df['Close'], window=14)

        return df.dropna()
    except Exception as e:
        print(f"Error calculating indicators: {e}")
        return df
