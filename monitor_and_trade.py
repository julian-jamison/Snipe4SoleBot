from __future__ import annotations

"""
monitor_and_trade.py
~~~~~~~~~~~~~~~~~~~~

• Runs the synchronous **sniper loop** in its own daemon thread
• Starts the async **arbitrage loop** (from arbitrage.py) in the main event‑loop
• Provides helpers to send Telegram messages safely from both sync & async code
"""

import asyncio
import logging
import threading
import time
from typing import List, Dict, Any

from mempool_monitor import get_new_liquidity_pools
from trade_execution import buy_token_multi_wallet, sell_token_auto_withdraw
from whale_tracking import get_whale_transactions
from telegram_notifications import safe_send_telegram_message
from utils import get_token_price, should_buy_token, get_random_wallet
from arbitrage import start_arbitrage_loop

_LOG = logging.getLogger("monitor_and_trade")

# ─── telegram helpers ──────────────────────────────────────────────────────

def _tell(message: str) -> None:
    """Thread‑safe wrapper (fire‑and‑forget) for synchronous code."""
    asyncio.create_task(safe_send_telegram_message(message))

async def _tell_async(message: str) -> None:
    """Awaitable helper for async code (rarely used here)."""
    await safe_send_telegram_message(message)

# ─── main sniper loop (runs in a thread) ───────────────────────────────────

def _sniper_loop() -> None:
    _LOG.info("🚀 Sniper bot running with Automatic Withdrawals…")
    _tell("🚀 Snipe4SoleBot is LIVE and scanning for new liquidity pools!")

    while True:
        try:
            new_pools: List[Dict[str, Any]] = get_new_liquidity_pools() or []
        except Exception as exc:
            _LOG.warning("mempool fetch failed: %s", exc)
            _tell(f"⚠️ mempool fetch failed: {exc}")
            new_pools = []

        for pool in new_pools:
            token = pool.get("baseMint") or pool.get("mint")
            if not token:
                continue

            _LOG.info("🔹 New liquidity detected: %s", token)
            _tell(f"🚀 New liquidity detected: {token}")

            # whale tracking (optional)
            try:
                buys, sells = asyncio.run(get_whale_transactions(token))
                if buys > 100:
                    _tell(f"🐋 WHALE ALERT! {buys} SOL in buys")
                if sells > 50:
                    _tell(f"⚠️ Whale sold {sells} SOL")
            except Exception as _:
                _LOG.debug("whale_tracking failed for %s", token)

            # buy decision
            if should_buy_token(token):
                wallet = get_random_wallet()
                _tell(f"🛒 Buying {token} with wallet {wallet.pubkey()}")

                asyncio.run(buy_token_multi_wallet(token, wallet))
                entry_price = get_token_price(token) or 0

                # monitor price
                while True:
                    price = get_token_price(token)
                    if not price:
                        time.sleep(2)
                        continue

                    pct = (price - entry_price) / entry_price * 100
                    if pct >= 10 or pct <= -5:
                        asyncio.run(sell_token_auto_withdraw(token, wallet))
                        outcome = "profit" if pct >= 0 else "loss"
                        _tell(f"💸 Sold {token} for {pct:.2f}% {outcome}.")
                        break
                    time.sleep(2)
            else:
                _tell(f"❌ Skipping {token}. Doesn’t meet buy criteria.")
        time.sleep(1)

# ─── thread launcher ──────────────────────────────────────────────────────

def start_sniper_thread() -> threading.Thread:
    """Launch the sniper loop in a background daemon thread."""
    thread = threading.Thread(target=_sniper_loop, name="SniperLoop", daemon=True)
    thread.start()
    return thread

# ─── async arbitrage orchestrator ──────────────────────────────────────────

async def _run_async_tasks() -> None:
    start_arbitrage_loop()
    _LOG.info("⚖️  Arbitrage loop started.")
    while True:
        await asyncio.sleep(3600)


def start_all() -> None:
    """Launch both sniper thread and arbitrage loop."""
    start_sniper_thread()
    try:
        asyncio.run(_run_async_tasks())
    except KeyboardInterrupt:
        _LOG.info("Shutting down…")
