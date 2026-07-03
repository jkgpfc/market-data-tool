# Nifty 50 Futures & Options Backtester

A Streamlit application for event-driven Nifty 50 Futures & Options backtesting. Users can describe a constrained natural-language F&O strategy, upload Nifty spot/futures/options/expiry CSV files, run a backtest, inspect a dashboard, and download an Excel report.

## What this app supports

- Nifty spot, futures, options, and expiry calendar CSV upload.
- Built-in sample dataset under `sample_data/` for immediate local testing.
- Natural-language strategy parsing into structured rules for:
  - Monthly, weekly, next-month, and next-to-next-month contracts.
  - Call/put buy and sell legs.
  - Futures buy and sell legs.
  - Percentage move triggers.
  - No-repeat level logic.
  - Rollover after the 15th or another parsed day.
- Event-driven daily backtest loop.
- Brokerage, STT, GST, exchange fees, SEBI fees, stamp duty, slippage, and margin assumptions.
- Trade log, MTM table, equity curve, drawdown, yearly P&L, and monthly P&L.
- Dashboard charts and Excel export.

## Built-in sample strategy

The app includes **“1 Percent Monthly Call + Future Roll Strategy”**:

> When Nifty spot moves up 1 percent from the previous trigger level, buy one monthly call and buy one monthly future. Do not repeat the same trigger level. Rollover open futures after the 15th to next month.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the app

```bash
streamlit run app.py
```

Use the sidebar to select sample data or upload your own CSV files. Then choose the built-in strategy or enter a custom natural-language strategy and click **Run backtest**.

## CSV schemas

### Spot CSV

Required columns:

```text
date,close
```

Optional columns: `open`, `high`, `low`, `volume`.

### Futures CSV

Required columns:

```text
date,expiry,close
```

Optional columns: `open`, `high`, `low`, `volume`.

### Options CSV

Required columns:

```text
date,expiry,strike,option_type,close
```

`option_type` must be `CE` or `PE`. Optional columns: `open`, `high`, `low`, `volume`.

### Expiry calendar CSV

Required columns:

```text
expiry
```

Include weekly expiries where available. Monthly contracts are inferred as the last listed expiry for each calendar month.

## Example custom strategies

```text
If Nifty spot moves up 1 percent, buy 1 lot monthly call and buy 1 lot monthly future. No-repeat levels. Rollover after 15th.
```

```text
On a 2 percent down move, sell 1 lot weekly call and buy 1 lot weekly put. No repeat levels. Rollover after 15th.
```

```text
If Nifty moves up 1.5 percent, buy next month future and buy 1 percent OTM call.
```

## Project structure

```text
app.py                # Streamlit dashboard
backtest_engine.py    # Event-driven backtest engine
strategy_parser.py    # Natural-language strategy parser
data_loader.py        # CSV validation and loading
expiry_utils.py       # Expiry calendar and rollover helpers
instruments.py        # Domain models
costs.py             # Cost, slippage, and margin model
metrics.py            # Drawdown and P&L metrics
charts.py             # Plotly chart builders
export_utils.py       # Excel report export
sample_data/          # Built-in sample CSV files
tests/                # Automated tests
```

## Run tests

```bash
pytest
python -m compileall .
```

## Notes and limitations

- The parser is deterministic and intentionally constrained; it is designed for auditable strategy phrases rather than arbitrary LLM interpretation.
- If an exact option quote is missing, the engine uses a conservative intrinsic-value proxy so the sample app can continue to run. Production deployments should provide complete option-chain history.
- Transaction cost defaults are approximate and configurable in the Streamlit sidebar.
