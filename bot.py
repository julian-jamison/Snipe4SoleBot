import time
import json
import os
from threading import Thread
from telegram import Bot
from trade_execution import execute_trade, get_new_liquidity_pools
from telegram_notifications import send_telegram_message
from decrypt_config import config
from utils import log_trade_result
from trade_execution import calculate_trade_size, get_market_volatility

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

            # Auto Sell Logic
            portfolio = load_portfolio()
            if token in portfolio:
                avg_price = portfolio[token]["avg_price"]
                current_price = price
                if not current_price:
                    continue

                pnl = ((current_price - avg_price) / avg_price) * 100

                if pnl >= TRADE_SETTINGS["profit_target"] or pnl <= TRADE_SETTINGS["stop_loss"]:
                    sell_price = execute_trade("sell", token)
                    if sell_price:
                        update_portfolio(token, "sell", sell_price, quantity)
                        trade_count += 1
                        profit += (sell_price - avg_price) * quantity
                        save_bot_status()
                        log_trade_result("sell", token, sell_price, quantity, (sell_price - avg_price) * quantity, "success")
                        send_telegram_message(f"📤 Auto-sell {quantity} of {token} at ${sell_price:.4f} | PNL: {pnl:.2f}%")

        time.sleep(10)

# ========== Start Thread ==========
Thread(target=bot_main_loop, daemon=True).start()
send_telegram_message("✅ Snipe4SoleBot is now running with auto sell enabled!")
