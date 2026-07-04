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
    frame = pd.read_csv(file)
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{name} CSV missing columns: {', '.join(sorted(missing))}")
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
    options["option_type"] = options["option_type"].astype(str).str.upper()
    expiries = ExpiryCalendar.from_frame(load_csv(expiry_file, required={"expiry"}, name="Expiry"))
    return MarketDataBundle(spot=spot, futures=futures, options=options, expiries=expiries)


def load_sample_data(sample_dir: str | Path = "sample_data") -> MarketDataBundle:
    path = Path(sample_dir)
    return load_market_data(path / "nifty_spot.csv", path / "nifty_futures.csv", path / "nifty_options.csv", path / "expiry_calendar.csv")
