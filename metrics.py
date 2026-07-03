"""Backtest performance metrics."""

from __future__ import annotations

import pandas as pd


def calculate_drawdown(equity: pd.Series) -> pd.Series:
    running_max = equity.cummax()
    return ((equity - running_max) / running_max).fillna(0.0)


def yearly_pnl(equity_curve: pd.DataFrame) -> pd.DataFrame:
    return _period_pnl(equity_curve, "Y", "year")


def monthly_pnl(equity_curve: pd.DataFrame) -> pd.DataFrame:
    return _period_pnl(equity_curve, "M", "month")


def summarize_performance(equity_curve: pd.DataFrame, trade_log: pd.DataFrame, initial_capital: float) -> dict[str, float | int | str]:
    if equity_curve.empty:
        return {"initial_capital": initial_capital, "final_equity": initial_capital, "total_pnl": 0.0, "return_pct": 0.0, "max_drawdown_pct": 0.0, "trades": 0}
    final_equity = float(equity_curve.iloc[-1]["equity"])
    total_pnl = final_equity - initial_capital
    max_drawdown = float(calculate_drawdown(equity_curve["equity"]).min() * 100)
    return {
        "initial_capital": round(initial_capital, 2),
        "final_equity": round(final_equity, 2),
        "total_pnl": round(total_pnl, 2),
        "return_pct": round(total_pnl / initial_capital * 100, 2) if initial_capital else 0.0,
        "max_drawdown_pct": round(max_drawdown, 2),
        "trades": int(len(trade_log)),
    }


def _period_pnl(equity_curve: pd.DataFrame, freq: str, label: str) -> pd.DataFrame:
    if equity_curve.empty:
        return pd.DataFrame(columns=[label, "start_equity", "end_equity", "pnl", "return_pct"])
    frame = equity_curve.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    grouped = frame.groupby(frame["date"].dt.to_period(freq))["equity"]
    result = grouped.agg(start_equity="first", end_equity="last").reset_index()
    result[label] = result["date"].astype(str)
    result["pnl"] = result["end_equity"] - result["start_equity"]
    result["return_pct"] = (result["pnl"] / result["start_equity"] * 100).round(2)
    return result[[label, "start_equity", "end_equity", "pnl", "return_pct"]]
