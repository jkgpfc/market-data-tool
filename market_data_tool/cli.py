"""Command-line interface for the market data tool."""

from __future__ import annotations

import argparse
import logging
import sys

from .config import DEFAULT_LOG_FILE, DEFAULT_OUTPUT_FILE
from .data_source import YahooFinanceProvider
from .io import export_to_excel, merge_symbols, read_symbols_from_csv
from .logging_config import configure_logging

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch global market data from Yahoo Finance and export indicators to Excel.",
    )
    parser.add_argument("symbols", nargs="*", help="Symbols, e.g. AAPL ^GSPC EURUSD=X GC=F NIFTY50 NSE:RELIANCE BSE:500325")
    parser.add_argument("--csv", dest="csv_path", help="CSV file containing a symbol/ticker/instrument column")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_FILE, help=f"Excel output path (default: {DEFAULT_OUTPUT_FILE})")
    parser.add_argument("--log-file", default=DEFAULT_LOG_FILE, help=f"Log file path (default: {DEFAULT_LOG_FILE})")
    parser.add_argument("--log-level", default="INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR"), help="Logging level")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.log_level, args.log_file)

    try:
        csv_symbols = read_symbols_from_csv(args.csv_path) if args.csv_path else []
        symbols = merge_symbols(args.symbols, csv_symbols)
        if not symbols:
            LOGGER.error("No symbols supplied. Provide positional symbols or --csv input.")
            return 2

        provider = YahooFinanceProvider()
        results = []
        for symbol in symbols:
            LOGGER.info("Processing %s as %s", symbol.original, symbol.yahoo_symbol)
            results.append(provider.fetch_symbol(symbol))

        output_path = export_to_excel(results, args.output)
        ok_count = sum(1 for result in results if result.status == "ok")
        LOGGER.info("Exported %d rows (%d successful, %d errors) to %s", len(results), ok_count, len(results) - ok_count, output_path)
        return 0 if ok_count else 1
    except Exception:  # noqa: BLE001 - top-level graceful CLI handling.
        LOGGER.exception("Application failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
