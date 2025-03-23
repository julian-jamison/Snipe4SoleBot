import time
import json
from threading import Thread
from telegram import Bot
from trade_execution import execute_trade, get_new_liquidity_pools
from mempool_monitor import check_mempool
from telegram_notifications import send_telegram_message

TELEGRAM_BOT_TOKEN = "7734018739:AAFQ2P5E-2cWlLGrV9GR_d-m_pEjnTlKTo0"
TELEGRAM_CHAT_ID = "6531394402"

bot = Bot(token=TELEGRAM_BOT_TOKEN)

STATUS_FILE = "bot_status.json"
start_time = time.time()
trade_count = 0
profit = 0

def save_bot_status():
    with open(STATUS_FILE, "w") as f:
        json.dump({
            "start_time": start_time,
            "trade_count": trade_count,
            "profit": profit
        }, f)

def load_bot_status():
    global start_time, trade_count, profit
    try:
        with open(STATUS_FILE, "r") as f:
            data = json.load(f)
            start_time = data.get("start_time", time.time())
            trade_count = data.get("trade_count", 0)
            profit = data.get("profit", 0)
    except FileNotFoundError:
        pass

# Load previous status at startup
load_bot_status()

def bot_main_loop():
    global trade_count, profit

    send_telegram_message("✅ Snipe4SoleBot is now running!")  # ← moved inside here

    while True:
        try:
            new_pools = get_new_liquidity_pools()
            
            if new_pools:
                best_pool = new_pools[0]
                token = best_pool["token"]
                execute_trade("buy", token)
                trade_count += 1
                save_bot_status()
                send_telegram_message(f"🚀 Auto-trade executed for {token} from {best_pool['dex']}!")

            time.sleep(10)
        
        except Exception as e:
            send_telegram_message(f"⚠️ Bot error: {e}")
            time.sleep(5)

# Start bot main loop in a separate thread
Thread(target=bot_main_loop, daemon=True).start()
