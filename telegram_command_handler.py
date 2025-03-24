from decrypt_config import config
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram import Update
import os
import json

WALLETS_FILE = "wallets.json"
PORTFOLIO_FILE = "portfolio.json"

app = None
TELEGRAM_BOT_TOKEN = config["telegram"]["bot_token"]


async def wallets_command(update: Update, context):
    if not update.effective_chat:
        return

    message = "💼 Wallet Balances:\n"
    portfolio = {}

    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            portfolio = json.load(f)

    if os.path.exists(WALLETS_FILE):
        with open(WALLETS_FILE, "r") as f:
            wallet_config = json.load(f)
        for name, address in wallet_config["wallets"].items():
            tokens = portfolio.get(address, {})
            total = sum(t["quantity"] for t in tokens.values()) if tokens else 0
            message += f"- {name} ({address[:6]}...): {total:.4f} tokens across {len(tokens)} assets\n"
    else:
        message += "⚠️ wallets.json not found."

    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)


def register_wallet_command():
    global app
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("wallets", wallets_command))
    return app
