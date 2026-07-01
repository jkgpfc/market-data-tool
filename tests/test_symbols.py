from market_data_tool.io import merge_symbols, read_symbols_from_csv
from market_data_tool.symbols import normalize_symbol


def test_normalize_nifty_aliases():
    assert normalize_symbol("Nifty 50").yahoo_symbol == "^NSEI"
    assert normalize_symbol("NIFTY50").yahoo_symbol == "^NSEI"


def test_normalize_nse_and_bse_prefixes():
    assert normalize_symbol("NSE:RELIANCE").yahoo_symbol == "RELIANCE.NS"
    assert normalize_symbol("BSE:500325").yahoo_symbol == "500325.BO"


def test_normalize_exchange_hint():
    assert normalize_symbol("TCS", "NSE").yahoo_symbol == "TCS.NS"
    assert normalize_symbol("500325", "BSE").yahoo_symbol == "500325.BO"


def test_merge_symbols_deduplicates_normalized_symbols():
    merged = merge_symbols(["NIFTY50", "NSE:RELIANCE"], [normalize_symbol("^NSEI"), normalize_symbol("RELIANCE", "NSE")])
    assert [item.yahoo_symbol for item in merged] == ["^NSEI", "RELIANCE.NS"]


def test_read_symbols_from_csv_with_exchange_hint(tmp_path):
    csv_path = tmp_path / "symbols.csv"
    csv_path.write_text("symbol,exchange\nRELIANCE,NSE\n500325,BSE\n", encoding="utf-8")

    assert [item.yahoo_symbol for item in read_symbols_from_csv(csv_path)] == ["RELIANCE.NS", "500325.BO"]
