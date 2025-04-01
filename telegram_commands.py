from telegram.ext import Updater, CommandHandler
from telegram_notifications import safe_send_telegram_message
from trade_execution import execute_trade
from health_check import send_health_update
from restore_backup import restore_from_gdrive
import os

# Define authorized user IDs (replace with actual Telegram user IDs)
AUTHORIZED_USERS = {123456789, 987654321}  # Example Telegram user IDs

def is_authorized(update):
    """Checks if the user is authorized to use admin commands."""
    user_id = update.message.chat_id
    return user_id in AUTHORIZED_USERS

def start(update, context):
    """Handles the /start command."""
    update.message.reply_text("🤖 Snipe4SoleBot is online! Use /help for commands.")

def restore(update, context):
    """Handles the /restore command to restore config from Google Drive."""
    if not is_authorized(update):
        update.message.reply_text("❌ You are not authorized to perform this action.")
        return
    message = restore_from_gdrive()
    update.message.reply_text(message)

def health(update, context):
    """Handles the /health command to check bot status."""
    send_health_update()
    update.message.reply_text("✅ Health check sent to Telegram.")

def execute_trade_command(update, context):
    """Handles the /trade command to execute a test trade."""
    if not is_authorized(update):
        update.message.reply_text("❌ You are not authorized to perform this action.")
        return
    execute_trade("buy", "TEST_TOKEN")
    update.message.reply_text("🛒 Test trade executed.")

def shutdown(update, context):
    """Handles the /shutdown command to stop the bot remotely."""
    if not is_authorized(update):
        update.message.reply_text("❌ You are not authorized to perform this action.")
        return
    update.message.reply_text("⚠️ Shutting down bot...")
    send_telegram_message("🔴 Bot has been stopped remotely.")
    os._exit(0)

def setup_telegram_bot(bot_token):
    """Starts the Telegram bot and registers commands."""
    updater = Updater(bot_token, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("restore", restore))
    dp.add_handler(CommandHandler("health", health))
    dp.add_handler(CommandHandler("trade", execute_trade_command))
    dp.add_handler(CommandHandler("shutdown", shutdown))
    
    updater.start_polling()
    updater.idle()
