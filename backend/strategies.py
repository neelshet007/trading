import pandas as pd
from typing import Dict, Any, Tuple

def evaluate_trend_continuation(df: pd.DataFrame) -> Tuple[bool, dict]:
    # Price above EMA/VWAP and HH-HL (simplified structure via higher close over periods)
    last = df.iloc[-1]
    prev = df.iloc[-2]
    reasons = []
    
    is_bullish = False
    is_bearish = False
    
    if last['Close'] > last['EMA_20'] and last['EMA_20'] > last['EMA_50']:
        if last['Close'] > prev['Close'] and last['Low'] >= prev['Low']:
            is_bullish = True
            reasons.extend(["Price above 20 & 50 EMA", "Higher High / Higher Low formed"])
        
    elif last['Close'] < last['EMA_20'] and last['EMA_20'] < last['EMA_50']:
        if last['Close'] < prev['Close'] and last['High'] <= prev['High']:
            is_bearish = True
            reasons.extend(["Price below 20 & 50 EMA", "Lower High / Lower Low formed"])
            
    if is_bullish:
        return True, {"signal": "bullish", "reasons": reasons, "score": 8.0}
    elif is_bearish:
        return True, {"signal": "bearish", "reasons": reasons, "score": 8.0}
    
    return False, {}

def evaluate_pullback(df: pd.DataFrame) -> Tuple[bool, dict]:
    # Pullback to EMA/VWAP, RSI cooling
    last = df.iloc[-1]
    prev = df.iloc[-2]
    reasons = []
    
    is_bullish = False
    is_bearish = False
    
    # Bullish: strong trend, pullback to EMA 20, RSI < 50
    if prev['Close'] > prev['EMA_50'] and last['Low'] <= last['EMA_20'] and last['Close'] >= last['EMA_20']:
        if last['RSI'] < 55 and last['RSI'] > 40:
            is_bullish = True
            reasons.extend(["Pullback to 20 EMA", "RSI cooling down (40-55)"])
            
    # Bearish: downtrend, rally to EMA 20, RSI > 50
    elif prev['Close'] < prev['EMA_50'] and last['High'] >= last['EMA_20'] and last['Close'] <= last['EMA_20']:
        if last['RSI'] > 45 and last['RSI'] < 60:
            is_bearish = True
            reasons.extend(["Rally to 20 EMA", "RSI cooling up (45-60)"])
            
    if is_bullish:
        return True, {"signal": "bullish", "reasons": reasons, "score": 7.5}
    elif is_bearish:
        return True, {"signal": "bearish", "reasons": reasons, "score": 7.5}
        
    return False, {}

def evaluate_breakout(df: pd.DataFrame) -> Tuple[bool, dict]:
    # Range breakout, volume spike
    last = df.iloc[-1]
    prev_20 = df.iloc[-20:-1]
    reasons = []
    
    avg_vol = prev_20['Volume'].mean() if 'Volume' in df.columns else 1
    recent_high = prev_20['High'].max()
    recent_low = prev_20['Low'].min()
    
    is_bullish = False
    is_bearish = False
    
    if last['Close'] > recent_high and ('Volume' not in df.columns or last['Volume'] > avg_vol * 1.5):
        is_bullish = True
        reasons.extend(["Price broke 20-period High", "Volume spike detected"])
        
    elif last['Close'] < recent_low and ('Volume' not in df.columns or last['Volume'] > avg_vol * 1.5):
        is_bearish = True
        reasons.extend(["Price broke 20-period Low", "Volume spike detected"])
        
    if is_bullish:
        return True, {"signal": "bullish", "reasons": reasons, "score": 8.5}
    elif is_bearish:
        return True, {"signal": "bearish", "reasons": reasons, "score": 8.5}
        
    return False, {}

def evaluate_reversal(df: pd.DataFrame) -> Tuple[bool, dict]:
    # RSI extremes, structure shift
    last = df.iloc[-1]
    prev = df.iloc[-2]
    reasons = []
    
    is_bullish = False
    is_bearish = False
    
    if prev['RSI'] < 30 and last['RSI'] >= 30:
        if last['Close'] > prev['Close']:
            is_bullish = True
            reasons.extend(["RSI recovering from oversold (<30)", "Price structure shifting up"])
            
    elif prev['RSI'] > 70 and last['RSI'] <= 70:
        if last['Close'] < prev['Close']:
            is_bearish = True
            reasons.extend(["RSI rejecting from overbought (>70)", "Price structure shifting down"])
            
    if is_bullish:
        return True, {"signal": "bullish", "reasons": reasons, "score": 7.0}
    elif is_bearish:
        return True, {"signal": "bearish", "reasons": reasons, "score": 7.0}
        
    return False, {}
