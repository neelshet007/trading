from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


MANIFESTO_PATH = Path(__file__).resolve().parent.parent / "SYSTEM_LOGIC_MANIFESTO.txt"


@dataclass(frozen=True)
class ManifestoConfig:
    structural_lookback_bars: int
    confluence_threshold: float
    confluence_max_score: float
    fixed_risk_min_pct: float
    fixed_risk_max_pct: float
    friction_cap_pct_of_r: float
    funding_clamp_hourly_pct: float
    regime_labels: dict[int, str]
    entry_models: tuple[str, ...]

    @property
    def default_risk_pct(self) -> float:
        return self.fixed_risk_min_pct


def _extract(pattern: str, text: str, cast):
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError(f"Could not parse manifesto pattern: {pattern}")
    return cast(match.group(1))


@lru_cache(maxsize=1)
def load_manifesto_config() -> ManifestoConfig:
    text = MANIFESTO_PATH.read_text(encoding="utf-8")
    lookback = _extract(r"Lookback Window:\s*Increased to\s*(\d+)\s*bars", text, int)
    threshold = _extract(r"threshold recalibrated to\s*([0-9.]+)\s*/\s*([0-9.]+)", text, lambda value: float(value))
    max_score = _extract(r"threshold recalibrated to\s*[0-9.]+\s*/\s*([0-9.]+)", text, float)
    risk_min = _extract(r"Fixed Risk:\s*([0-9.]+)\s*-\s*([0-9.]+)%", text, lambda value: float(value))
    risk_max = _extract(r"Fixed Risk:\s*[0-9.]+\s*-\s*([0-9.]+)%", text, float)
    friction_cap = _extract(r"exceeds\s*([0-9.]+)%\s*of the projected R-Multiple", text, float)
    funding_clamp = _extract(r"funding rates reach extreme\s+thresholds\s*\(>\s*([0-9.]+)%\s*per hour\)", text, float)

    return ManifestoConfig(
        structural_lookback_bars=lookback,
        confluence_threshold=threshold,
        confluence_max_score=max_score,
        fixed_risk_min_pct=risk_min,
        fixed_risk_max_pct=risk_max,
        friction_cap_pct_of_r=friction_cap,
        funding_clamp_hourly_pct=funding_clamp,
        regime_labels={
            1: "Regime 1 - Low Volatility Consolidation",
            2: "Regime 2 - Directional Expansion",
            3: "Regime 3 - High Volatility Repricing",
        },
        entry_models=("Unicorn", "Silver Bullet", "OTE"),
    )

