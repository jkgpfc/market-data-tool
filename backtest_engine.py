"""Event-driven Nifty F&O backtesting engine."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from costs import CostModel
from data_loader import MarketDataBundle
from expiry_utils import should_rollover
from instruments import Instrument, InstrumentType, OptionType, Side, StrategyDefinition


@dataclass(slots=True)
class Position:
    instrument: Instrument
    entry_date: pd.Timestamp
    expiry: pd.Timestamp
    entry_price: float
    quantity: int
    side: Side
    strike: float | None = None
    last_price: float = 0.0

    @property
    def label(self) -> str:
        suffix = f" {self.strike:.0f}" if self.strike is not None else ""
        return f"{self.instrument.label}{suffix} exp {self.expiry.date()}"

    def mtm(self, price: float) -> float:
        return (price - self.entry_price) * self.quantity * self.side.sign


@dataclass(slots=True)
class BacktestResult:
    trade_log: pd.DataFrame
    mtm: pd.DataFrame
    equity_curve: pd.DataFrame
    yearly_pnl: pd.DataFrame
    monthly_pnl: pd.DataFrame
    summary: dict[str, float | int | str]


class BacktestEngine:
    """Simple event-driven engine over daily spot/futures/options bars."""

    def __init__(self, data: MarketDataBundle, cost_model: CostModel | None = None) -> None:
        self.data = data
        self.cost_model = cost_model or CostModel()

    def run(self, strategy: StrategyDefinition) -> BacktestResult:
        cash = strategy.initial_capital
        positions: list[Position] = []
        trade_rows: list[dict] = []
        mtm_rows: list[dict] = []
        used_levels: set[float] = set()
        reference_level: float | None = None

        spot = self.data.spot.dropna(subset=["date", "close"]).sort_values("date")
        if spot.empty:
            raise ValueError("Spot data is empty")

        for row in spot.itertuples(index=False):
            as_of = pd.Timestamp(row.date)
            spot_close = float(row.close)
            reference_level = spot_close if reference_level is None else reference_level

            # Roll and expire existing positions before fresh entries.
            for position in list(positions):
                price = self._price_position(position, as_of, spot_close)
                position.last_price = price
                if strategy.square_off_on_expiry and as_of >= position.expiry:
                    cash += self._close_position(position, as_of, price, "expiry", trade_rows)
                    positions.remove(position)
                elif position.instrument.instrument_type is InstrumentType.FUTURE and should_rollover(as_of, position.expiry, strategy.rollover_after_day):
                    cash += self._close_position(position, as_of, price, "rollover", trade_rows)
                    positions.remove(position)
                    new_position, cash_delta = self._open_position(position.instrument, strategy, as_of, spot_close, "rollover-entry")
                    if new_position:
                        positions.append(new_position)
                        cash += cash_delta
                        trade_rows.append(self._trade_row(new_position, as_of, "OPEN", "rollover-entry", -cash_delta))

            if self._triggered(strategy, spot_close, reference_level):
                level = round(reference_level * (1 + strategy.trigger.move_pct / 100), 2)
                if not strategy.trigger.no_repeat_levels or level not in used_levels:
                    for leg in strategy.legs:
                        position, cash_delta = self._open_position(leg, strategy, as_of, spot_close, "trigger")
                        if position:
                            positions.append(position)
                            cash += cash_delta
                            trade_rows.append(self._trade_row(position, as_of, "OPEN", "trigger", -cash_delta))
                    used_levels.add(level)
                    reference_level = spot_close

            open_mtm = sum(position.mtm(self._price_position(position, as_of, spot_close)) for position in positions)
            margin = self.cost_model.required_margin(sum(abs(p.quantity) // strategy.lot_size for p in positions))
            equity = cash + open_mtm
            mtm_rows.append({"date": as_of, "cash": cash, "open_mtm": open_mtm, "equity": equity, "margin_required": margin, "open_positions": len(positions)})

        final_date = pd.Timestamp(spot.iloc[-1]["date"])
        final_spot = float(spot.iloc[-1]["close"])
        for position in list(positions):
            price = self._price_position(position, final_date, final_spot)
            cash += self._close_position(position, final_date, price, "end-of-data", trade_rows)
            positions.remove(position)
        if mtm_rows:
            mtm_rows[-1]["cash"] = cash
            mtm_rows[-1]["open_mtm"] = 0.0
            mtm_rows[-1]["equity"] = cash
            mtm_rows[-1]["open_positions"] = 0

        trade_log = pd.DataFrame(trade_rows)
        mtm = pd.DataFrame(mtm_rows)
        equity_curve = mtm[["date", "equity"]].copy() if not mtm.empty else pd.DataFrame(columns=["date", "equity"])
        return _assemble_result(trade_log, mtm, equity_curve, strategy.initial_capital)

    def _triggered(self, strategy: StrategyDefinition, spot_close: float, reference: float) -> bool:
        pct_move = ((spot_close - reference) / reference) * 100
        direction = strategy.trigger.direction
        threshold = strategy.trigger.move_pct
        return (direction in {"up", "both"} and pct_move >= threshold) or (direction in {"down", "both"} and pct_move <= -threshold)

    def _open_position(self, instrument: Instrument, strategy: StrategyDefinition, as_of: pd.Timestamp, spot_close: float, reason: str) -> tuple[Position | None, float]:
        expiry = self.data.expiries.next_expiry(as_of, instrument.expiry_bucket)
        strike = self._select_strike(instrument, spot_close)
        price = self._lookup_price(instrument, as_of, expiry, spot_close, strike)
        if price is None:
            return None, 0.0
        exec_price = self.cost_model.execution_price(price, instrument.side.value)
        costs = self.cost_model.trade_cost(exec_price, instrument.quantity, instrument.side.value)
        if instrument.instrument_type is InstrumentType.FUTURE:
            trade_cashflow = -costs
        else:
            trade_cashflow = -exec_price * instrument.quantity * instrument.side.sign - costs
        position = Position(instrument, as_of, expiry, exec_price, instrument.quantity, instrument.side, strike, exec_price)
        return position, trade_cashflow

    def _close_position(self, position: Position, as_of: pd.Timestamp, price: float, reason: str, trade_rows: list[dict]) -> float:
        close_side = "sell" if position.side is Side.BUY else "buy"
        exec_price = self.cost_model.execution_price(price, close_side)
        costs = self.cost_model.trade_cost(exec_price, position.quantity, close_side)
        if position.instrument.instrument_type is InstrumentType.FUTURE:
            cashflow = (exec_price - position.entry_price) * position.quantity * position.side.sign - costs
        else:
            cashflow = exec_price * position.quantity * position.side.sign - costs
        trade_rows.append(self._trade_row(position, as_of, "CLOSE", reason, cashflow, exec_price, costs))
        return cashflow

    def _trade_row(self, position: Position, as_of: pd.Timestamp, action: str, reason: str, cashflow: float, price: float | None = None, costs: float | None = None) -> dict:
        return {
            "date": as_of,
            "action": action,
            "reason": reason,
            "instrument": position.label,
            "side": position.side.value,
            "quantity": position.quantity,
            "expiry": position.expiry,
            "strike": position.strike,
            "price": position.entry_price if price is None else price,
            "costs": costs if costs is not None else self.cost_model.trade_cost(position.entry_price, position.quantity, position.side.value),
            "cashflow": cashflow,
        }

    def _price_position(self, position: Position, as_of: pd.Timestamp, spot_close: float) -> float:
        return self._lookup_price(position.instrument, as_of, position.expiry, spot_close, position.strike) or position.last_price or position.entry_price

    def _lookup_price(self, instrument: Instrument, as_of: pd.Timestamp, expiry: pd.Timestamp, spot_close: float, strike: float | None) -> float | None:
        if instrument.instrument_type is InstrumentType.FUTURE:
            frame = self.data.futures[(self.data.futures["date"] == as_of) & (self.data.futures["expiry"] == expiry)]
            return float(frame.iloc[-1]["close"]) if not frame.empty else spot_close
        if instrument.instrument_type is InstrumentType.OPTION:
            frame = self.data.options[
                (self.data.options["date"] == as_of)
                & (self.data.options["expiry"] == expiry)
                & (self.data.options["option_type"] == (instrument.option_type or OptionType.CALL).value)
                & (self.data.options["strike"] == strike)
            ]
            if not frame.empty:
                return float(frame.iloc[-1]["close"])
            return _intrinsic_proxy(spot_close, strike or spot_close, instrument.option_type or OptionType.CALL)
        return spot_close

    def _select_strike(self, instrument: Instrument, spot_close: float) -> float | None:
        if instrument.instrument_type is not InstrumentType.OPTION:
            return None
        raw = spot_close * (1 + instrument.strike_offset_pct / 100)
        return round(raw / 50) * 50


def _intrinsic_proxy(spot: float, strike: float, option_type: OptionType) -> float:
    intrinsic = max(0.0, spot - strike) if option_type is OptionType.CALL else max(0.0, strike - spot)
    return round(intrinsic + max(5.0, spot * 0.002), 2)


def _assemble_result(trade_log: pd.DataFrame, mtm: pd.DataFrame, equity_curve: pd.DataFrame, initial_capital: float) -> BacktestResult:
    from metrics import calculate_drawdown, monthly_pnl, summarize_performance, yearly_pnl

    if not equity_curve.empty:
        equity_curve["drawdown"] = calculate_drawdown(equity_curve["equity"])
    yearly = yearly_pnl(equity_curve)
    monthly = monthly_pnl(equity_curve)
    summary = summarize_performance(equity_curve, trade_log, initial_capital)
    return BacktestResult(trade_log=trade_log, mtm=mtm, equity_curve=equity_curve, yearly_pnl=yearly, monthly_pnl=monthly, summary=summary)
