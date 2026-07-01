import csv
from pathlib import Path

from market_data_tool.io import read_symbols_from_csv


def test_nifty50_csv_contains_50_yahoo_nse_symbols():
    csv_path = Path("nifty50_symbols.csv")
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))

    assert len(rows) == 50
    assert all(row["symbol"].endswith(".NS") for row in rows)
    assert all(row["exchange"] == "NSE" for row in rows)
    assert len({row["symbol"] for row in rows}) == 50


def test_nifty50_csv_is_read_without_suffix_mutation():
    symbols = read_symbols_from_csv("nifty50_symbols.csv")

    assert len(symbols) == 50
    assert symbols[0].yahoo_symbol == "RELIANCE.NS"
    assert symbols[-1].yahoo_symbol == "TATACONSUM.NS"
