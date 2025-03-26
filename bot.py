import time
import json
import os
from threading import Thread
import asyncio
import random
import requests

import nest_asyncio
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from trade_execution import execute_trade, check_for_auto_sell, calculate_trade_size, get_market_volatility
from telegram_notifications import send_telegram_message
from decrypt_config import config
from utils import log_trade_result

# ========== Telegram Setup ==========
TELEGRAM_BOT_TOKEN = config["telegram"]["bot_token"]
TELEGRAM_CHAT_ID = config["telegram"]["chat_id"]
bot = Bot(token=TELEGRAM_BOT_TOKEN)

TRADE_SETTINGS = config["trade_settings"]

STATUS_FILE = "bot_status.json"
PORTFOLIO_FILE = "portfolio.json"
WALLETS_FILE = "wallets.json"
STARTUP_LOCK_FILE = "bot_started.lock"
TELEGRAM_LOCK_FILE = "telegram_listener.lock"
start_time = time.time()
trade_count = 0
profit = 0
wallet_index = 0  # For round-robin

# Optional token filter
ALLOWED_TOKENS = set(config.get("allowed_tokens", []))

# ========== Load Wallets ===========

def load_wallets_config():
    if not os.path.exists(WALLETS_FILE):
        raise FileNotFoundError("wallets.json not found!")
    with open(WALLETS_FILE, "r") as f:
        return json.load(f)

wallet_config = load_wallets_config()
wallets = wallet_config["wallets"]
wallet_keys = list(wallets.values())
profit_split = wallet_config.get("profit_split", {})
auto_withdrawal_cfg = wallet_config.get("auto_withdrawal", {})

# ========== Wallet Rotation ===========

def get_next_wallet():
    global wallet_index
    if not wallet_keys:
        raise ValueError("No wallets found for trading.")
    wallet = wallet_keys[wallet_index % len(wallet_keys)]
    wallet_index += 1
    return wallet

# ========== Portfolio Management ===========

def load_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        return {}
    with open(PORTFOLIO_FILE, "r") as f:
        return json.load(f)

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=2)

def update_portfolio(token, action, price, quantity, wallet):
    portfolio = load_portfolio()
    if wallet not in portfolio:
        portfolio[wallet] = {}
    if token not in portfolio[wallet]:
        portfolio[wallet][token] = {"avg_price": 0, "quantity": 0}

    if action == "buy":
        prev_quantity = portfolio[wallet][token]["quantity"]
        prev_price = portfolio[wallet][token]["avg_price"]
        new_total_qty = prev_quantity + quantity
        if new_total_qty > 0:
            portfolio[wallet][token]["avg_price"] = ((prev_quantity * prev_price) + (quantity * price)) / new_total_qty
        portfolio[wallet][token]["quantity"] = new_total_qty

    elif action == "sell":
        portfolio[wallet][token]["quantity"] -= quantity
        if portfolio[wallet][token]["quantity"] <= 0:
            del portfolio[wallet][token]  # Fully sold
        if not portfolio[wallet]:
            del portfolio[wallet]  # Remove wallet if empty

    save_portfolio(portfolio)

# ========== Status Persistence ===========

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

# ========== Telegram Command Listener ===========

async def run_telegram_command_listener(token):
    if os.path.exists(TELEGRAM_LOCK_FILE):
        print("⚠️ Telegram listener already running.")
        return

    print("🤖 Telegram command listener running...")
    with open(TELEGRAM_LOCK_FILE, "w") as f:
        f.write("started")

    from telegram_commands import (status, wallets, pause, resume)
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("wallets", wallets))
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

# ========== Bot Main Loop ===========

def bot_main_loop():
    global trade_count, profit
    while True:
        new_pools = get_new_liquidity_pools()
        if new_pools:
            best_pool = new_pools[0]
            token = best_pool["token"]
            wallet = get_next_wallet()
            price = execute_trade("buy", token, wallet=wallet)
            if price:
                volatility = get_market_volatility()
                quantity = calculate_trade_size(volatility)
                update_portfolio(token, "buy", price, quantity, wallet)
                trade_count += 1
                save_bot_status()
                send_telegram_message(f"🚀 Auto-buy {quantity} of {token} at ${price:.4f} from {best_pool['dex']} using wallet {wallet}")
        check_for_auto_sell()
        check_auto_withdrawal()
        time.sleep(10)

# ========== Start Threads ===========

if __name__ == "__main__":
    if os.path.exists(TELEGRAM_LOCK_FILE):
        os.remove(TELEGRAM_LOCK_FILE)

    if not os.path.exists(STARTUP_LOCK_FILE):
        send_telegram_message("✅ Snipe4SoleBot is now running with auto sell enabled!")
        with open(STARTUP_LOCK_FILE, "w") as f:
            f.write("sent")

    Thread(target=bot_main_loop, daemon=True).start()
    nest_asyncio.apply()

    try:
        asyncio.run(run_telegram_command_listener(TELEGRAM_BOT_TOKEN))
    except RuntimeError as e:
        print(f"❌ Telegram listener failed to start: {e}")
