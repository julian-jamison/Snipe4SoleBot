"""
telegram_command_handler.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Lightweight command interface for Snipe4SoleBot via Telegram Bot API.
"""

from __future__ import annotations

import json
import os
import time
import asyncio
import aiohttp
import threading
from typing import Tuple

from telegram.request import HTTPXRequest as AiohttpRequest
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from decrypt_config import config

# ─── constants ────────────────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN = config["telegram"]["bot_token"]
TELEGRAM_CHAT_ID   = config["telegram"]["chat_id"]

STATUS_FILE    = "bot_status.json"
PORTFOLIO_FILE = "portfolio.json"
WALLETS_FILE   = "wallets.json"
LOG_FILE       = "logs/agent_activity.log"

telegram_listener_started = False

# ─── Telegram helpers ─────────────────────────────────────────────────────

async def _create_session() -> Tuple[Bot, aiohttp.ClientSession]:
    session = aiohttp.ClientSession()
    request = AiohttpRequest(session)
    bot     = Bot(token=TELEGRAM_BOT_TOKEN, request=request)
    return bot, session


def schedule_safe_telegram_message(message: str) -> None:
    """Thread‑safe wrapper to send a Telegram message from sync code."""
    def _runner():
        try:
            asyncio.run(safe_send_telegram_message(message))
        except RuntimeError as exc:
            print(f"⚠️ Telegram loop fallback error: {exc}")

    threading.Thread(target=_runner, daemon=True).start()


async def safe_send_telegram_message(message: str) -> None:
    print(f"🔄 Sending Telegram message: {message[:40]!r}…")
    try:
        bot, session = await _create_session()
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        await session.close()
        print("📩 Telegram message sent.")
    except Exception as exc:
        print(f"❌ Telegram send failed: {exc}")


# ─── command callbacks ────────────────────────────────────────────────────

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return
    print(f"📩 /status from chat_id={update.effective_chat.id}")

    try:
        with open(STATUS_FILE, "r") as f:
            status_data = json.load(f)
        uptime = round((time.time() - status_data["start_time"]) / 60, 2)

         msg = (
            f"📈 Bot Status:\n"
            f"• Uptime: {uptime} mins\n"
            f"• Trades: {status_data['trade_count']}\n"
            f"• Profit: {status_data['profit']} SOL"
        )
