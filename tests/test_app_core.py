import pandas as pd

from backtest_engine import BacktestEngine
from data_loader import load_sample_data
from expiry_utils import ExpiryCalendar
from strategy_parser import BUILT_IN_STRATEGY_NAME, parse_strategy


def test_builtin_strategy_parser():
    strategy = parse_strategy(BUILT_IN_STRATEGY_NAME)
    assert strategy.trigger.move_pct == 1.0
    assert len(strategy.legs) == 2
    assert strategy.rollover_after_day == 15


def test_custom_strategy_parser_put_sell_weekly():
    strategy = parse_strategy("If Nifty drops 2 percent, sell 1 lot weekly put. No repeat levels. Rollover after 18th.")
    assert strategy.trigger.direction == "down"
    assert strategy.trigger.move_pct == 2.0
    assert strategy.legs[0].expiry_bucket == "weekly"
    assert strategy.legs[0].side.value == "sell"
    assert strategy.rollover_after_day == 18


def test_expiry_calendar_monthly_bucket():
    calendar = ExpiryCalendar.from_dates(["2024-01-04", "2024-01-25", "2024-02-29", "2024-03-28"])
    assert calendar.next_expiry(pd.Timestamp("2024-01-05"), "monthly") == pd.Timestamp("2024-01-25")
    assert calendar.next_expiry(pd.Timestamp("2024-01-05"), "next_month") == pd.Timestamp("2024-02-29")


def test_sample_backtest_runs():
    data = load_sample_data()
    strategy = parse_strategy(BUILT_IN_STRATEGY_NAME)
    result = BacktestEngine(data).run(strategy)
    assert not result.equity_curve.empty
    assert not result.trade_log.empty
    assert "total_pnl" in result.summary
