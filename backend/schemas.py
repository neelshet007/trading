from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class ConfluenceScore(BaseModel):
    trend_alignment: int = 0
    fvg_mitigation: int = 0
    idm_sweep: int = 0
    discount_premium: int = 0
    total_score: int = 0

class NarrativeDetail(BaseModel):
    reason: str
    location: str
    context: str
    score_breakdown: List[str]
    timeline: List[str]

class SetupResponse(BaseModel):
    symbol: str
    bias: str
    status: str
    entry: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward: Optional[float] = None
    confluence: ConfluenceScore
    narrative: Optional[NarrativeDetail] = None
    ob_top: Optional[float] = None
    ob_bottom: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)

class ScanResult(BaseModel):
    opportunities: List[SetupResponse]
