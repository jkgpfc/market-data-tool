"""Yahoo Finance market data provider."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd
import yfinance as yf

from .indicators import rsi, vwap
from .models import MarketDataResult
from .symbols import SymbolRequest

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class YahooFinanceProvider:
    """Fetch and calculate market data from Yahoo Finance."""

    intraday_period: str = "1d"
    hourly_period: str = "60d"
    daily_period: str = "1y"
    weekly_period: str = "5y"
    monthly_period: str = "10y"

    def fetch_symbol(self, request: str | SymbolRequest) -> MarketDataResult:
        """Fetch a symbol and calculate supported metrics.

        Yahoo Finance symbol conventions are used after normalization, enabling
        global stocks, indices, ETFs, forex, commodities, futures, and
        options/futures contracts where Yahoo publishes the instrument.
        """
        symbol_request = request if isinstance(request, SymbolRequest) else SymbolRequest(original=str(request), yahoo_symbol=str(request).strip())
        normalized = symbol_request.yahoo_symbol.strip()
        if not normalized:
            return MarketDataResult(symbol=normalized, original_symbol=symbol_request.original, status="error", error="Empty symbol")

        try:
            ticker = yf.Ticker(normalized)
            info = self._safe_info(ticker)
            intraday = self._history(ticker, period=self.intraday_period, interval="5m")
            hourly = self._history(ticker, period=self.hourly_period, interval="1h")
            daily = self._history(ticker, period=self.daily_period, interval="1d")
            weekly = self._history(ticker, period=self.weekly_period, interval="1wk")
            monthly = self._history(ticker, period=self.monthly_period, interval="1mo")

            cmp_value = self._current_market_price(intraday, daily, info)
            if cmp_value is None:
                raise ValueError("No price data returned by Yahoo Finance")

            return MarketDataResult(
                symbol=normalized,
                original_symbol=symbol_request.original,
                status="ok",
                cmp=cmp_value,
                vwap=vwap(intraday),
                hourly_rsi_14=rsi(hourly.get("Close", pd.Series(dtype=float))),
                daily_rsi_14=rsi(daily.get("Close", pd.Series(dtype=float))),
                weekly_rsi_14=rsi(weekly.get("Close", pd.Series(dtype=float))),
                monthly_rsi_14=rsi(monthly.get("Close", pd.Series(dtype=float))),
                currency=info.get("currency"),
                exchange=info.get("exchange") or info.get("fullExchangeName"),
                instrument_type=info.get("quoteType"),
            )
        except Exception as exc:  # noqa: BLE001 - per-symbol resilience is intentional.
            LOGGER.exception("Failed to process symbol %s", normalized)
            return MarketDataResult(symbol=normalized, original_symbol=symbol_request.original, status="error", error=str(exc))

    @staticmethod
    def _safe_info(ticker: yf.Ticker) -> dict[str, object]:
        try:
            return ticker.get_info() or {}
        except Exception as exc:  # noqa: BLE001 - metadata may fail while prices work.
            LOGGER.warning("Unable to fetch metadata for %s: %s", ticker.ticker, exc)
            return {}

    @staticmethod
    def _history(ticker: yf.Ticker, *, period: str, interval: str) -> pd.DataFrame:
        frame = ticker.history(period=period, interval=interval, auto_adjust=False, actions=False)
        if frame is None or frame.empty:
            return pd.DataFrame()
        return frame.dropna(how="all")

    @staticmethod
    def _current_market_price(
        intraday: pd.DataFrame,
        daily: pd.DataFrame,
        info: dict[str, object],
    ) -> float | None:
        for key in ("regularMarketPrice", "currentPrice", "previousClose"):
            value = info.get(key)
            if isinstance(value, int | float) and not pd.isna(value):
                return round(float(value), 4)

        for frame in (intraday, daily):
            if not frame.empty and "Close" in frame.columns:
                closes = pd.to_numeric(frame["Close"], errors="coerce").dropna()
                if not closes.empty:
                    return round(float(closes.iloc[-1]), 4)
        return None
