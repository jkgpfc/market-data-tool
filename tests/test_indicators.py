import pandas as pd

from market_data_tool.indicators import rsi, vwap


def test_rsi_uses_wilder_reference_value():
    closes = pd.Series([
        44.34, 44.09, 44.15, 43.61, 44.33,
        44.83, 45.10, 45.42, 45.84, 46.08,
        45.89, 46.03, 45.61, 46.28, 46.28,
    ])

    assert rsi(closes, period=14) == 70.4641


def test_vwap_uses_typical_price_weighted_by_volume():
    frame = pd.DataFrame(
        {
            "High": [11.0, 12.0],
            "Low": [9.0, 10.0],
            "Close": [10.0, 11.0],
            "Volume": [100, 300],
        }
    )

    assert vwap(frame) == 10.75


def test_rsi_flat_series_is_neutral():
    assert rsi(pd.Series([10.0] * 20), period=14) == 50.0

def test_rsi_all_losses_is_zero():
    assert rsi(pd.Series(range(20, 0, -1)), period=14) == 0.0
