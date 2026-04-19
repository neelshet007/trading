from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List

from market_segments import MARKET_SEGMENTS, get_market_segment
from market_utils import ensure_utc, get_market_clock, utc_now


@dataclass
class SegmentScanState:
    segment: str
    active: bool = False
    status: str = "idle"
    last_accessed: datetime | None = None
    last_activated: datetime | None = None
    last_completed: datetime | None = None
    last_error: str | None = None
    opportunities: List[Dict[str, Any]] = field(default_factory=list)


class LazyScannerManager:
    def __init__(self) -> None:
        self._lock = Lock()
        self._states: Dict[str, SegmentScanState] = {}

    def _state_for(self, segment: str) -> SegmentScanState:
        if segment not in self._states:
            self._states[segment] = SegmentScanState(segment=segment)
        return self._states[segment]

    def reap_expired(self) -> None:
        now = utc_now()
        with self._lock:
            for segment, config in MARKET_SEGMENTS.items():
                state = self._state_for(segment)
                if not state.last_accessed:
                    continue
                age = (now - ensure_utc(state.last_accessed)).total_seconds()
                if age > config["activation_ttl_seconds"]:
                    state.active = False
                    state.status = "hibernated"
                    state.opportunities = []
                    state.last_error = None

    def activate(self, segment: str) -> SegmentScanState:
        config = get_market_segment(segment)
        if not config:
            raise ValueError(f"Unknown market segment: {segment}")
        self.reap_expired()
        with self._lock:
            state = self._state_for(config["slug"])
            now = utc_now()
            state.active = True
            state.status = "activating" if not state.opportunities else "active"
            state.last_accessed = now
            state.last_activated = state.last_activated or now
            return state

    def _serialize_signal(self, signal: Any) -> Dict[str, Any]:
        if hasattr(signal, "model_dump"):
            return signal.model_dump()
        if isinstance(signal, dict):
            return signal
        return dict(signal)

    def refresh_sync(self, segment: str) -> Dict[str, Any]:
        config = get_market_segment(segment)
        if not config:
            raise ValueError(f"Unknown market segment: {segment}")

        from engine import run_scan

        slug = config["slug"]
        state = self.activate(slug)
        with self._lock:
            state.status = "scanning"
            state.last_error = None

        try:
            results = run_scan(config["symbols"])
            serialized = [self._serialize_signal(item) for item in results]
            with self._lock:
                state = self._state_for(slug)
                state.opportunities = serialized
                state.status = "active"
                state.last_completed = utc_now()
                state.last_accessed = state.last_completed
        except Exception as exc:
            with self._lock:
                state = self._state_for(slug)
                state.status = "error"
                state.last_error = str(exc)
                state.last_accessed = utc_now()
            raise

        return self.snapshot(slug)

    async def refresh(self, segment: str) -> Dict[str, Any]:
        return await asyncio.to_thread(self.refresh_sync, segment)

    def snapshot(self, segment: str) -> Dict[str, Any]:
        config = get_market_segment(segment)
        if not config:
            raise ValueError(f"Unknown market segment: {segment}")
        self.reap_expired()
        with self._lock:
            state = self._state_for(config["slug"])
            last_seen = state.last_accessed or utc_now()
            return {
                "segment": config["slug"],
                "title": config["title"],
                "backend_market": config["backend_market"],
                "default_timeframe": config["default_timeframe"],
                "poll_interval_seconds": config["poll_interval_seconds"],
                "activation_ttl_seconds": config["activation_ttl_seconds"],
                "scanner_focus": config["scanner_focus"],
                "margin_profile": config["margin_profile"],
                "zoom_resolution": config["zoom_resolution"],
                "active": state.active,
                "status": state.status,
                "last_accessed": state.last_accessed,
                "last_activated": state.last_activated,
                "last_completed": state.last_completed,
                "last_error": state.last_error,
                "market_clock": get_market_clock(config["backend_market"], last_seen),
                "opportunities": state.opportunities,
            }


lazy_scanner = LazyScannerManager()
