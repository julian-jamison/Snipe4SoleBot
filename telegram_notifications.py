from telegram import Bot
from decrypt_config import config
import json
import schedule
import time
import asyncio
from datetime import datetime

TELEGRAM_BOT_TOKEN = config["telegram"]["bot_token"]
TELEGRAM_CHAT_ID = config["telegram"]["chat_id"]

bot = Bot(token=TELEGRAM_BOT_TOKEN)
TRADE_LOG_FILE = "trade_log.json"

def send_telegram_message(message):
    """Sends a Telegram alert."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram bot token or chat ID not set. Message not sent.")
        return
    
    try:
        asyncio.run(bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message))  # 👈 Await this properly
        print(f"📩 Telegram message sent: {message}")
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")

def send_trade_alert(action, token, price, quantity, profit_loss=None):
    """Sends a detailed trade alert to Telegram."""
    message = f"📢 Trade Alert:\nAction: {action.upper()}\nToken: {token}\nPrice: ${price:.4f}\nQuantity: {quantity}"
    
    if profit_loss is not None:
        message += f"\nProfit/Loss: {profit_loss:.4f} SOL"

    send_telegram_message(message)

def send_system_alert(status):
    """Sends system status updates to Telegram."""
    message = f"⚠️ System Alert: {status}"
    send_telegram_message(message)

def send_daily_summary():
    """Sends a daily summary of all trades and profit/loss to Telegram at 9 PM PST."""
    if not os.path.exists(TRADE_LOG_FILE):
        send_telegram_message("📊 Daily Summary: No trades executed today.")
        return

    try:
        with open(TRADE_LOG_FILE, "r") as f:
            trade_logs = json.load(f)

        if not trade_logs:
            send_telegram_message("📊 Daily Summary: No trades executed today.")
            return

        total_trades = len(trade_logs)
        total_profit = sum(trade.get("profit_loss", 0) for trade in trade_logs)
        summary_message = f"📊 Daily Trade Summary - {datetime.now().strftime('%Y-%m-%d')}:\n"
        summary_message += f"Total Trades: {total_trades}\nTotal Profit/Loss: {total_profit:.4f} SOL\n"

        # Send details of last 5 trades
        last_trades = trade_logs[-5:]
        for trade in last_trades:
            summary_message += f"\n🔹 {trade['timestamp']} - {trade['action'].upper()} {trade['token']}\n"
            summary_message += f"Price: ${trade['price']:.4f}, Quantity: {trade['quantity']}, P/L: {trade['profit_loss']:.4f} SOL"

        send_telegram_message(summary_message)

        # Clear log for next day
        with open(TRADE_LOG_FILE, "w") as f:
            json.dump([], f)

        send_telegram_message("✅ Daily Summary sent and logs cleared for next day.")

    except Exception as e:
        send_telegram_message(f"⚠️ Failed to send daily summary: {e}")

# 🔹 Schedule daily summary at 9 PM PST
schedule.every().day.at("21:00").do(send_daily_summary)

if __name__ == "__main__":
    send_telegram_message("🚀 Telegram Notification Service Started.")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute
