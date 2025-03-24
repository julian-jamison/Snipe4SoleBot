import time
import json
import os
from threading import Thread
import asyncio
from telegram import Bot
from trade_execution import execute_trade, check_for_auto_sell, calculate_trade_size, get_market_volatility
from telegram_notifications import send_telegram_message
from decrypt_config import config
from utils import log_trade_result
from telegram_command_handler import run_telegram_command_listener
import requests

# ========== Telegram Setup ==========
TELEGRAM_BOT_TOKEN = config["telegram"]["bot_token"]
TELEGRAM_CHAT_ID = config["telegram"]["chat_id"]
bot = Bot(token=TELEGRAM_BOT_TOKEN)

TRADE_SETTINGS = config["trade_settings"]

STATUS_FILE = "bot_status.json"
PORTFOLIO_FILE = "portfolio.json"
start_time = time.time()
trade_count = 0
profit = 0

# ========== Portfolio Management ==========

def load_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        return {}
    with open(PORTFOLIO_FILE, "r") as f:
        return json.load(f)

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=2)

def update_portfolio(token, action, price, quantity):
    portfolio = load_portfolio()
    if token not in portfolio:
        portfolio[token] = {"avg_price": 0, "quantity": 0}

    if action == "buy":
        prev_quantity = portfolio[token]["quantity"]
        prev_price = portfolio[token]["avg_price"]
        new_total_qty = prev_quantity + quantity
        if new_total_qty > 0:
            portfolio[token]["avg_price"] = ((prev_quantity * prev_price) + (quantity * price)) / new_total_qty
        portfolio[token]["quantity"] = new_total_qty

    elif action == "sell":
        portfolio[token]["quantity"] -= quantity
        if portfolio[token]["quantity"] <= 0:
            del portfolio[token]  # Fully sold

    save_portfolio(portfolio)

# ========== Status Persistence ==========

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

# ========== Get New Liquidity Pools ==========

def get_new_liquidity_pools():
    import time

    pools = []
    dex_endpoints = [
        ("Raydium", "https://api.raydium.io/pairs"),
        # ("Jupiter", "https://cache.jup.ag/pools"),  # Removed for now
    ]

    for dex, url in dex_endpoints:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                for pool_data in data:
                    token_address = pool_data.get("mint") or pool_data.get("address") or pool_data.get("baseMint")
                    if token_address:
                        pools.append({"dex": dex, "token": token_address})
            elif isinstance(data, dict):
                for pool_id, pool_data in data.items():
                    token_address = pool_data.get("mint") or pool_data.get("address") or pool_data.get("baseMint")
                    if token_address:
                        pools.append({"dex": dex, "token": token_address})

        except requests.exceptions.HTTPError as http_err:
            if response.status_code == 429:
                print(f"❌ {dex} rate limited. Retrying after short delay...")
                time.sleep(5)  # Wait before next iteration
            else:
                print(f"❌ HTTP error fetching {dex}: {http_err}")
        except Exception as e:
            print(f"❌ Error fetching {dex} liquidity pools: {e}")

    return pools


# ========== Bot Main Loop ==========

def bot_main_loop():
    global trade_count, profit

    while True:
        new_pools = get_new_liquidity_pools()

        if new_pools:
            best_pool = new_pools[0]
            token = best_pool["token"]

            # Auto Buy
            price = execute_trade("buy", token)
            if price:
                volatility = get_market_volatility()
                quantity = calculate_trade_size(volatility)
                update_portfolio(token, "buy", price, quantity)
                trade_count += 1
                save_bot_status()
                send_telegram_message(f"🚀 Auto-buy {quantity} of {token} at ${price:.4f} from {best_pool['dex']}")

        # Check portfolio for early auto-sell
        check_for_auto_sell()

        time.sleep(10)

# ========== Start Threads ==========

if __name__ == "__main__":
    Thread(target=bot_main_loop, daemon=True).start()

    try:
        # Run the telegram listener directly (NOT in asyncio.run)
        run_telegram_command_listener(TELEGRAM_BOT_TOKEN)
    except Exception as e:
        print(f"❌ Telegram listener crashed: {e}")

    send_telegram_message("✅ Snipe4SoleBot is now running with auto sell enabled!")

