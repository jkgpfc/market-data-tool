from io import BytesIO, StringIO

import pandas as pd

from backtest_engine import BacktestEngine, calculate_trigger_level
from data_loader import load_csv, load_sample_data
from expiry_utils import ExpiryCalendar
from export_utils import backtest_to_excel_bytes
from instruments import InstrumentType, OptionType, Side
from strategy_parser import BUILT_IN_STRATEGY_NAME, built_in_strategy, parse_strategy


def test_builtin_strategy_parser():
    strategy = parse_strategy(BUILT_IN_STRATEGY_NAME)
    assert strategy.trigger.move_pct == 1.0
    assert strategy.trigger.direction == "both"
    assert strategy.rollover_after_day == 15
    assert len(strategy.legs) == 2
    option_leg, future_leg = strategy.legs
    assert option_leg.instrument_type is InstrumentType.OPTION
    assert option_leg.option_type is OptionType.CALL
    assert option_leg.side is Side.SELL
    assert future_leg.instrument_type is InstrumentType.FUTURE
    assert future_leg.side is Side.BUY


def test_custom_strategy_parser_put_sell_weekly():
    strategy = parse_strategy("If Nifty drops 2 percent, sell 1 lot weekly put. No repeat levels. Rollover after 18th.")
    assert strategy.trigger.direction == "down"
    assert strategy.trigger.move_pct == 2.0
    assert strategy.legs[0].expiry_bucket == "weekly"
    assert strategy.legs[0].side.value == "sell"
    assert strategy.rollover_after_day == 18


def test_expiry_calendar_monthly_buckets():
    calendar = ExpiryCalendar.from_dates(["2024-01-04", "2024-01-25", "2024-02-29", "2024-03-28"])
    assert calendar.next_expiry(pd.Timestamp("2024-01-05"), "monthly") == pd.Timestamp("2024-01-25")
    assert calendar.next_expiry(pd.Timestamp("2024-01-05"), "next_month") == pd.Timestamp("2024-02-29")
    assert calendar.next_expiry(pd.Timestamp("2024-01-05"), "next_to_next_month") == pd.Timestamp("2024-03-28")




def test_expiry_switching_before_and_after_15th():
    data = load_sample_data()
    engine = BacktestEngine(data)
    strategy = built_in_strategy()
    monthly_leg = strategy.legs[0]

    before = engine._effective_instrument(monthly_leg, strategy, pd.Timestamp("2024-01-15"))
    after = engine._effective_instrument(monthly_leg, strategy, pd.Timestamp("2024-01-16"))

    assert before.expiry_bucket == "monthly"
    assert data.expiries.next_expiry(pd.Timestamp("2024-01-15"), before.expiry_bucket) == pd.Timestamp("2024-01-25")
    assert after.expiry_bucket == "next_to_next_month"
    assert data.expiries.next_expiry(pd.Timestamp("2024-01-16"), after.expiry_bucket) == pd.Timestamp("2024-03-28")


def test_expiry_switching_across_year_transition():
    calendar = ExpiryCalendar.from_dates(["2024-12-26", "2025-01-30", "2025-02-27", "2025-03-27"])
    data = load_sample_data()
    data.expiries = calendar
    engine = BacktestEngine(data)
    strategy = built_in_strategy()
    monthly_leg = strategy.legs[0]

    before = engine._effective_instrument(monthly_leg, strategy, pd.Timestamp("2024-12-15"))
    after = engine._effective_instrument(monthly_leg, strategy, pd.Timestamp("2024-12-16"))

    assert calendar.next_expiry(pd.Timestamp("2024-12-15"), before.expiry_bucket) == pd.Timestamp("2024-12-26")
    assert calendar.next_expiry(pd.Timestamp("2024-12-16"), after.expiry_bucket) == pd.Timestamp("2025-02-27")




def test_calculate_trigger_level_boundaries():
    initial = 25_000.0
    assert calculate_trigger_level(25_125.0, initial, 1.0) == 0
    assert calculate_trigger_level(25_250.0, initial, 1.0) == 1
    assert calculate_trigger_level(25_500.0, initial, 1.0) == 2
    assert calculate_trigger_level(24_875.0, initial, 1.0) == 0
    assert calculate_trigger_level(24_750.0, initial, 1.0) == -1
    assert calculate_trigger_level(24_500.0, initial, 1.0) == -2
    assert calculate_trigger_level(initial, initial, 1.0) == 0


def test_positive_trigger_levels_are_emitted_once():
    engine = BacktestEngine(load_sample_data())
    strategy = built_in_strategy()
    triggered: set[int] = set()

    levels = engine._trigger_levels(strategy, 103.1, 100.0, triggered)
    assert levels == [1, 2, 3]
    triggered.update(levels)
    assert engine._trigger_levels(strategy, 101.0, 100.0, triggered) == []
    assert engine._trigger_levels(strategy, 100.0, 100.0, triggered) == []
    assert engine._trigger_levels(strategy, 103.5, 100.0, triggered) == []


def test_negative_trigger_levels_are_emitted_once():
    engine = BacktestEngine(load_sample_data())
    strategy = built_in_strategy()
    triggered: set[int] = set()

    levels = engine._trigger_levels(strategy, 96.9, 100.0, triggered)
    assert levels == [-1, -2, -3]
    triggered.update(levels)
    assert engine._trigger_levels(strategy, 99.0, 100.0, triggered) == []
    assert engine._trigger_levels(strategy, 100.0, 100.0, triggered) == []
    assert engine._trigger_levels(strategy, 96.5, 100.0, triggered) == []


def test_sample_backtest_runs_with_required_outputs():
    data = load_sample_data()
    strategy = parse_strategy(BUILT_IN_STRATEGY_NAME)
    result = BacktestEngine(data).run(strategy)
    assert not result.equity_curve.empty
    assert not result.trade_log.empty
    assert not result.mtm.empty
    assert not result.monthly_pnl.empty
    assert not result.yearly_pnl.empty
    assert "drawdown" in result.equity_curve.columns
    assert "total_pnl" in result.summary
    assert (result.trade_log["side"] == "sell").any()
    assert result.trade_log["instrument"].str.contains("next_to_next_month").any()


def test_export_generates_excel_workbook():
    result = BacktestEngine(load_sample_data()).run(parse_strategy(BUILT_IN_STRATEGY_NAME))
    workbook = backtest_to_excel_bytes(result)
    assert workbook.startswith(b"PK")
    sheets = pd.read_excel(BytesIO(workbook), sheet_name=None)
    assert {"Summary", "Trade Log", "MTM", "Equity Curve", "Yearly PnL", "Monthly PnL"}.issubset(sheets)


def test_streamlit_app_import_smoke():
    import app

    assert callable(app.main)


def test_csv_validation_reports_missing_columns():
    bad_csv = StringIO("date,open\n2024-01-01,100\n")
    try:
        load_csv(bad_csv, required={"date", "close"}, name="Spot")
    except ValueError as exc:
        assert "Spot CSV missing columns: close" in str(exc)
    else:  # pragma: no cover - defensive assertion path
        raise AssertionError("Expected CSV validation to reject missing close column")
