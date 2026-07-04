from io import BytesIO, StringIO

import pandas as pd

from backtest_engine import BacktestEngine
from data_loader import load_csv, load_sample_data
from expiry_utils import ExpiryCalendar
from export_utils import backtest_to_excel_bytes
from instruments import InstrumentType, OptionType, Side
import pandas as pd

from backtest_engine import BacktestEngine
from data_loader import load_sample_data
from expiry_utils import ExpiryCalendar
from strategy_parser import BUILT_IN_STRATEGY_NAME, parse_strategy


def test_builtin_strategy_parser():
    strategy = parse_strategy(BUILT_IN_STRATEGY_NAME)
    assert strategy.trigger.move_pct == 1.0
    assert strategy.trigger.direction == "up"
    assert strategy.rollover_after_day == 15
    assert len(strategy.legs) == 2
    option_leg, future_leg = strategy.legs
    assert option_leg.instrument_type is InstrumentType.OPTION
    assert option_leg.option_type is OptionType.CALL
    assert option_leg.side is Side.SELL
    assert future_leg.instrument_type is InstrumentType.FUTURE
    assert future_leg.side is Side.BUY
    assert len(strategy.legs) == 2
    assert strategy.rollover_after_day == 15


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


def test_sample_backtest_runs_with_required_outputs():
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
    assert "total_pnl" in result.summary
