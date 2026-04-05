from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


Direction = Literal["long", "short"]
Bias = Literal["bullish", "bearish", "neutral"]


@dataclass(slots=True)
class MarketConfig:
    market: str
    timeframe: str
    lookback_bars: int
    trend_ma_period: int
    signal_ma_period: int
    momentum_lookback: int
    min_slope_pct: float
    atr_period: int
    atr_threshold_pct: float
    pullback_max_distance_atr: float
    pullback_min_distance_atr: float
    swing_window: int
    equal_level_tolerance_atr: float
    sweep_reversal_bars: int
    trap_reversal_bars: int
    rejection_wick_ratio: float
    momentum_body_atr_ratio: float
    stop_buffer_atr: float
    stop_min_buffer_pct: float
    min_rr: float
    target_rr: float
    fee_pct: float
    slippage_pct: float
    max_consecutive_losses: int
    max_open_positions: int
    min_bars_between_trades: int
    max_trades_per_day: int


@dataclass(slots=True)
class StrategyScore:
    trend_alignment: int = 0
    momentum: int = 0
    liquidity_sweep: int = 0
    confirmation: int = 0
    clean_pullback: int = 0

    @property
    def total(self) -> int:
        return (
            self.trend_alignment
            + self.momentum
            + self.liquidity_sweep
            + self.confirmation
            + self.clean_pullback
        )

    def as_dict(self) -> Dict[str, int]:
        return {
            "trend_alignment": self.trend_alignment,
            "momentum": self.momentum,
            "liquidity_sweep": self.liquidity_sweep,
            "confirmation": self.confirmation,
            "clean_pullback": self.clean_pullback,
            "total": self.total,
        }


@dataclass(slots=True)
class TradeSignal:
    symbol: str
    market: str
    timeframe: str
    timestamp: Any
    direction: Direction
    bias: Bias
    score: StrategyScore
    entry: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    setup_type: str
    reasons: List[str] = field(default_factory=list)
    confirmation_type: Optional[str] = None
    liquidity_level: Optional[float] = None
    sweep_level: Optional[float] = None
    trap_level: Optional[float] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BacktestTrade:
    symbol: str
    market: str
    timeframe: str
    direction: Direction
    entry_time: Any
    exit_time: Any
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    fees: float
    slippage: float
    pnl: float
    pnl_pct: float
    equity_after_trade: float
    risk_reward: float
    score: int
    outcome: str
    reasons: List[str] = field(default_factory=list)
