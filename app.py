"""Streamlit dashboard for Nifty 50 Futures & Options strategy backtesting."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from backtest_engine import BacktestEngine
from charts import drawdown_chart, equity_curve_chart, pnl_bar_chart
from costs import CostModel
from data_loader import load_market_data, load_sample_data
from export_utils import backtest_to_excel_bytes
from strategy_parser import (
    BUILT_IN_STRATEGY_NAME,
    BUILT_IN_STRATEGY_TEXT,
    built_in_strategy,
    parse_strategy,
)

st.set_page_config(page_title="Nifty F&O Backtester", layout="wide")


def main() -> None:
    st.title("Nifty 50 Futures & Options Backtester")
    st.caption("Natural-language strategy parser → event-driven backtest → dashboard + Excel export")

    with st.sidebar:
        st.header("Data")
        use_sample = st.toggle("Use built-in sample data", value=True)
        spot_file = futures_file = options_file = expiry_file = None
        if not use_sample:
            spot_file = st.file_uploader("Nifty spot CSV", type="csv")
            futures_file = st.file_uploader("Nifty futures CSV", type="csv")
            options_file = st.file_uploader("Nifty options CSV", type="csv")
            expiry_file = st.file_uploader("Expiry calendar CSV", type="csv")

        st.header("Costs & Risk")
        initial_capital = st.number_input("Initial capital", min_value=100000.0, value=1_000_000.0, step=50000.0)
        lot_size = st.number_input("Nifty lot size", min_value=1, value=50, step=1)
        brokerage = st.number_input("Brokerage per order", min_value=0.0, value=20.0, step=1.0)
        slippage_bps = st.number_input("Slippage (bps)", min_value=0.0, value=2.0, step=0.5)
        margin = st.number_input("Margin per lot", min_value=0.0, value=150_000.0, step=10000.0)
        initial_spot = st.number_input(
            "Initial spot baseline (0 = first spot close)",
            min_value=0.0,
            value=0.0,
            step=50.0,
            help="Fresh +1%, +2%, -1%, -2% trigger levels are measured from this baseline.",
        )

    strategy_choice = st.radio("Strategy input", [BUILT_IN_STRATEGY_NAME, "Custom natural-language strategy"], horizontal=True)
    if strategy_choice == BUILT_IN_STRATEGY_NAME:
        strategy_text = st.text_area("Strategy", BUILT_IN_STRATEGY_TEXT, height=110)
    else:
        strategy_text = st.text_area(
            "Strategy",
            "If Nifty spot moves up 1 percent, buy 1 lot monthly call and sell 1 lot monthly put. No-repeat levels. Rollover after 15th.",
            height=110,
        )

    if st.button("Run backtest", type="primary"):
        try:
            data = load_sample_data() if use_sample else _load_uploaded_data(spot_file, futures_file, options_file, expiry_file)
            if strategy_choice == BUILT_IN_STRATEGY_NAME:
                strategy = built_in_strategy()
            else:
                strategy = parse_strategy(
                    strategy_text,
                    lot_size=int(lot_size),
                    initial_capital=initial_capital,
                )
            strategy = _with_runtime_values(strategy, initial_capital, int(lot_size), margin, initial_spot or None)
            cost_model = CostModel(
                brokerage_per_order=brokerage,
                slippage_bps=slippage_bps,
                margin_per_lot=margin,
            )
            result = BacktestEngine(data, cost_model).run(strategy)
            _render_result(result)
        except Exception as exc:  # noqa: BLE001 - Streamlit should show user-friendly errors.
            st.error(str(exc))
            st.exception(exc)


def _load_uploaded_data(spot_file, futures_file, options_file, expiry_file):  # noqa: ANN001 - Streamlit upload types.
    missing = [name for name, file in {"spot": spot_file, "futures": futures_file, "options": options_file, "expiry": expiry_file}.items() if file is None]
    if missing:
        raise ValueError(f"Upload all required CSV files before running: {', '.join(missing)}")
    return load_market_data(spot_file, futures_file, options_file, expiry_file)


def _with_runtime_values(strategy, initial_capital: float, lot_size: int, margin: float, initial_spot: float | None):  # noqa: ANN001
    from dataclasses import replace

    legs = tuple(replace(leg, quantity=max(lot_size, leg.quantity)) for leg in strategy.legs)
    return replace(strategy, initial_capital=initial_capital, lot_size=lot_size, margin_per_lot=margin, initial_spot=initial_spot, legs=legs)


def _render_result(result) -> None:  # noqa: ANN001
    st.subheader("Summary")
    cols = st.columns(5)
    for col, (label, value) in zip(cols, result.summary.items()):
        col.metric(label.replace("_", " ").title(), value)

    left, right = st.columns(2)
    left.plotly_chart(equity_curve_chart(result.equity_curve), use_container_width=True)
    right.plotly_chart(drawdown_chart(result.equity_curve), use_container_width=True)

    st.plotly_chart(pnl_bar_chart(result.monthly_pnl, "month"), use_container_width=True)

    tabs = st.tabs(["Trade Log", "MTM", "Equity Curve", "Yearly P&L", "Monthly P&L"])
    tabs[0].dataframe(result.trade_log, use_container_width=True)
    tabs[1].dataframe(result.mtm, use_container_width=True)
    tabs[2].dataframe(result.equity_curve, use_container_width=True)
    tabs[3].dataframe(result.yearly_pnl, use_container_width=True)
    tabs[4].dataframe(result.monthly_pnl, use_container_width=True)

    st.download_button(
        "Download Excel report",
        data=backtest_to_excel_bytes(result),
        file_name="nifty_fo_backtest.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    main()
