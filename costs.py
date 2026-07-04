"""Indian F&O transaction cost and margin model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CostModel:
    """Configurable brokerage, tax, slippage, and margin assumptions."""

    brokerage_per_order: float = 20.0
    stt_rate_sell: float = 0.0005
    exchange_txn_rate: float = 0.000035
    sebi_rate: float = 0.000001
    stamp_duty_buy_rate: float = 0.00003
    gst_rate: float = 0.18
    slippage_bps: float = 2.0
    margin_per_lot: float = 150_000.0

    def execution_price(self, price: float, side: str) -> float:
        """Apply slippage against the trader."""
        multiplier = 1 + self.slippage_bps / 10_000 if side == "buy" else 1 - self.slippage_bps / 10_000
        return round(price * multiplier, 4)

    def trade_cost(self, price: float, quantity: int, side: str) -> float:
        """Calculate approximate transaction costs for one executed order."""
        turnover = abs(price * quantity)
        brokerage = min(self.brokerage_per_order, turnover * 0.0003)
        exchange = turnover * self.exchange_txn_rate
        sebi = turnover * self.sebi_rate
        stt = turnover * self.stt_rate_sell if side == "sell" else 0.0
        stamp = turnover * self.stamp_duty_buy_rate if side == "buy" else 0.0
        gst = (brokerage + exchange) * self.gst_rate
        return round(brokerage + exchange + sebi + stt + stamp + gst, 2)

    def required_margin(self, lots: int) -> float:
        return lots * self.margin_per_lot
