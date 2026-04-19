from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class RegimeContext(BaseModel):
    hmm_state: int
    hmm_regime: str
    regime_confidence: float
    ipda_cycle: str
    institutional_bias: str
    correlated_factors: List[str] = []


class MarketFootprint(BaseModel):
    htf_range_low: float
    htf_range_high: float
    nearest_order_block_low: Optional[float] = None
    nearest_order_block_high: Optional[float] = None
    nearest_fvg_low: Optional[float] = None
    nearest_fvg_high: Optional[float] = None
    fvg_atr_multiple: Optional[float] = None
    premium_discount_state: str
    ote_level: Optional[float] = None
    structure_signal: str
    cvd_divergence: str
    liquidation_sweep_confirmed: bool


class TriggerPlan(BaseModel):
    entry_model: str
    entry_price: float
    entry_band_low: float
    entry_band_high: float
    stop_loss: float
    take_profit: float
    invalidation: str
    execution_timeframe: str
    confirmation: str


class RiskEnvelope(BaseModel):
    var_95: float
    gjr_garch_vol: float
    convexity_risk: float
    expected_slippage_bps: float
    funding_rate_clamp_bps: float
    max_equity_allocation: float
    recommended_equity_allocation: float
    r_multiple: float
    expectancy: float


class HumanLoopAssessment(BaseModel):
    inducement_traps: List[str]
    human_checks: List[str]
    automation_risk: str


class ConfluenceScore(BaseModel):
    trend_alignment: int = 0
    fvg_mitigation: int = 0
    idm_sweep: int = 0
    discount_premium: int = 0
    order_flow_alignment: int = 0
    total_score: int = 0


class NarrativeDetail(BaseModel):
    reason: str
    location: str
    context: str
    score_breakdown: List[str]
    timeline: List[str]
    zoom_reason: Optional[str] = None


class ChecklistDetails(BaseModel):
    regime_allows_execution: bool
    liquidity_swept: bool
    fvg_created: bool
    in_ote_zone: bool
    cvd_supportive: bool


class DerivativeStats(BaseModel):
    funding_rate_clamp_bps: float
    liquidation_bias: str
    cvd_divergence: str


class ForensicReport(BaseModel):
    symbol: str
    formation: str
    catalyst: str
    checklist: ChecklistDetails
    derivative_stats: DerivativeStats
    instruction: str
    entry: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    context: RegimeContext
    footprint: MarketFootprint
    risk: RiskEnvelope
    hitl: HumanLoopAssessment
    zoom_resolution: Optional[str] = None
    trade_classification: Optional[str] = None
    margin_multiple: Optional[str] = None
    auto_square_off: Optional[str] = None


class SetupResponse(BaseModel):
    symbol: str
    bias: str
    status: str
    timestamp: Optional[datetime] = None
    entry: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward: Optional[float] = None
    confluence: ConfluenceScore
    context: RegimeContext
    footprint: MarketFootprint
    trigger: TriggerPlan
    risk: RiskEnvelope
    hitl: HumanLoopAssessment
    narrative: Optional[NarrativeDetail] = None
    ob_top: Optional[float] = None
    ob_bottom: Optional[float] = None
    zoom_resolution: Optional[str] = None
    trade_classification: Optional[str] = None
    margin_multiple: Optional[str] = None
    auto_square_off: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ScanResult(BaseModel):
    opportunities: List[SetupResponse]


class SegmentActivationResponse(BaseModel):
    segment: str
    title: str
    active: bool
    status: str
    poll_interval_seconds: int
    activation_ttl_seconds: int
    scanner_focus: str
    default_timeframe: str
    margin_profile: str
    zoom_resolution: str
    last_accessed: Optional[datetime] = None
    last_completed: Optional[datetime] = None
    last_error: Optional[str] = None


class SegmentScanResponse(SegmentActivationResponse):
    backend_market: str
    market_clock: dict
    opportunities: List[SetupResponse]
