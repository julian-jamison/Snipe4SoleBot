import time
import json
from threading import Thread
from telegram import Bot
from trade_execution import execute_trade, get_new_liquidity_pools
from telegram_notifications import send_telegram_message

# Telegram credentials (already decrypted via config)
TELEGRAM_BOT_TOKEN = "7734018739:AAFQ2P5E-2cWlLGrV9GR_d-m_pEjnTlKTo0"
TELEGRAM_CHAT_ID = "6531394402"

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Status file for persistence
STATUS_FILE = "bot_status.json"
start_time = time.time()
trade_count = 0
profit = 0

def save_bot_status():
    """Saves bot status to a file for uptime and trade tracking."""
    with open(STATUS_FILE, "w") as f:
        json.dump({
            "start_time": start_time,
            "trade_count": trade_count,
            "profit": profit
        }, f)

def load_bot_status():
    """Loads bot status from a previous run if available."""
    global start_time, trade_count, profit
    try:
        with open(STATUS_FILE, "r") as f:
            data = json.load(f)
            start_time = data.get("start_time", time.time())
            trade_count = data.get("trade_count", 0)
            profit = data.get("profit", 0)
    except FileNotFoundError:
        pass

# Load status on startup
load_bot_status()

def bot_main_loop():
    """Main trading loop to monitor liquidity pools and auto-execute trades."""
    global trade_count, profit

    while True:
        try:
            print("🔁 Checking for new liquidity pools...")
            new_pools = get_new_liquidity_pools()

            if new_pools:
                best_pool = new_pools[0]
                token = best_pool["token"]
                print(f"📈 Executing trade for {token} on {best_pool['dex']}")
                execute_trade("buy", token)
                trade_count += 1
                save_bot_status()
                send_telegram_message(f"🚀 Auto-trade executed for {token} from {best_pool['dex']}!")

            time.sleep(10)  # Cooldown between checks

        except Exception as e:
            print(f"❌ Error in bot loop: {e}")
            send_telegram_message(f"❌ Bot encountered an error: {e}")
            time.sleep(10)  # Prevent tight restart loop on crash

# Only notify once that the bot has started
send_telegram_message("✅ Snipe4SoleBot is now running!")

# Start the main bot loop in a background thread
Thread(target=bot_main_loop, daemon=True).start()

# Keep main thread alive
while True:
    time.sleep(60)
