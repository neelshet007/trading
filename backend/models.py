from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, List, Optional
from datetime import datetime

class ProbabilityInsight(BaseModel):
    breakout: str
    trend_continuation: str


class AnalysisSummary(BaseModel):
    headline: str
    explanation: str
    why_now: str
    rating: str
    categories: List[str]
    pattern_descriptions: List[str]
    probability: ProbabilityInsight


class SignalModel(BaseModel):
    symbol: str
    market: str
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
    timestamp_display_ist: Optional[str] = None
    patterns: List[str] = []
    pattern_strength: Optional[float] = None
    breakout_level: Optional[float] = None
    categories: List[str] = []
    confluence_score: Optional[float] = None
    pattern_details: List[Dict[str, Any]] = []
    probability: Optional[ProbabilityInsight] = None
    analysis_summary: Optional[AnalysisSummary] = None

    model_config = ConfigDict(populate_by_name=True)

class MarketSummaryModel(BaseModel):
    market: Optional[str] = None
    status: str
    bullish_count: int
    bearish_count: int
    sector_strength: Dict[str, str] = {}
    timestamp: datetime = datetime.utcnow()
    timestamp_display_ist: Optional[str] = None
    market_clock: Dict[str, Any] = {}

class WatchlistModel(BaseModel):
    symbol: str
    added_at: datetime = datetime.utcnow()

class ScoreResponse(BaseModel):
    score: float
    reasons: List[str]
