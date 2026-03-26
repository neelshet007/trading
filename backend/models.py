from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class SignalModel(BaseModel):
    symbol: str
    strategy: str
    signal: str  # "bullish", "bearish", "neutral"
    score: float
    reasons: List[str]
    timeframe: str
    entry_zone: Optional[float] = None
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    risk_reward: Optional[float] = None
    timestamp: datetime = datetime.utcnow()

    model_config = ConfigDict(populate_by_name=True)

class MarketSummaryModel(BaseModel):
    status: str
    bullish_count: int
    bearish_count: int
    sector_strength: dict
    timestamp: datetime = datetime.utcnow()

class WatchlistModel(BaseModel):
    symbol: str
    added_at: datetime = datetime.utcnow()

class ScoreResponse(BaseModel):
    score: float
    reasons: List[str]
