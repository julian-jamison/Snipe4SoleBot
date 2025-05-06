from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update
from telegram_notifications import safe_send_telegram_message
from trade_execution import execute_trade
from health_check import send_health_update
from restore_backup import restore_from_gdrive
from decrypt_config import config
import os
import json
import time
import subprocess

AUTHORIZED_USERS = {123456789, 987654321}  # Replace with real IDs

STATUS_FILE = "bot_status.json"
PORTFOLIO_FILE = "portfolio.json"
WALLETS_FILE = "wallets.json"
LOG_FILE = "logs/agent_activity.log"

def is_authorized(update: Update):
    return update.effective_chat and update.effective_chat.id in AUTHORIZED_USERS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Snipe4SoleBot is online! Use /help for commands.")

async def restore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ You are not authorized to perform this action.")
        return
    message = restore_from_gdrive()
    await update.message.reply_text(message)

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    send_health_update()
    await update.message.reply_text("✅ Health check sent to Telegram.")

async def execute_trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ You are not authorized to perform this action.")
        return
    execute_trade("buy", "TEST_TOKEN")
    await update.message.reply_text("🛒 Test trade executed.")

async def shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ You are not authorized to perform this action.")
        return
    await update.message.reply_text("⚠️ Shutting down bot...")
    await safe_send_telegram_message("🔴 Bot has been stopped remotely.")
    os._exit(0)

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ You are not authorized.")
        return
    await update.message.reply_text("♻️ Restarting the bot...")
    await safe_send_telegram_message("♻️ Snipe4Sol is restarting...")
    subprocess.Popen(["systemctl", "restart", "snipe4sol.service"])
    os._exit(0)

async def version(update: Update, context: ContextTypes.DEFAULT_TYPE):
    live_mode = config.get("live_mode", False)
    tokens = config.get("allowed_tokens", [])
    mode = "LIVE" if live_mode else "TEST"
    token_list = ", ".join(tokens) if tokens else "None"
    msg = (
        f"🛠️ Bot Configuration:
"
        f"- Mode: {mode}
"
        f"- Allowed Tokens: {token_list}"
    )
    await update.message.reply_text(msg)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return
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
    await update.message.reply_text(msg)

async def log_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("❌ You are not authorized to perform this action.")
        return
    try:
        if not os.path.exists(LOG_FILE):
            await update.message.reply_text("No log file found.")
            return
        with open(LOG_FILE, "r") as log:
            lines = log.readlines()
            if not lines:
                await update.message.reply_text("Log file is empty.")
                return
            summary_lines = lines[-15:]
            await update.message.reply_text("📋 Recent Bot Activity:

" + "".join(summary_lines))
    except Exception as e:
        await update.message.reply_text(f"Error reading log file: {e}")

async def setup_telegram_bot(token: str):
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("restore", restore))
    app.add_handler(CommandHandler("health", health))
    app.add_handler(CommandHandler("trade", execute_trade_command))
    app.add_handler(CommandHandler("shutdown", shutdown))
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(CommandHandler("version", version))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("log_summary", log_summary))
    await app.run_polling()
