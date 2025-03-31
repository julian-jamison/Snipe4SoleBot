import asyncio
import json
import os
import time
import schedule
from datetime import datetime
from telegram import Bot
from decrypt_config import config
import asyncio
from telegram.error import RetryAfter, TimedOut

# Load config values
TELEGRAM_BOT_TOKEN = config['telegram']['bot_token']
TELEGRAM_CHAT_ID = config['telegram']['chat_id']
TRADE_LOG_FILE = "trade_log.json"

# Initialize bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def _async_send(msg: str):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
        print(f"📩 Telegram message sent: {msg}")
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")

def send_telegram_message_async(message: str):
    try:
        loop = asyncio.get_running_loop()
        asyncio.create_task(_async_send(message))
    except RuntimeError:
        # No running loop — fallback for sync context like exceptions or shutdown
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_async_send(message))
        finally:
            loop.close()

    for attempt in range(retries):
        try:
            asyncio.run(bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message))
            print(f"📩 Telegram message sent: {message}")
            return
        except RetryAfter as e:
            wait_time = int(e.retry_after)
            print(f"⏳ Flood control: retrying in {wait_time} seconds...")
            time.sleep(wait_time)
        except TimedOut:
            print("❌ Telegram message failed: Timed out")
            time.sleep(5)
        except Exception as e:
            print(f"❌ Failed to send Telegram message: {e}")
            break

def send_trade_alert(action, token, price, quantity, profit_loss=None):
    """Sends a detailed trade alert to Telegram."""
    message = f"📢 Trade Alert:\nAction: {action.upper()}\nToken: {token}\nPrice: ${price:.4f}\nQuantity: {quantity}"
    if profit_loss is not None:
        message += f"\nProfit/Loss: {profit_loss:.4f} SOL"
    send_telegram_message(message)

def send_system_alert(status):
    """Sends a system status alert."""
    send_telegram_message(f"⚠️ System Alert: {status}")

def send_daily_summary():
    """Sends daily trade summary to Telegram and clears logs for the next day."""
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

        # Include last 5 trades
        last_trades = trade_logs[-5:]
        for trade in last_trades:
            summary_message += f"\n🔹 {trade['timestamp']} - {trade['action'].upper()} {trade['token']}\n"
            summary_message += f"Price: ${trade['price']:.4f}, Quantity: {trade['quantity']}, P/L: {trade['profit_loss']:.4f} SOL"

        send_telegram_message(summary_message)

        # Clear the log for the next day
        with open(TRADE_LOG_FILE, "w") as f:
            json.dump([], f)

        send_telegram_message("✅ Daily Summary sent and logs cleared for next day.")

    except Exception as e:
        send_telegram_message(f"⚠️ Failed to send daily summary: {e}")

# Schedule daily summary at 9 PM PST
schedule.every().day.at("21:00").do(send_daily_summary)

if __name__ == "__main__":
    send_telegram_message("🚀 Telegram Notification Service Started.")
    while True:
        schedule.run_pending()
        time.sleep(60)
