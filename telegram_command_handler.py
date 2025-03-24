from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import json
import os

WALLETS_FILE = "wallets.json"
PORTFOLIO_FILE = "portfolio.json"

app = None  # To store the Telegram app globally


async def wallets_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    if app is None:
        app = ApplicationBuilder().token(os.environ.get("TELEGRAM_BOT_TOKEN", "")).build()

    app.add_handler(CommandHandler("wallets", wallets_command))
    return app


async def run_telegram_command_listener(token):
    global app
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("wallets", wallets_command))
    print("🤖 Telegram command listener running...")
    await app.run_polling()
