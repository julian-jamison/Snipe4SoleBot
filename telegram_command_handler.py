import json
import os
import time
from telegram import Update
from telegram.ext import ContextTypes

STATUS_FILE = "bot_status.json"
PORTFOLIO_FILE = "portfolio.json"
WALLETS_FILE = "wallets.json"


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return

    print(f"📩 Received /status from chat_id={update.effective_chat.id}")

    try:
        with open(STATUS_FILE, "r") as f:
            status_data = json.load(f)
        uptime = round((time.time() - status_data["start_time"]) / 60, 2)
        msg = (
            f"📈 Bot Status:\n"
            f"Uptime: {uptime} mins\n"
            f"Trades: {status_data['trade_count']}\n"
            f"Profit: {status_data['profit']} SOL"
        )
    except Exception as e:
        msg = f"⚠️ Could not load bot status: {e}"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


async def wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return

    print(f"📩 Received /wallets from chat_id={update.effective_chat.id}")

    try:
        with open(PORTFOLIO_FILE, "r") as pf:
            portfolio = json.load(pf)
        with open(WALLETS_FILE, "r") as wf:
            wallets_data = json.load(wf)["wallets"]

        message = "👛 Wallet Overview:\n"
        for name, address in wallets_data.items():
            value = 0
            for token_data in portfolio.get(address, {}).values():
                value += token_data.get("quantity", 0) * token_data.get("avg_price", 0)
            message += f"- {name} ({address[:5]}...): {value:.4f} SOL\n"

    except Exception as e:
        message = f"⚠️ Failed to load wallet data: {e}"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)


async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📩 Received /pause from chat_id={update.effective_chat.id}")
    with open("pause_flag", "w") as f:
        f.write("1")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="⏸ Bot paused.")


async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📩 Received /resume from chat_id={update.effective_chat.id}")
    if os.path.exists("pause_flag"):
        os.remove("pause_flag")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="▶️ Bot resumed.")
