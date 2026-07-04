"""Plotly chart helpers for Streamlit dashboards."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def equity_curve_chart(equity_curve: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=equity_curve.get("date"), y=equity_curve.get("equity"), mode="lines", name="Equity"))
    fig.update_layout(title="Equity Curve", xaxis_title="Date", yaxis_title="Equity", template="plotly_white")
    return fig


def drawdown_chart(equity_curve: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=equity_curve.get("date"), y=equity_curve.get("drawdown", 0) * 100, fill="tozeroy", name="Drawdown %"))
    fig.update_layout(title="Drawdown", xaxis_title="Date", yaxis_title="Drawdown %", template="plotly_white")
    return fig


def pnl_bar_chart(period_pnl: pd.DataFrame, label: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=period_pnl.get(label), y=period_pnl.get("pnl"), name="P&L"))
    fig.update_layout(title=f"{label.title()} P&L", xaxis_title=label.title(), yaxis_title="P&L", template="plotly_white")
    return fig
