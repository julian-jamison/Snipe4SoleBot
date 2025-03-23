import time
import json
from threading import Thread
from telegram import Bot
from trade_execution import execute_trade, get_new_liquidity_pools
from telegram_notifications import send_telegram_message
from decrypt_config import config
from utils import log_trade_result, backup_trade_log, restore_trade_log
import logging

# Setup rotating log
logger = logging.getLogger("Snipe4SoleBot")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler("bot_debug.log")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

TELEGRAM_BOT_TOKEN = config["telegram"]["bot_token"]
TELEGRAM_CHAT_ID = config["telegram"]["chat_id"]

bot = Bot(token=TELEGRAM_BOT_TOKEN)

STATUS_FILE = "bot_status.json"
start_time = time.time()
trade_count = 0
profit = 0

def save_bot_status():
    """Saves bot status to file for tracking uptime and trade stats."""
    with open(STATUS_FILE, "w") as f:
        json.dump({
            "start_time": start_time,
            "trade_count": trade_count,
            "profit": profit
        }, f)

def load_bot_status():
    """Loads bot status from file."""
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
restore_trade_log()


def bot_main_loop():
    """Main loop to monitor liquidity pools and execute trades."""
    global trade_count, profit

    while True:
        logger.info("🔁 Checking for new liquidity pools...")
        new_pools = get_new_liquidity_pools()

        if new_pools:
            best_pool = new_pools[0]
            token = best_pool["token"]
            try:
                execute_trade("buy", token)
                trade_count += 1
                save_bot_status()
                send_telegram_message(f"🚀 Auto-trade executed for {token} from {best_pool['dex']}!")
                logger.info(f"✅ Trade executed for {token} from {best_pool['dex']}")
            except Exception as e:
                logger.error(f"❌ Trade execution error for {token}: {e}")

        time.sleep(15)  # Adjust delay as needed


# Start bot main loop in a separate thread
Thread(target=bot_main_loop, daemon=True).start()

send_telegram_message("✅ Snipe4SoleBot is now running!")
logger.info("✅ Bot launched and monitoring started.")
backup_trade_log()
