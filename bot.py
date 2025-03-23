import time
import json
from threading import Thread
from telegram import Bot

from trade_execution import execute_trade, get_new_liquidity_pools
from telegram_notifications import send_telegram_message
from utils import fetch_price
from decrypt_config import config
from portfolio import add_position, get_all_positions, get_position, remove_position

TELEGRAM_BOT_TOKEN = config["telegram"]["bot_token"]
TELEGRAM_CHAT_ID = config["telegram"]["chat_id"]
TRADE_SETTINGS = config["trade_settings"]

bot = Bot(token=TELEGRAM_BOT_TOKEN)

STATUS_FILE = "bot_status.json"
start_time = time.time()
trade_count = 0
profit_total = 0


def save_bot_status():
    with open(STATUS_FILE, "w") as f:
        json.dump({
            "start_time": start_time,
            "trade_count": trade_count,
            "profit_total": profit_total
        }, f)


def load_bot_status():
    global start_time, trade_count, profit_total
    try:
        with open(STATUS_FILE, "r") as f:
            data = json.load(f)
            start_time = data.get("start_time", time.time())
            trade_count = data.get("trade_count", 0)
            profit_total = data.get("profit_total", 0)
    except FileNotFoundError:
        pass


load_bot_status()


def auto_buy_loop():
    """Snipes high-liquidity tokens and logs buys."""
    global trade_count
    while True:
        print("🔁 Checking for new liquidity pools...")
        pools = get_new_liquidity_pools()
        if pools:
            best = pools[0]
            token = best["token"]
            price = fetch_price(token)
            if not price:
                print(f"⚠️ Skipping {token}, price unavailable")
                continue
            quantity = 100  # Example size
            execute_trade("buy", token)
            add_position(token, quantity, price, best["dex"])
            send_telegram_message(f"✅ Bought {quantity} of {token} at ${price:.6f} via {best['dex']}")
            trade_count += 1
            save_bot_status()
        time.sleep(10)


def auto_sell_loop():
    """Monitors portfolio to sell on profit or loss."""
    global profit_total, trade_count
    while True:
        positions = get_all_positions()
        for token, data in positions.items():
            entry_price = data["price"]
            current_price = fetch_price(token)
            if not current_price:
                continue

            change_pct = ((current_price - entry_price) / entry_price) * 100

            if change_pct >= TRADE_SETTINGS["profit_target"]:
                execute_trade("sell", token)
                profit = (current_price - entry_price) * data["quantity"]
                send_telegram_message(f"📈 Sold {token} with +{change_pct:.2f}% gain (${profit:.2f})")
                profit_total += profit
                remove_position(token)
                trade_count += 1
                save_bot_status()

            elif change_pct <= TRADE_SETTINGS["stop_loss"]:
                execute_trade("sell", token)
                loss = (current_price - entry_price) * data["quantity"]
                send_telegram_message(f"📉 Sold {token} with {change_pct:.2f}% loss (${loss:.2f})")
                profit_total += loss
                remove_position(token)
                trade_count += 1
                save_bot_status()

        time.sleep(15)


# Start all bot threads
Thread(target=auto_buy_loop, daemon=True).start()
Thread(target=auto_sell_loop, daemon=True).start()

send_telegram_message("✅ Snipe4SoleBot is now running with auto-sell enabled!")
