"""
portfolio.py
~~~~~~~~~~~~

Lightweight position store backed by a JSON file.

• Thread‑safe: uses a global `threading.Lock()` so concurrent reads/writes from
  the sniper thread, arbitrage loop, or web dashboard don’t corrupt the file.
• Helpers:
    add_position(token, qty, price, dex)
    remove_position(token)
    get_position(token)              -> None | dict
    get_all_positions()              -> dict
    reset_portfolio()                -> wipes file (use with care)
• Prices rounded to 6 decimals; quantities preserved in full precision.
"""

from __future__ import annotations

import json
import os
import threading
from decimal import Decimal
from typing import Dict

PORTFOLIO_FILE = "portfolio.json"
_LOCK          = threading.Lock()      # ensures atomic file operations


# ───────────────────────── internal helpers ──────────────────────────────

def _read() -> Dict[str, dict]:
    if not os.path.exists(PORTFOLIO_FILE):
        return {}
    with _LOCK, open(PORTFOLIO_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # corrupted / empty file – start fresh but keep a backup
            os.rename(PORTFOLIO_FILE, PORTFOLIO_FILE + ".bak")
            return {}


def _write(obj: Dict[str, dict]) -> None:
    tmp = PORTFOLIO_FILE + ".tmp"
    with _LOCK, open(tmp, "w") as f:
        json.dump(obj, f, indent=4)
    os.replace(tmp, PORTFOLIO_FILE)   # atomic on POSIX


# ───────────────────────── public API ────────────────────────────────────

def add_position(token: str, quantity: float, price: float, dex: str) -> None:
    """
    Merge a buy leg into the portfolio, computing a new average cost basis.
    """
    pf = _read()
    if token in pf:
        old          = pf[token]
        total_qty    = Decimal(str(old["quantity"])) + Decimal(str(quantity))
        avg_price    = (
            Decimal(str(old["price"])) * Decimal(str(old["quantity"])) +
            Decimal(str(price)) * Decimal(str(quantity))
        ) / total_qty
        pf[token]["quantity"] = float(total_qty)
        pf[token]["price"]    = round(float(avg_price), 6)
    else:
        pf[token] = {
            "quantity": float(quantity),
            "price":    round(float(price), 6),
            "dex":      dex
        }
    _write(pf)


def remove_position(token: str) -> None:
    pf = _read()
    if token in pf:
        del pf[token]
        _write(pf)


def get_position(token: str) -> dict | None:
    return _read().get(token)


def get_all_positions() -> Dict[str, dict]:
    return _read()


def reset_portfolio() -> None:
    """Dangerous: wipe all positions (used for testing)."""
    _write({})


# ───────────────────────── cli helper (optional) ─────────────────────────
if __name__ == "__main__":
    import pprint, sys
    cmd = sys.argv[1:] and sys.argv[1] or "show"
    if cmd == "show":
        pprint.pprint(get_all_positions())
    elif cmd == "reset":
        reset_portfolio()
        print("Portfolio reset.")
