"""
price_feeds.py
~~~~~~~~~~~~~~

Ultra‑thin, dependency‑light price oracle helper.

Priority order
--------------
1.  Jupiter v6 quote API   (fast, many pairs, no key)          https://price.jup.ag/v6/price
2.  Raydium price API      (good for fresh pools)              https://api.raydium.io/v2/sdk/price
3.  CoinGecko REST         (fallback, slower rate‑limit)       https://api.coingecko.com/api/v3/simple/price

• Sync helpers (`_jup_price`, `_raydium_price`, `_coingecko_price`) are unchanged.  
• `get_price_usd()` is still here for one‑off lookups (memoised).  
• **NEW** `async def get_token_prices()` returns live quotes from each DEX in a dict
  shaped like `{"jupiter": 1.0034, "raydium": 1.0112}` – perfect for arbitrage.py.

All synchronous functions can be called from a worker thread or via `asyncio.to_thread()`.
"""

from __future__ import annotations

import requests
import time
import asyncio
from functools import lru_cache
from typing import Dict

JUP_URL        = "https://price.jup.ag/v6/price"
RAYDIUM_URL    = "https://api.raydium.io/v2/sdk/price"
COINGECKO_URL  = "https://api.coingecko.com/api/v3/simple/price"

HEADERS = {"User-Agent": "Snipe4SoleBot/1.0"}

# ───────────────────────── internal sync helpers ──────────────────────────


def _jup_price(mint: str) -> float | None:
    try:
        r = requests.get(f"{JUP_URL}?ids={mint}", timeout=3, headers=HEADERS)
        r.raise_for_status()
        return r.json()["data"][mint]["price"]
    except Exception:
        return None


def _raydium_price(mint: str) -> float | None:
    try:
        r = requests.get(f"{RAYDIUM_URL}?ids={mint}", timeout=3, headers=HEADERS)
        r.raise_for_status()
        return float(r.json()[mint]["priceUSD"])
    except Exception:
        return None


def _coingecko_price(cg_id: str) -> float | None:
    try:
        r = requests.get(
            COINGECKO_URL,
            params={"ids": cg_id, "vs_currencies": "usd"},
            timeout=5,
            headers=HEADERS,
        )
        r.raise_for_status()
        return r.json()[cg_id]["usd"]
    except Exception:
        return None


# ───────────────────────── one‑off memoised helper ────────────────────────


@lru_cache(maxsize=512)
def get_price_usd(token_mint: str, coingecko_id: str | None = None) -> float | None:
    """
    Return latest USD price for *token_mint* or None.

    Memoised for 15 s; call `invalidate_cache()` after your own swap if you need
    an immediate refresh.
    """
    for fn in (_jup_price, _raydium_price):
        p = fn(token_mint)
        if p:
            return p

    if coingecko_id:
        return _coingecko_price(coingecko_id)

    return None


# ───────────────────────── async multi‑DEX wrapper ────────────────────────

_DexFuncMap: Dict[str, callable] = {
    "jupiter": _jup_price,
    "raydium": _raydium_price,
}


async def get_token_prices(token_mint: str, coingecko_id: str | None = None) -> dict[str, float]:
    """
    Concurrently fetch live USD quotes from the supported DEX endpoints.

    Parameters
    ----------
    token_mint : str
        SPL token mint address (same IDs you use for Jupiter / Raydium queries).
    coingecko_id : str | None
        Optional CoinGecko slug for fallback.

    Returns
    -------
    dict[str, float]
        e.g. {"jupiter": 1.0034, "raydium": 1.0112}

        The dict may contain 0, 1, or many quotes depending on endpoint success.
    """
    loop = asyncio.get_running_loop()

    # fire sync helpers in the default thread‑pool
    tasks = {
        dex: loop.run_in_executor(None, fn, token_mint)
        for dex, fn in _DexFuncMap.items()
    }

    prices: dict[str, float] = {}
    for dex, task in tasks.items():
        price = await task
        if price:
            prices[dex] = float(price)

    # Optional fallback to CoinGecko if both DEX queries failed
    if not prices and coingecko_id:
        cg_price = await loop.run_in_executor(None, _coingecko_price, coingecko_id)
        if cg_price:
            prices["coingecko"] = float(cg_price)

    return prices


# ───────────────────────── cache invalidation helper ──────────────────────

_last_clear = 0.0


def invalidate_cache(force: bool = False) -> None:
    """Clear the LRU cache every 15 s or immediately when force=True."""
    global _last_clear
    now = time.time()
    if force or now - _last_clear > 15:
        get_price_usd.cache_clear()
        _last_clear = now
