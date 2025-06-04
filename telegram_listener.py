'''telegram_listener.py – standalone command listener for Snipe4SoleBot

Runs in its own process so the trading bot’s asyncio loop stays clean.  
Adds graceful shutdown handling so the listener dies when the main bot
terminates (SIGINT/SIGTERM) or when the owner sends /shutdown.
'''

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Final, Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application, ApplicationBuilder, CallbackContext, CommandHandler,
    ContextTypes,
)

###########################################################################
# 📋  Configuration / startup helpers
###########################################################################

LOG_FILE: Final[str] = "telegram_bot.log"
CONFIG_FILE: Final[str] = "config.json"
STATUS_FILE: Final[str] = "bot_status.json"
PORTFOLIO_FILE: Final[str] = "portfolio.json"

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf‑8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("telegram_listener")

# ── Retrieve bot token & admin chat id ───────────────────────────────────
TOKEN: Optional[str] = sys.argv[1] if len(sys.argv) > 1 else None
ADMIN_CHAT_ID: Optional[int] = None  # will be read from config if present

if not TOKEN:
    try:
        with open(CONFIG_FILE, "r", encoding="utf‑8") as f:
            cfg = json.load(f)
            TOKEN = cfg.get("telegram", {}).get("bot_token")
            ADMIN_CHAT_ID = cfg.get("telegram", {}).get("chat_id")
    except Exception as exc:
        logger.error("Could not read %s: %s", CONFIG_FILE, exc)

if not TOKEN:
    logger.critical("Telegram bot token missing – aborting listener start")
    sys.exit(1)

###########################################################################
# 🛠️  Utility helpers
###########################################################################

def _read_json(path: str | Path) -> dict:
    try:
        with open(path, "r", encoding="utf‑8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as exc:
        logger.warning("Failed to read %s: %s", path, exc)
        return {}

###########################################################################
# 🤖  Command handlers
###########################################################################

async def _restricted(func):  # decorator to restrict commands to ADMIN_CHAT_ID
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if ADMIN_CHAT_ID and update.effective_chat.id != ADMIN_CHAT_ID:
            await update.message.reply_text("⛔️ Unauthorized")
            return
        return await func(update, context)
    return wrapper

@_restricted
async def cmd_start(update: Update, _: CallbackContext):
    await update.message.reply_text(
        "🚀 *Solana Trading Bot – Control Interface*\n\n"  # noqa: E501
        "Available commands:\n"
        "/status – bot status\n"
        "/balance – wallet balances\n"
        "/positions – open positions\n"
        "/shutdown – stop listener\n"
        "/help – show help",
        parse_mode=ParseMode.MARKDOWN,
    )

@_restricted
async def cmd_help(update: Update, _: CallbackContext):
    await cmd_start(update, _)

@_restricted
async def cmd_status(update: Update, _: CallbackContext):
    status = _read_json(STATUS_FILE)
    if not status:
        await update.message.reply_text("Status information not available.")
        return
    msg = (
        "📊 *Bot Status*\n\n"
        f"Status: {status.get('status', 'unknown')}\n"
        f"Uptime: {status.get('uptime', 'n/a')}\n"
        f"Trades: {status.get('trade_count', 0)}\n"
        f"Profit: {status.get('profit', 0):.4f}\n"
        f"Memory: {status.get('memory_mb', 0):.2f} MB\n\n"
        "*Active strategies:*\n" + "\n".join(f"• {s}" for s in status.get("active_strategies", []))
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

@_restricted
async def cmd_balance(update: Update, _: CallbackContext):
    status = _read_json(STATUS_FILE)
    balances: dict = status.get("wallet_balances", {})
    if not balances:
        await update.message.reply_text("No wallet balance information.")
        return
    lines = ["💰 *Wallet balances*\n"]
    for name, bal in balances.items():
        lines.append(f"*{name}*: {bal:.4f} SOL")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

@_restricted
async def cmd_positions(update: Update, _: CallbackContext):
    portfolio = _read_json(PORTFOLIO_FILE)
    if not portfolio:
        await update.message.reply_text("No open positions.")
        return
    text = ["📈 *Open Positions*\n"]
    for wallet, tokens in portfolio.items():
        text.append(f"*{wallet}*:")
        for mint, pos in tokens.items():
            avg = pos.get("avg_price", 0)
            qty = pos.get("quantity", 0)
            text.append(
                f"• `{mint[:6]}…` qty={qty:.4f} @ ${avg:.6f} ≈ ${avg*qty:.4f}")
    await update.message.reply_text("\n".join(text), parse_mode=ParseMode.MARKDOWN)

# Graceful shutdown via /shutdown command
STOP_EVENT: asyncio.Event = asyncio.Event()

@_restricted
async def cmd_shutdown(update: Update, _: CallbackContext):
    await update.message.reply_text("👋 Listener shutting down…")
    logger.info("Shutdown requested by admin – exiting")
    STOP_EVENT.set()

###########################################################################
# 🏃  Main entrypoint
###########################################################################

async def _run_bot() -> None:
    application: Application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start",     cmd_start))
    application.add_handler(CommandHandler("help",      cmd_help))
    application.add_handler(CommandHandler("status",    cmd_status))
    application.add_handler(CommandHandler("balance",   cmd_balance))
    application.add_handler(CommandHandler("positions", cmd_positions))
    application.add_handler(CommandHandler("shutdown",  cmd_shutdown))

    # Register signal handlers so Ctrl‑C or kill terminates cleanly
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, STOP_EVENT.set)

    logger.info("Telegram listener starting…")

    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)

    # Wait until STOP_EVENT is set (signal or /shutdown)
    await STOP_EVENT.wait()

    logger.info("Telegram listener stopping…")
    await application.updater.stop()
    await application.stop()
    await application.shutdown()


def main() -> None:
    try:
        asyncio.run(_run_bot())
    except KeyboardInterrupt:
        # If asyncio loop already closed, ignore
        pass


if __name__ == "__main__":
    main()
