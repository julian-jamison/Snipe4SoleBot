"""
price_feeds.py
~~~~~~~~~~~~~~

Ultra‑thin, dependency‑light price oracle helper.

Priority order
--------------
1.  Jupiter v6 quote API   (fast, many pairs, no key)          https://price.jup.ag/v6/price
2.  Raydium price API      (good for fresh pools)              https://api.raydium.io/v2/sdk/price
3.  CoinGecko REST         (fallback, slower rate‑limit)       https://api.coingecko.com/api/v3/simple/price

All functions are **synchronous** – call from worker thread / asyncio.to_thread().
"""

from __future__ import annotations

import requests
import time
from functools import lru_cache

JUP_URL   = "https://price.jup.ag/v6/price"
RAYDIUM_URL = "https://api.raydium.io/v2/sdk/price"
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

HEADERS = {"User-Agent": "Snipe4SoleBot/1.0"}

# --- helpers ---------------------------------------------------------------

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


# --- public API ------------------------------------------------------------

@lru_cache(maxsize=512)
def get_price_usd(token_mint: str, coingecko_id: str | None = None) -> float | None:
    """
    Return latest USD price or None.

    Memoised for 15 s; call `invalidate_cache()` after a swap.
    """
    for fn in (_jup_price, _raydium_price):
        p = fn(token_mint)
        if p:
            return p

    if coingecko_id:
        return _coingecko_price(coingecko_id)

    return None


_last_clear = 0.0


def invalidate_cache(force: bool = False) -> None:
    """Clear LRU every 15 s or when force=True."""
    global _last_clear
    now = time.time()
    if force or now - _last_clear > 15:
        get_price_usd.cache_clear()
        _last_clear = now
