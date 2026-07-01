"""Technical indicator calculations for market data."""

from __future__ import annotations

import pandas as pd


def rsi(series: pd.Series, period: int = 14) -> float | None:
    """Return the latest Wilder RSI value for a price series.

    Args:
        series: Price series, typically closing prices.
        period: RSI lookback period.

    Returns:
        The latest RSI rounded to four decimals, or None when insufficient data is
        available.
    """
    prices = pd.to_numeric(series, errors="coerce").dropna()
    if len(prices) <= period:
        return None

    delta = prices.diff().dropna()
    gains = delta.clip(lower=0).to_list()
    losses = (-delta.clip(upper=0)).to_list()

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for gain, loss in zip(gains[period:], losses[period:], strict=False):
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period

    if avg_loss == 0 and avg_gain == 0:
        return 50.0
    if avg_loss == 0:
        return 100.0
    if avg_gain == 0:
        return 0.0

    rs = avg_gain / avg_loss
    return round(float(100 - (100 / (1 + rs))), 4)


def vwap(frame: pd.DataFrame) -> float | None:
    """Return VWAP from OHLCV data using typical price.

    Args:
        frame: DataFrame containing High, Low, Close, and Volume columns.

    Returns:
        VWAP rounded to four decimals, or None when unavailable.
    """
    required = {"High", "Low", "Close", "Volume"}
    if frame.empty or not required.issubset(frame.columns):
        return None

    data = frame[list(required)].apply(pd.to_numeric, errors="coerce").dropna()
    data = data[data["Volume"] > 0]
    if data.empty:
        return None

    typical_price = (data["High"] + data["Low"] + data["Close"]) / 3
    volume = data["Volume"]
    denominator = volume.sum()
    if denominator == 0:
        return None

    return round(float((typical_price * volume).sum() / denominator), 4)
