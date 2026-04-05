from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from trading_types import MarketConfig


CONFIG_DIR = Path(__file__).resolve().parent / "market_configs"


@lru_cache(maxsize=None)
def load_market_config(market: str) -> MarketConfig:
    normalized = market.strip().lower()
    config_path = CONFIG_DIR / f"config_{normalized}.json"
    if not config_path.exists():
        raise ValueError(f"Unsupported market config: {market}")

    data = json.loads(config_path.read_text(encoding="utf-8"))
    return MarketConfig(**data)

