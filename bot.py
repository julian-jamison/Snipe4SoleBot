import time
import json
import logging
from threading import Thread
from telegram import Bot
from trade_execution import execute_trade, get_new_liquidity_pools
from telegram_notifications import send_telegram_message

# --- Logging Setup ---
logger = logging.getLogger("Snipe4SoleBot")
logger.setLevel(logging.INFO)
handler = logging.handlers.RotatingFileHandler("snipebot.log", maxBytes=5_000_000, backupCount=3)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# --- Telegram Config ---
TELEGRAM_BOT_TOKEN = "7734018739:AAFQ2P5E-2cWlLGrV9GR_d-m_pEjnTlKTo0"
TELEGRAM_CHAT_ID = "6531394402"

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# --- Bot Status ---
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

load_bot_status()

def bot_main_loop():
    global trade_count, profit
    while True:
        logger.info("🔁 Checking for new liquidity pools...")
        new_pools = get_new_liquidity_pools()

        if new_pools:
            best_pool = new_pools[0]
            token = best_pool["token"]
            logger.info(f"🚀 Auto-trade triggered for {token} from {best_pool['dex']}")
            execute_trade("buy", token)
            trade_count += 1
            save_bot_status()
            send_telegram_message(f"🚀 Auto-trade executed for {token} from {best_pool['dex']}!")

        time.sleep(15)  # Tune this for your use case

# Start bot in background thread
Thread(target=bot_main_loop, daemon=True).start()

logger.info("✅ Snipe4SoleBot initialized and running!")
send_telegram_message("✅ Snipe4SoleBot is now running!")
