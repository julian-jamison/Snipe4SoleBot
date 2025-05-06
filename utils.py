"""
utils.py
~~~~~~~~

Light helpers shared across Snipe4SoleBot.

Exports
-------
fetch_price(token_mint)            -> float | None   (async wrapper)
get_token_price(token_mint)        -> float | None   (sync)
should_buy_token(token_mint)       -> bool           (placeholder heuristic)
get_random_wallet()                -> Keypair        (dummy wallet picker)
log_trade_result(...)              -> None           (write to trade_log.jsonl)
"""

from __future__ import annotations

import asyncio
import json
import random
import time
from pathlib import Path
from typing import Any, Dict, Optional

from solders.keypair import Keypair

from decrypt_config import config
from price_feeds import get_price_usd

# ─── price helpers ────────────────────────────────────────────────────────


async def fetch_price(token_mint: str) -> Optional[float]:
    """Async wrapper so coroutine code can await a price lookup."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, get_price_usd, token_mint)


def get_token_price(token_mint: str) -> Optional[float]:
    """Synchronous convenience wrapper."""
    return get_price_usd(token_mint)


# ─── buy‑decision placeholder ─────────────────────────────────────────────


def should_buy_token(token_mint: str) -> bool:
    """
    Very naive heuristic:
      • token must have a price
      • price must be below 10 USD
    Replace with real logic (liquidity checks, anti‑rug rules, etc.).
    """
    price = get_price_usd(token_mint)
    return price is not None and price < 10


# ─── wallet picker ────────────────────────────────────────────────────────

_wallet_cache: list[Keypair] = []


def _load_hot_wallets() -> None:
    """
    Populate _wallet_cache with dummy Keypair objects so
    monitor_and_trade can call .pubkey() without errors.
    """
    if _wallet_cache:  # already loaded
        return

    for name in config["solana_wallets"]:
        if name.startswith("wallet_"):
            # NOTE: replace with real private keys if needed
            _wallet_cache.append(Keypair())


def get_random_wallet() -> Keypair:
    """Return a random wallet from the loaded list."""
    _load_hot_wallets()
    return random.choice(_wallet_cache)


# ─── trade logging ────────────────────────────────────────────────────────

_LOG_PATH = Path("trade_log.jsonl")


def log_trade_result(
    side: str,
    token: str,
    price: float,
    qty: float,
    pnl: float,
    status: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Append a JSON line with trade details for later analysis."""
    record: Dict[str, Any] = {
        "ts": int(time.time()),
        "side": side,
        "token": token,
        "price": price,
        "qty": qty,
        "pnl": pnl,
        "status": status,
    }
    if extra:
        record.update(extra)

    try:
        with _LOG_PATH.open("a") as fp:
            fp.write(json.dumps(record) + "\n")
    except Exception as exc:
        print(f"⚠️ Could not write trade log: {exc}")
