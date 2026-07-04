"""Natural-language strategy parser for Nifty F&O strategies."""

from __future__ import annotations

import re

from instruments import Instrument, InstrumentType, OptionType, Side, StrategyDefinition, TriggerRule

BUILT_IN_STRATEGY_NAME = "1 Percent Monthly Call + Future Roll Strategy"
BUILT_IN_STRATEGY_TEXT = (
    "When Nifty spot moves up 1 percent from the last executed level, sell one selected monthly call and buy "
    "one Nifty future. Do not repeat the same trigger level. After the 15th of each month, use "
    "next-to-next-month option and future contracts. Continue until the backtest end date."
)


def built_in_strategy() -> StrategyDefinition:
    """Return the requested built-in strategy definition."""
    return StrategyDefinition(
        name=BUILT_IN_STRATEGY_NAME,
        description=BUILT_IN_STRATEGY_TEXT,
        legs=(
            Instrument(InstrumentType.OPTION, Side.SELL, quantity=50, expiry_bucket="monthly", option_type=OptionType.CALL),
            Instrument(InstrumentType.FUTURE, Side.BUY, quantity=50, expiry_bucket="monthly"),
        ),
        trigger=TriggerRule(move_pct=1.0, direction="up", no_repeat_levels=True),
        rollover_after_day=15,
    )


def parse_strategy(text: str, *, lot_size: int = 50, initial_capital: float = 1_000_000.0) -> StrategyDefinition:
    """Parse a constrained natural-language F&O strategy into structured rules.

    The parser is intentionally deterministic and transparent. It supports phrases for call/put
    buy/sell, futures buy/sell, weekly/monthly/next-month/next-to-next-month expiries,
    percentage move triggers, no-repeat levels, and rollover-after-day rules.
    """
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        raise ValueError("Strategy text cannot be blank")
    lowered = cleaned.lower()

    if lowered in {BUILT_IN_STRATEGY_NAME.lower(), "built in", "sample"}:
        return built_in_strategy()

    expiry_bucket = _parse_expiry_bucket(lowered)
    quantity = _parse_quantity(lowered, lot_size)
    legs = tuple(_parse_legs(lowered, quantity, expiry_bucket))
    if not legs:
        raise ValueError("No tradable legs found. Include phrases like 'buy call', 'sell put', or 'buy future'.")

    trigger = TriggerRule(
        move_pct=_parse_move_pct(lowered),
        direction=_parse_direction(lowered),
        no_repeat_levels="repeat" not in lowered or "no repeat" in lowered or "no-repeat" in lowered,
    )
    rollover_after_day = _parse_rollover_day(lowered)

    return StrategyDefinition(
        name=_title_from_text(cleaned),
        description=cleaned,
        legs=legs,
        trigger=trigger,
        rollover_after_day=rollover_after_day,
        initial_capital=initial_capital,
        lot_size=lot_size,
    )


def _parse_legs(text: str, quantity: int, expiry_bucket: str) -> list[Instrument]:
    legs: list[Instrument] = []
    option_patterns = ((OptionType.CALL, r"\b(call|ce)\b"), (OptionType.PUT, r"\b(put|pe)\b"))
    for option_type, option_pattern in option_patterns:
        if re.search(option_pattern, text):
            side = Side.SELL if re.search(rf"\b(sell|short|write)\b[^.]*{option_pattern}", text) else Side.BUY
            legs.append(Instrument(InstrumentType.OPTION, side, quantity, expiry_bucket, option_type, _parse_strike_offset(text)))
    if re.search(r"\b(future|futures|fut)\b", text):
        side = Side.SELL if re.search(r"\b(sell|short)\b[^.]*\b(future|futures|fut)\b", text) else Side.BUY
        legs.append(Instrument(InstrumentType.FUTURE, side, quantity, expiry_bucket))
    return legs


def _parse_expiry_bucket(text: str) -> str:
    if "next to next" in text or "next-to-next" in text:
        return "next_to_next_month"
    if "next month" in text or "next-month" in text:
        return "next_month"
    if "weekly" in text or "week" in text:
        return "weekly"
    return "monthly"


def _parse_quantity(text: str, lot_size: int) -> int:
    lot_match = re.search(r"(\d+)\s*(lot|lots)", text)
    if lot_match:
        return int(lot_match.group(1)) * lot_size
    qty_match = re.search(r"(\d+)\s*(qty|quantity|contracts)", text)
    if qty_match:
        return int(qty_match.group(1))
    return lot_size


def _parse_move_pct(text: str) -> float:
    pct_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent|per cent)", text)
    return float(pct_match.group(1)) if pct_match else 1.0


def _parse_direction(text: str) -> str:
    if "down" in text or "fall" in text or "drops" in text:
        return "down"
    if "both" in text or "either direction" in text:
        return "both"
    return "up"


def _parse_rollover_day(text: str) -> int:
    rollover_match = re.search(r"roll(?:over)?[^0-9]*(\d{1,2})(?:st|nd|rd|th)?", text)
    if rollover_match:
        return max(1, min(28, int(rollover_match.group(1))))
    if "after the 15" in text or "after 15" in text:
        return 15
    return 15


def _parse_strike_offset(text: str) -> float:
    otm_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent|per cent)\s*otm", text)
    itm_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent|per cent)\s*itm", text)
    if otm_match:
        return float(otm_match.group(1))
    if itm_match:
        return -float(itm_match.group(1))
    return 0.0


def _title_from_text(text: str) -> str:
    return text[:80] + ("..." if len(text) > 80 else "")
