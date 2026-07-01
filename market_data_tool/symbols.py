"""Symbol normalization helpers for Yahoo Finance symbols."""

from __future__ import annotations

from dataclasses import dataclass

NIFTY_50_ALIASES = {
    "NIFTY",
    "NIFTY50",
    "NIFTY 50",
    "NIFTY_50",
    "NSEI",
    "^NSEI",
}

EXCHANGE_SUFFIXES = {
    "NSE": ".NS",
    "BSE": ".BO",
}


@dataclass(frozen=True, slots=True)
class SymbolRequest:
    """A requested instrument and its Yahoo Finance-normalized symbol."""

    original: str
    yahoo_symbol: str
    exchange: str | None = None


def normalize_symbol(symbol: str, exchange: str | None = None) -> SymbolRequest:
    """Normalize a user-supplied symbol into Yahoo Finance notation.

    Supported conveniences:
    - Nifty 50 aliases resolve to ``^NSEI``.
    - ``NSE:RELIANCE`` and ``BSE:500325`` prefixes resolve to ``RELIANCE.NS``
      and ``500325.BO``.
    - CSV exchange hints of ``NSE`` or ``BSE`` append ``.NS``/``.BO`` when the
      symbol is not already a Yahoo Finance symbol.
    - Existing Yahoo suffixes and special symbols such as ``EURUSD=X``, ``GC=F``
      and ``^GSPC`` pass through unchanged.
    """
    raw = str(symbol).strip()
    hint = str(exchange).strip().upper() if exchange else None
    base = raw

    if ":" in raw:
        prefix, possible_symbol = raw.split(":", 1)
        prefix = prefix.strip().upper()
        if prefix in EXCHANGE_SUFFIXES:
            hint = prefix
            base = possible_symbol.strip()

    upper_base = base.upper().replace("-", " ").strip()
    compact_upper_base = upper_base.replace(" ", "")
    if upper_base in NIFTY_50_ALIASES or compact_upper_base in {alias.replace(" ", "") for alias in NIFTY_50_ALIASES}:
        return SymbolRequest(original=raw, yahoo_symbol="^NSEI", exchange="NSE")

    if _looks_like_yahoo_symbol(base):
        return SymbolRequest(original=raw, yahoo_symbol=base, exchange=hint)

    if hint in EXCHANGE_SUFFIXES:
        return SymbolRequest(original=raw, yahoo_symbol=f"{base}{EXCHANGE_SUFFIXES[hint]}", exchange=hint)

    return SymbolRequest(original=raw, yahoo_symbol=base, exchange=hint)


def _looks_like_yahoo_symbol(symbol: str) -> bool:
    return symbol.startswith("^") or "=" in symbol or "." in symbol or "-" in symbol
