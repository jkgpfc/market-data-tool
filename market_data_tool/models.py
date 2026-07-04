"""Application data models."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class MarketDataResult:
    """Calculated market data for a single symbol."""

    symbol: str
    status: str
    original_symbol: str | None = None
    cmp: float | None = None
    vwap: float | None = None
    hourly_rsi_14: float | None = None
    daily_rsi_14: float | None = None
    weekly_rsi_14: float | None = None
    monthly_rsi_14: float | None = None
    currency: str | None = None
    exchange: str | None = None
    instrument_type: str | None = None
    error: str | None = None
    fetched_at_utc: str = ""

    def __post_init__(self) -> None:
        if not self.fetched_at_utc:
            self.fetched_at_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable representation suitable for tabular export."""
        return asdict(self)
