"""
utils.py
~~~~~~~~

Small, dependency‑light helpers used across Snipe4SoleBot.

Exports
-------
fetch_price(token_mint)            -> float | None   # async‑friendly wrapper
get_token_price(token_mint)        -> float | None
should_buy_token(token_mint)       -> bool           # naïve placeholder logic
get_random_wallet()                -> Keypair        # random hot wallet
log_trade_result(...)              -> None           # disk JSON audit (optional)
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, Optional

from price_feeds import get_price_usd
from decrypt_config import config
from solders.keypair import Keypair

# ─── price helpers ────────────────────────────────────────────────────────


async def fetch_price(token_mint: str) -> Optional[float]:
    """
    Async wrapper around price_feeds.get_price_usd so callers can `await`.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, get_price_usd, token_mint)


def get_token_price(token_mint: str) -> Optional[float]:
    """
    Synchronous convenience wrapper (used by monitor_and_trade.py).
    """
    return get_price_usd(token_mint)


# ─── buy‑decision placeholder ─────────────────────────────────────────────


def should_buy_token(token_mint: str) -> bool:
    """
    Very simple heuristic for demo purposes:
      • must have a price (oracle returns non‑None)
      • price must be below the configured max_gas_fee for illustration
    Replace with your real liquidity + on‑chain checks.
    """
    price = get_price_usd(token_mint)
    if price is None:
        return False

    max_gas_fee = config["trade_settings"]["max_gas_fee"]
    return price < max_gas_fee * 1_000  # totally arbitrary demo rule


# ─── wallet picker ────────────────────────────────────────────────────────


_wallet_cache: list[Keypair] = []


def _load_hot_wa_
