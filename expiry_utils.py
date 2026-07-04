"""Expiry calendar utilities for Nifty futures and options."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

import pandas as pd

from instruments import ExpiryBucket


@dataclass(frozen=True, slots=True)
class ExpiryCalendar:
    """Expiry calendar wrapper with bucket lookup helpers."""

    expiries: tuple[pd.Timestamp, ...]

    @classmethod
    def from_frame(cls, frame: pd.DataFrame) -> "ExpiryCalendar":
        if "expiry" not in frame.columns:
            raise ValueError("Expiry calendar CSV must contain an 'expiry' column")
        expiries = tuple(sorted(pd.to_datetime(frame["expiry"], errors="coerce").dropna().dt.normalize().unique()))
        if not expiries:
            raise ValueError("Expiry calendar does not contain any valid dates")
        return cls(tuple(pd.Timestamp(expiry) for expiry in expiries))

    @classmethod
    def from_dates(cls, dates: Iterable[str | date | pd.Timestamp]) -> "ExpiryCalendar":
        frame = pd.DataFrame({"expiry": list(dates)})
        return cls.from_frame(frame)

    def next_expiry(self, as_of: pd.Timestamp, bucket: ExpiryBucket = "weekly") -> pd.Timestamp:
        """Return the next expiry matching the requested bucket on or after as_of."""
        as_of = pd.Timestamp(as_of).normalize()
        future_expiries = [expiry for expiry in self.expiries if expiry >= as_of]
        if not future_expiries:
            raise ValueError(f"No expiry available on or after {as_of.date()}")

        if bucket == "weekly":
            return future_expiries[0]

        monthly = self.monthly_expiries(as_of)
        if bucket == "monthly":
            return monthly[0]
        if bucket == "next_month":
            return monthly[1]
        if bucket == "next_to_next_month":
            return monthly[2]
        raise ValueError(f"Unsupported expiry bucket: {bucket}")

    def monthly_expiries(self, as_of: pd.Timestamp) -> list[pd.Timestamp]:
        """Return month-end contract expiries from as_of onward."""
        as_of = pd.Timestamp(as_of).normalize()
        frame = pd.DataFrame({"expiry": [expiry for expiry in self.expiries if expiry >= as_of]})
        if frame.empty:
            raise ValueError(f"No monthly expiries available on or after {as_of.date()}")
        frame["period"] = frame["expiry"].dt.to_period("M")
        monthly = frame.groupby("period", as_index=False)["expiry"].max()["expiry"].tolist()
        if len(monthly) < 3:
            raise ValueError("At least three monthly expiries are required for next-to-next-month contracts")
        return [pd.Timestamp(expiry) for expiry in monthly]


def should_rollover(as_of: pd.Timestamp, current_expiry: pd.Timestamp, rollover_after_day: int = 15) -> bool:
    """Return True once the calendar day reaches rollover threshold before expiry."""
    as_of = pd.Timestamp(as_of).normalize()
    current_expiry = pd.Timestamp(current_expiry).normalize()
    return as_of.day > rollover_after_day and as_of < current_expiry
