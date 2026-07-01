# Market Data Tool

A production-ready Python CLI for fetching global market data from Yahoo Finance, calculating common technical indicators, and exporting a formatted Excel workbook.

## Features

- Fetches Yahoo Finance data for globally supported instruments:
  - Stocks
  - Indices, including Nifty 50 via `NIFTY50`, `NIFTY 50`, or `^NSEI`
  - ETFs
  - Forex pairs
  - Commodities
  - Futures/F&O where Yahoo Finance publishes the symbol
- Normalizes common India market inputs:
  - `NSE:RELIANCE` -> `RELIANCE.NS`
  - `BSE:500325` -> `500325.BO`
  - CSV `exchange` column values of `NSE` or `BSE` append `.NS` or `.BO`
- Calculates, per symbol:
  - Current Market Price (CMP)
  - VWAP from recent intraday bars
  - Hourly RSI (14)
  - Daily RSI (14)
  - Weekly RSI (14)
  - Monthly RSI (14)
- Accepts symbols from command-line input and/or a CSV file.
- Exports a formatted `.xlsx` workbook with filters, frozen headers, and autosized columns.
- Uses structured modules, standard logging, and per-symbol graceful error handling.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Command-line symbols

```bash
python main.py AAPL ^GSPC SPY EURUSD=X GC=F NIFTY50 NSE:RELIANCE BSE:500325 --output market_data_output.xlsx
```

### CSV input

```bash
python main.py --csv sample_input.csv --output market_data_output.xlsx
```

### Ready-made Nifty 50 CSV for Indian users

The repository includes `nifty50_symbols.csv`, a ready-made file of the current Nifty 50 stock constituents in Yahoo Finance NSE format (`*.NS`). To fetch CMP, VWAP, and hourly/daily/weekly/monthly RSI for all 50 stocks:

```bash
python main.py --csv nifty50_symbols.csv --output nifty50_market_data.xlsx
```

To fetch only the Nifty 50 index itself, use the shortcut alias or Yahoo index symbol:

```bash
python main.py NIFTY50 --output nifty50_index.xlsx
python main.py ^NSEI --output nifty50_index.xlsx
```

For individual Indian stocks, pass the Yahoo symbol directly or use the built-in NSE/BSE shortcuts:

```bash
python main.py RELIANCE.NS TCS.NS HDFCBANK.NS --output india_stocks.xlsx
python main.py NSE:RELIANCE NSE:TCS BSE:500325 --output india_stocks.xlsx
```

### Combine command-line and CSV symbols

```bash
python main.py MSFT BTC-USD --csv sample_input.csv --output market_data_output.xlsx
```

The CSV reader prefers a `symbol` column and also accepts `ticker` or `instrument`. If none of those columns exist, the first column is used. An optional `exchange` column can contain `NSE` or `BSE` to normalize bare India-market symbols to Yahoo suffixes.

## Yahoo Finance Symbol Examples

| Asset type | Example symbols |
| --- | --- |
| US stocks | `AAPL`, `MSFT`, `TSLA` |
| Global stocks | `RELIANCE.NS`, `VOD.L`, `7203.T` |
| NSE/BSE shortcuts | `NSE:RELIANCE`, `BSE:500325`, or CSV rows with `exchange=NSE/BSE` |
| Indices | `^GSPC`, `^DJI`, `^NSEI`, `NIFTY50`, `^FTSE` |
| ETFs | `SPY`, `QQQ`, `EEM` |
| Forex | `EURUSD=X`, `GBPUSD=X`, `JPY=X` |
| Commodities/Futures | `GC=F`, `CL=F`, `SI=F`, `ES=F` |

Yahoo Finance coverage varies by exchange and instrument. Unsupported or delisted symbols are logged and exported with `status=error` instead of stopping the whole run.

## Data and Indicator Notes

- VWAP is calculated as an intraday bar approximation using `(High + Low + Close) / 3` weighted by volume over the current fetched session (`1d` of `5m` bars by default). Yahoo Finance does not provide exchange tick data through `yfinance`, so this should not be treated as official exchange VWAP.
- RSI(14) uses Wilder's smoothing: the initial average gain/loss is the simple average over the first 14 price changes, then subsequent values use Wilder's recursive formula.
- Hourly RSI uses Yahoo `1h` bars over `60d`; daily, weekly, and monthly RSI use `1d`, `1wk`, and `1mo` bars respectively.
- `yfinance` documents valid intervals of `1m`, `2m`, `5m`, `15m`, `30m`, `60m`, `90m`, `1h`, `1d`, `5d`, `1wk`, `1mo`, and `3mo`, with intraday data generally unable to extend beyond the last 60 days. Availability can still vary by exchange, asset class, and Yahoo endpoint behavior.

## Production Improvement Ideas

- Add retries with exponential backoff, request throttling, and local caching.
- Add a provider interface with licensed market-data fallbacks for production NSE/BSE/F&O coverage.
- Add exchange-calendar-aware session handling for exact VWAP windows.
- Add CI, packaging metadata, Docker support, and typed linting.
- Add persistent audit logs and structured JSON logs for observability.

## Output Columns

- `original_symbol`
- `symbol`
- `status`
- `cmp`
- `vwap`
- `hourly_rsi_14`
- `daily_rsi_14`
- `weekly_rsi_14`
- `monthly_rsi_14`
- `currency`
- `exchange`
- `instrument_type`
- `error`
- `fetched_at_utc`

## Logging

By default, logs are written to the console and `market_data_tool.log`.

```bash
python main.py --csv sample_input.csv --log-level DEBUG --log-file logs/market_data.log
```

## Project Structure

```text
market_data_tool/
  cli.py              # CLI orchestration
  config.py           # Defaults and constants
  data_source.py      # Yahoo Finance provider
  indicators.py       # RSI and VWAP calculations
  io.py               # CSV input and Excel output
  logging_config.py   # Logging setup
  models.py           # Result dataclass
main.py               # Entry point
sample_input.csv      # Mixed global example input
nifty50_symbols.csv   # Ready-made Nifty 50 stock CSV in Yahoo NSE format
requirements.txt      # Runtime dependencies
```

## Development Notes

- The Yahoo Finance provider is isolated in `market_data_tool.data_source.YahooFinanceProvider` so additional providers can be added later.
- Indicator functions are pure and testable.
- Symbol failures are captured at the result level for resilient batch processing.
- `nifty50_symbols.csv` was prepared for Indian users who want a one-command Nifty 50 stock scan; because Nifty 50 constituents are reviewed periodically, refresh this file against NSE/NSE Indices before relying on it for production workflows.
