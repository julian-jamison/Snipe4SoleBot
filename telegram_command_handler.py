import json
import os
import time
import asyncio
import aiohttp
import threading
from telegram.request import _httpxrequest as AiohttpRequest
from telegram import Update, Bot
from telegram.ext import ContextTypes
from telegram.ext import ApplicationBuilder, CommandHandler
from decrypt_config import config

TELEGRAM_BOT_TOKEN = config["telegram"]["bot_token"]
TELEGRAM_CHAT_ID = config["telegram"]["chat_id"]

STATUS_FILE = "bot_status.json"
PORTFOLIO_FILE = "portfolio.json"
WALLETS_FILE = "wallets.json"
LOG_FILE = "logs/agent_activity.log"

# Create the session inside the event loop
async def create_session():
    session = aiohttp.ClientSession()
    request = AiohttpRequest(session)
    bot = Bot(token=TELEGRAM_BOT_TOKEN, request=request)
    return bot, session

telegram_listener_started = False

def schedule_safe_telegram_message(message: str):
    def run_in_loop():
        try:
            asyncio.run(safe_send_telegram_message(message))
        except RuntimeError as e:
            print(f"⚠️ Loop error fallback: {e}")
    threading.Thread(target=run_in_loop).start()

async def safe_send_telegram_message(message: str):
    print(f"🔄 Attempting to send Telegram message: {message[:40]}...")
    try:
        bot, _ = await create_session()
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print(f"📩 Telegram message sent safely: {message}")
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
            f"📈 Bot Status:
"
            f"Uptime: {uptime} mins
"
            f"Trades: {status_data['trade_count']}
"
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
    message = "👛 Wallet Overview:
"
    for name, address in wallets_data.items():
        value = 0
        for token_data in portfolio.get(address, {}).values():
            value += token_data.get("quantity", 0) * token_data.get("avg_price", 0)
        message += f"- {name} ({address[:5]}...): {value:.4f} SOL
"
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

async def log_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📩 Received /log_summary from chat_id={update.effective_chat.id}")
    try:
        if not os.path.exists(LOG_FILE):
            await context.bot.send_message(chat_id=update.effective_chat.id, text="No log file found.")
            return
        with open(LOG_FILE, "r") as log:
            lines = log.readlines()
            if not lines:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="Log file is empty.")
                return
            summary_lines = lines[-15:]
            await context.bot.send_message(chat_id=update.effective_chat.id, text="📋 Recent Bot Activity:

" + "".join(summary_lines))
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error reading log file: {e}")

async def run_telegram_command_listener(token):
    global telegram_listener_started
    if telegram_listener_started:
        return
    telegram_listener_started = True
    print("✅ Starting Telegram command listener...")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("wallets", wallets))
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(CommandHandler("debug", debug))
    app.add_handler(CommandHandler("log_summary", log_summary))
    await app.run_polling()
