import asyncio
import os
import signal
import sys
import json
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("telegram_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("telegram_listener")

# Telegram token (read from config or CLI)
TOKEN = sys.argv[1] if len(sys.argv) > 1 else ""
if not TOKEN:
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            TOKEN = config.get("telegram", {}).get("bot_token", "")
    except Exception as e:
        logger.error(f"Failed to read config: {e}")
if not TOKEN:
    logger.error("No token provided!")
    sys.exit(1)

# --- Command Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 *Solana Trading Bot* 🚀\n\n"
        "Welcome to the control interface.\n\n"
        "Available commands:\n"
        "/status - Check bot status\n"
        "/balance - Check wallet balances\n"
        "/positions - Show open positions\n"
        "/stop - Stop the trading bot\n"
        "/restart - Restart the trading bot\n"
        "/help - Show this message",
        parse_mode="Markdown"
    )

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop the main bot process by killing the PID in /var/run/snipe4solebot.pid."""
    pidfile = "/var/run/snipe4solebot.pid"
    if not os.path.exists(pidfile):
        await update.message.reply_text("❌ Main bot is not running (PID file not found).")
        return
    try:
        with open(pidfile, "r") as f:
            pid = int(f.read().strip())
        # Send SIGTERM
        os.kill(pid, signal.SIGTERM)
        await update.message.reply_text("🛑 Bot stopped successfully!")
    except Exception as e:
        await update.message.reply_text(f"Failed to stop bot: {e}")

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restart the main bot by killing, then re-launching. (Simple demo version)"""
    pidfile = "/var/run/snipe4solebot.pid"
    if not os.path.exists(pidfile):
        await update.message.reply_text("❌ Main bot is not running (PID file not found).")
        return
    try:
        with open(pidfile, "r") as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        await update.message.reply_text("🔄 Bot stopping, will auto-restart if managed by systemd or restart script.")
    except Exception as e:
        await update.message.reply_text(f"Failed to restart bot: {e}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Your original status logic here
    if os.path.exists("bot_status.json"):
        with open("bot_status.json", "r") as f:
            status = json.load(f)
        message = f"📊 *Bot Status*\n\n"
        message += f"🤖 Status: {status.get('status', 'Unknown')}\n"
        message += f"⏱️ Uptime: {status.get('uptime', 'Unknown')}\n"
        message += f"💰 Profit: ${status.get('profit', 0):.4f}\n"
        message += f"📈 Trades: {status.get('trade_count', 0)}\n"
        message += f"🧠 Memory: {status.get('memory_mb', 0):.2f} MB\n\n"
        message += "*Active Strategies:*\n"
        for strategy in status.get('active_strategies', []):
            message += f"- {strategy}\n"
        await update.message.reply_text(message, parse_mode="Markdown")
    else:
        await update.message.reply_text("Status information not available.")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if os.path.exists("bot_status.json"):
        with open("bot_status.json", "r") as f:
            status = json.load(f)
        wallet_balances = status.get('wallet_balances', {})
        if wallet_balances:
            message = "💰 *Wallet Balances*\n\n"
            for wallet, balance in wallet_balances.items():
                message += f"*{wallet}*: {balance:.4f} SOL\n"
        else:
            message = "No wallet balance information available."
        await update.message.reply_text(message, parse_mode="Markdown")
    else:
        await update.message.reply_text("Wallet information not available.")

async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if os.path.exists("portfolio.json"):
        with open("portfolio.json", "r") as f:
            portfolio = json.load(f)
        if portfolio:
            message = "📊 *Open Positions*\n\n"
            for wallet, tokens in portfolio.items():
                message += f"*Wallet: {wallet}*\n"
                for token, position in tokens.items():
                    entry_price = position.get("price", 0)
                    quantity = position.get("quantity", 0)
                    value = entry_price * quantity
                    message += f"*Token*: `{token[:10]}...`\n"
                    message += f"*Entry Price*: ${entry_price:.6f}\n"
                    message += f"*Quantity*: {quantity:.6f}\n"
                    message += f"*Value*: ${value:.4f}\n\n"
        else:
            message = "No open positions."
        await update.message.reply_text(message, parse_mode="Markdown")
    else:
        await update.message.reply_text("No open positions or portfolio information not available.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_command)
    app.add_handler(CommandHandler("status", status_command)
    app.add_handler(CommandHandler("balance", balance_command)
    app.add_handler(CommandHandler("positions", positions_command)
    app.add_handler(CommandHandler("stop", stop_command)
    app.add_handler(CommandHandler("restart", restart_command)
    app.add_handler(CommandHandler("help", help_command)
    logging.info("Starting Telegram command listener...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main()
