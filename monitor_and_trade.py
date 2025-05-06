"""
monitor_and_trade.py
~~~~~~~~~~~~~~~~~~~~

• Starts the live‐liquidity **sniper loop** (runs in a daemon thread).
• Starts the async **arbitrage loop** from arbitrage.py (runs in the
  main asyncio event‑loop).
• Provides helpers for sending Telegram notifications safely from both
  sync threads and async tasks.
"""

from __future__ import annotations

import time
import asyncio
import threading
import logging

from mempool_monitor import get_new_liquidity_pools
from trade_execution import buy_token_multi_wallet, sell_token_auto_withdraw
from whale_tracking import get_whale_transactions
from telegram_notifications import safe_send_telegram_message
from utils import get_token_price, should_buy_token, get_random_wallet
from arbitrage import start_arbitrage_loop           # NEW ⭐

_LOG = logging.getLogger("monitor_and_trade")

# ───────────────────────── shared Telegram helper ──────────────────────────


def send_telegram_message_sync(message: str) -> None:
    """
    Thread‑safe helper for synchronous contexts (sniper loop).

    If we’re already inside an event‑loop, schedule a coroutine task;
    otherwise spin up a one‑shot loop to send the message.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(safe_send_telegram_message(message))
    except RuntimeError:  # no running loop in this thread
        asyncio.run(safe_send_telegram_message(message))


async def send_telegram_message_async(message: str) -> None:
    """Awaitable helper for async contexts."""
    await safe_send_telegram_message(message)

# ───────────────────────── sniper (sync) loop ──────────────────────────────


def sniper_loop() -> None:
    """Main liquidity‑sniping loop with auto‑withdrawals (runs in thread)."""
    _LOG.info("🚀 Sniper bot running with Automatic Withdrawals…")
    send_telegram_message_sync("🚀 Snipe4SoleBot is LIVE and scanning for new liquidity pools!")

    while True:
        new_pools = get_new_liquidity_pools()  # sync helper

        for pool in new_pools:
            token_address = pool.get("baseMint") or pool.get("mint")
            if not token_address:
                continue

            _LOG.info("🔹 New liquidity detected: %s", token_address)
            send_telegram_message_sync(f"🚀 New liquidity detected: {token_address}")

            # Whale activity
            whale_buys, whale_sells = get_whale_transactions(token_address)
            if whale_buys > 100:
                send_telegram_message_sync(f"🐋 WHALE ALERT! {whale_buys} SOL in buys")
            if whale_sells > 50:
                send_telegram_message_sync(f"⚠️ Warning! {whale_sells} SOL in sells")

            # Buy decision
            if should_buy_token(token_address):
                selected_wallet = get_random_wallet()
                send_telegram_message_sync(f"🛒 Buying {token_address} with wallet {selected_wallet.pubkey()}.")

                buy_token_multi_wallet(token_address, selected_wallet)
                initial_price = get_token_price(token_address)

                # Price monitor – auto‑sell in‑place
                while True:
                    current_price = get_token_price(token_address)
                    if not current_price:
                        time.sleep(2)
                        continue

                    profit_pct = (current_price - initial_price) / initial_price * 100
                    if profit_pct >= 10:
                        sell_token_auto_withdraw(token_address, selected_wallet)
                        send_telegram_message_sync(f"✅ Sold {token_address} for {profit_pct:.2f}% profit! Profits withdrawn.")
                        break
                    elif profit_pct <= -5:
                        sell_token_auto_withdraw(token_address, selected_wallet)
                        send_telegram_message_sync(f"❌ Stop‑loss! Sold {token_address} at {profit_pct:.2f}% loss.")
                        break

                    time.sleep(2)
            else:
                send_telegram_message_sync(f"❌ Skipping {token_address}. Doesn’t meet buy criteria.")

        time.sleep(1)

# ───────────────────────── orchestrator ────────────────────────────────────


def start_sniper_thread() -> threading.Thread:
    """Launch the synchronous sniper loop in a daemon thread."""
    thread = threading.Thread(target=sniper_loop, daemon=True, name="SniperLoop")
    thread.start()
    return thread


async def _run_async_tasks() -> None:
    """
    Entrypoint for the main asyncio event‑loop.

    • Starts arbitrage scanning (returns a background Task)
    • Keeps the loop alive forever.
    """
    start_arbitrage_loop()  # from arbitrage.py – returns a Task, we don’t need the handle
    _LOG.info("⚖️  Arbitrage loop started.")
    while True:
        await asyncio.sleep(3600)  # keep loop alive


def start_all() -> None:
    """
    Call this from your main `bot.py` (or __main__) to launch everything:

    >>> from monitor_and_trade import start_all
    >>> start_all()
    """
    # 1. start sniper (sync) thread
    start_sniper_thread()

    # 2. run async arbitrage loop in the main thread
    try:
        asyncio.run(_run_async_tasks())
    except KeyboardInterrupt:
        _LOG.info("Shutting down…")


# If you prefer this module to be executable directly, uncomment:
# if __name__ == "__main__":
#     start_all()
