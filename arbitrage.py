# arbitrage.py
"""
Cross‑DEX arbitrage scanner/executor for Snipe4SoleBot.

Usage
-----
from arbitrage import start_arbitrage_loop
asyncio.create_task(start_arbitrage_loop())   # fire‑and‑forget inside your bot
"""

import asyncio, time, logging
from decimal import Decimal
from collections import deque
from typing import Dict, Tuple

from price_feeds import get_token_prices          # your price_feeds.py
from trade_execution import execute_trade          # async buy/sell helper :contentReference[oaicite:0]{index=0}:contentReference[oaicite:1]{index=1}
from portfolio import add_position, remove_position, get_position  :contentReference[oaicite:2]{index=2}:contentReference[oaicite:3]{index=3}
from telegram_notifications import safe_send_telegram_message
from decrypt_config import config

_LOG = logging.getLogger("arbitrage")

###############################################################################
# Config & constants
###############################################################################

ARBI_CFG = config.get("arbitrage_settings", {
    "min_spread_bps": 30,           # 0.30 % gross spread
    "max_slippage_bps": 100,        # 1 % slippage allowance
    "capital_per_trade_sol": 1.0,   # trade size
    "cooldown_seconds": 15,         # per‑token cooldown
    "poll_interval_sec": 3,         # how often to poll prices
})

# remember last trade to avoid spam
_last_trade_ts: Dict[str, float] = {}
_spread_history: Dict[str, deque] = {}

###############################################################################
# Helper utilities
###############################################################################

def _best_buy_sell(prices: Dict[str, float]) -> Tuple[Tuple[str, Decimal], Tuple[str, Decimal]]:
    """Return (dex_with_lowest_price, price), (dex_with_highest_price, price)."""
    dex_low = min(prices, key=prices.get)
    dex_high = max(prices, key=prices.get)
    return (dex_low, Decimal(prices[dex_low])), (dex_high, Decimal(prices[dex_high]))

def _bps(a: Decimal, b: Decimal) -> Decimal:
    """Return basis‑point spread between prices."""
    return (b - a) / a * Decimal(10_000)

###############################################################################
# Core logic
###############################################################################

async def try_arbitrage(token: str) -> None:
    prices = await get_token_prices(token)        # e.g. {"raydium":1.004, "orca":1.012}
    if len(prices) < 2:
        return

    (dex_buy, p_buy), (dex_sell, p_sell) = _best_buy_sell(prices)
    spread_bps = _bps(p_buy, p_sell)

    # Track recent spreads for optional analytics
    hist = _spread_history.setdefault(token, deque(maxlen=100))
    hist.append(float(spread_bps))

    if spread_bps < ARBI_CFG["min_spread_bps"]:
        return  # not big enough

    now = time.time()
    if now - _last_trade_ts.get(token, 0) < ARBI_CFG["cooldown_seconds"]:
        return  # still cooling down

    qty = ARBI_CFG["capital_per_trade_sol"] / float(p_buy)
    _LOG.info("⚖️  Arbitrage %s: buy %s @ %.6f, sell %s @ %.6f (%.2f bps)",
              token, dex_buy, p_buy, dex_sell, p_sell, spread_bps)

    await safe_send_telegram_message(
        f"⚖️  Arbitrage spotted on {token}: buy **{dex_buy}** @ {p_buy:.6f}, "
        f"sell **{dex_sell}** @ {p_sell:.6f} | spread {spread_bps:.1f} bps"
    )

    # Execute legs – buy then sell; if either leg fails we bail
    if await execute_trade("buy", token):            # leg 1
        add_position(token, qty, float(p_buy), dex_buy)
        if await execute_trade("sell", token):       # leg 2
            remove_position(token)
            await safe_send_telegram_message(f"✅ Arbitrage complete on {token} ({spread_bps:.1f} bps)")
        else:
            await safe_send_telegram_message(f"⚠️ Could not complete sell leg for {token}. Check manually!")

    _last_trade_ts[token] = now

###############################################################################
# Public API – background loop
###############################################################################

async def _runner(tokens: list[str]) -> None:
    while True:
        try:
            for t in tokens:
                await try_arbitrage(t)
        except Exception as exc:
            _LOG.exception("Arbitrage loop error: %s", exc)
            await safe_send_telegram_message(f"❌ Arbitrage loop error: {exc}")
        await asyncio.sleep(ARBI_CFG["poll_interval_sec"])

def start_arbitrage_loop(tokens: list[str] | None = None) -> asyncio.Task:
    """
    Launch the continuous arbitrage scanner.

    Parameters
    ----------
    tokens : list[str] | None
        Token symbols to scan.  If None, we fall back to `config["allowed_tokens"]`
        so you can reuse the list already loaded in bot.py :contentReference[oaicite:4]{index=4}:contentReference[oaicite:5]{index=5}.
    """
    tokens = tokens or config.get("allowed_tokens", [])
    if not tokens:
        raise ValueError("No tokens configured for arbitrage scanning.")
    return asyncio.create_task(_runner(tokens))
