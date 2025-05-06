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
    """Thread‑safe helper to send a Telegram message from sync code."""
    def _runner() -> None:
        try:
            asyncio.run(safe_send_telegram_message(message))
        except RuntimeError as exc:
            print(f"⚠️ Telegram loop fallback error: {exc}")

    threading.Thread(target=_runner, daemon=True).start()


async def safe_send_telegram_message(message: str) -> None:
    print(f"🔄 Sending Telegram message: {message[:40]}…")
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
    except Exception as exc:
        msg = f"⚠️ Could not load bot status: {exc}"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


async def wallets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return
    print(f"📩 /wallets from chat_id={update.effective_chat.id}")

    try:
        with open(PORTFOLIO_FILE, "r") as pf:
            portfolio = json.load(pf)
    except Exception as exc:
        portfolio = {}
        print(f"⚠️ Error loading portfolio.json: {exc}")

    try:
        with open(WALLETS_FILE, "r") as wf:
            wallets_data = json.load(wf)["wallets"]
    except Exception as exc:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"⚠️ Failed to load wallets.json: {exc}",
        )
        return

    if not portfolio:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ Portfolio is empty.",
        )
        return

    lines = ["👛 Wallet Overview:"]
    for name, address in wallets_data.items():
        value = 0.0
        for token_data in portfolio.get(address, {}).values():
            value += token_data.get("quantity", 0) * token_data.get("avg_price", 0)
        lines.append(f"- {name} ({address[:5]}…): {value:.4f} SOL")

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="\n".join(lines),
    )


async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"📩 /pause from chat_id={update.effective_chat.id}")
    with open("pause_flag", "w") as f:
        f.write("1")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="⏸ Bot paused.")


async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"📩 /resume from chat_id={update.effective_chat.id}")
    if os.path.exists("pause_flag"):
        os.remove("pause_flag")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="▶️ Bot resumed.")


async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"📩 /debug from chat_id={update.effective_chat.id}")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="✅ Debug mode active.")


async def log_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"📩 /log_summary from chat_id={update.effective_chat.id}")

    if not os.path.exists(LOG_FILE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No log file found.")
        return

    try:
        with open(LOG_FILE, "r") as log_f:
            lines = log_f.readlines()
        if not lines:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Log file is empty.")
            return

        summary = "".join(lines[-15:])
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="📋 Recent Bot Activity:\n\n" + summary,
        )
    except Exception as exc:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Error reading log file: {exc}",
        )


# ─── listener bootstrap ───────────────────────────────────────────────────


async def run_telegram_command_listener(token: str) -> None:
    global telegram_listener_started
    if telegram_listener_started:
        return
    telegram_listener_started = True
    print("✅ Starting Telegram command listener…")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("status",      status))
    app.add_handler(CommandHandler("wallets",     wallets))
    app.add_handler(CommandHandler("pause",       pause))
    app.add_handler(CommandHandler("resume",      resume))
    app.add_handler(CommandHandler("debug",       debug))
    app.add_handler(CommandHandler("log_summary", log_summary))

    await app.run_polling()
