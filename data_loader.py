"""CSV loading and normalization for Nifty spot, futures, options, and expiries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from expiry_utils import ExpiryCalendar


@dataclass(slots=True)
class MarketDataBundle:
    spot: pd.DataFrame
    futures: pd.DataFrame
    options: pd.DataFrame
    expiries: ExpiryCalendar


def load_csv(file: str | Path | BinaryIO, *, required: set[str], name: str) -> pd.DataFrame:
    """Load a CSV and validate required columns, dates, expiries, and numeric fields."""
    try:
        frame = pd.read_csv(file)
    except Exception as exc:  # noqa: BLE001 - include CSV name in user-facing errors.
        raise ValueError(f"Unable to read {name} CSV: {exc}") from exc

    frame = pd.read_csv(file)
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{name} CSV missing columns: {', '.join(sorted(missing))}")
    if frame.empty:
        raise ValueError(f"{name} CSV is empty")

    if "date" in frame.columns:
        raw_dates = frame["date"].copy()
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
        invalid = frame["date"].isna() & raw_dates.notna()
        if invalid.any():
            raise ValueError(f"{name} CSV contains invalid date values in 'date'")
        frame = frame.dropna(subset=["date"])
        if frame.empty:
            raise ValueError(f"{name} CSV has no valid dated rows")

    if "expiry" in frame.columns:
        raw_expiries = frame["expiry"].copy()
        frame["expiry"] = pd.to_datetime(frame["expiry"], errors="coerce").dt.normalize()
        invalid = frame["expiry"].isna() & raw_expiries.notna()
        if invalid.any():
            raise ValueError(f"{name} CSV contains invalid date values in 'expiry'")
        if frame["expiry"].isna().any():
            raise ValueError(f"{name} CSV contains blank expiry values")

    for column in ["open", "high", "low", "close", "volume", "strike"]:
        if column in frame.columns:
            raw_values = frame[column].copy()
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
            invalid = frame[column].isna() & raw_values.notna()
            if invalid.any():
                raise ValueError(f"{name} CSV contains non-numeric values in '{column}'")
            if column in required and frame[column].isna().any():
                raise ValueError(f"{name} CSV contains blank values in required column '{column}'")

    sort_columns = [column for column in ["date", "expiry", "strike"] if column in frame.columns]
    return frame.sort_values(sort_columns).reset_index(drop=True) if sort_columns else frame.reset_index(drop=True)
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
        frame = frame.dropna(subset=["date"])
    if "expiry" in frame.columns:
        frame["expiry"] = pd.to_datetime(frame["expiry"], errors="coerce").dt.normalize()
    for column in ["open", "high", "low", "close", "volume", "strike"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.sort_values([column for column in ["date", "expiry", "strike"] if column in frame.columns]).reset_index(drop=True)


def load_market_data(
    spot_file: str | Path | BinaryIO,
    futures_file: str | Path | BinaryIO,
    options_file: str | Path | BinaryIO,
    expiry_file: str | Path | BinaryIO,
) -> MarketDataBundle:
    spot = load_csv(spot_file, required={"date", "close"}, name="Spot")
    futures = load_csv(futures_file, required={"date", "expiry", "close"}, name="Futures")
    options = load_csv(options_file, required={"date", "expiry", "strike", "option_type", "close"}, name="Options")
    options["option_type"] = options["option_type"].astype(str).str.strip().str.upper()
    invalid_option_types = sorted(set(options["option_type"]) - {"CE", "PE"})
    if invalid_option_types:
        raise ValueError(f"Options CSV option_type must be CE or PE; found: {', '.join(invalid_option_types)}")
    options["option_type"] = options["option_type"].astype(str).str.upper()
    expiries = ExpiryCalendar.from_frame(load_csv(expiry_file, required={"expiry"}, name="Expiry"))
    return MarketDataBundle(spot=spot, futures=futures, options=options, expiries=expiries)


def load_sample_data(sample_dir: str | Path = "sample_data") -> MarketDataBundle:
    path = Path(sample_dir)
    return load_market_data(path / "nifty_spot.csv", path / "nifty_futures.csv", path / "nifty_options.csv", path / "expiry_calendar.csv")
