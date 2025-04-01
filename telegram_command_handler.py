import json
import os
import time
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram_notifications import status, wallets, pause, resume, debug

STATUS_FILE = "bot_status.json"
PORTFOLIO_FILE = "portfolio.json"
WALLETS_FILE = "wallets.json"

TELEGRAM_BOT_TOKEN = config["telegram"]["bot_token"]
TELEGRAM_CHAT_ID = config["telegram"]["chat_id"]
bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def safe_send_telegram_message(message):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print(f"📩 Telegram message sent safely: {message}")
    except RuntimeError as e:
        if 'event loop is closed' in str(e) or 'no current event loop' in str(e):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message))
                loop.close()
            except Exception as inner_e:
                print(f"❌ Failed to send Telegram message with new loop: {inner_e}")
        else:
            print(f"❌ Failed to send Telegram message: {e}")
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")


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
    except Exception as e:
        portfolio = {}
        print(f"⚠️ Error loading portfolio.json: {e}")

    try:
        with open(WALLETS_FILE, "r") as wf:
            wallets_data = json.load(wf)["wallets"]
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"⚠️ Failed to load wallets.json: {e}")
        return

    if not portfolio:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Portfolio is empty.")
        return

    message = "👛 Wallet Overview:\n"
    for name, address in wallets_data.items():
        value = 0
        for token_data in portfolio.get(address, {}).values():
            value += token_data.get("quantity", 0) * token_data.get("avg_price", 0)
        message += f"- {name} ({address[:5]}...): {value:.4f} SOL\n"

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


async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📩 Received /debug from chat_id={update.effective_chat.id}")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="✅ Debug mode is working.")


async def run_telegram_command_listener(token):
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("wallets", wallets))
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(CommandHandler("debug", debug))
    await app.run_polling()
