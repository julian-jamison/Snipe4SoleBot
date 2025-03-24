import os
import time
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

STATUS_FILE = "bot_status.json"
PAUSE_FILE = "pause_flag"

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return
    try:
        with open(STATUS_FILE, "r") as f:
            status = json.load(f)
        uptime = round((time.time() - status["start_time"]) / 60, 2)
        msg = (f"📈 Bot Status:\n"
               f"Uptime: {uptime} mins\n"
               f"Trades: {status['trade_count']}\n"
               f"Profit: {status['profit']} SOL")
    except:
        msg = "⚠️ Could not load bot status."

    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(PAUSE_FILE, "w") as f:
        f.write("1")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="⏸ Bot paused.")

async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if os.path.exists(PAUSE_FILE):
        os.remove(PAUSE_FILE)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="▶️ Bot resumed.")

async def run_telegram_command_listener(token):
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))

    print("🤖 Telegram command listener running...")
    await app.initialize()
    await app.start()
    await app.run_polling()
