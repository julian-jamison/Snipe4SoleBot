import time
import json
import os
import sys
import fcntl
from threading import Thread
import asyncio
import random
import requests
import atexit
import csv

import nest_asyncio
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from trade_execution import execute_trade, check_for_auto_sell, calculate_trade_size, get_market_volatility
from telegram_notifications import safe_send_telegram_message
from decrypt_config import config
from utils import log_trade_result
from solana.rpc.api import Client
from telegram_command_handler import run_telegram_command_listener
from monitor_and_trade import start_sniper_thread

import os
print("🔍 DEBUG: CONFIG_ENCRYPTION_KEY =", os.getenv("CONFIG_ENCRYPTION_KEY"))


# ========== Telegram Setup ==========
TELEGRAM_BOT_TOKEN = config["telegram"]["bot_token"]
TELEGRAM_CHAT_ID = config["telegram"]["chat_id"]
bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def safe_send_telegram_message(message):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print(f"📩 Telegram message sent: {message}")
    except RuntimeError as e:
        if "event loop is closed" in str(e) or "no current event loop" in str(e):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message))
                loop.close()
            except Exception as inner_e:
                print(f"❌ Failed with new loop: {inner_e}")
        else:
            print(f"❌ Send message failed: {e}")

TRADE_SETTINGS = config["trade_settings"]
LIVE_MODE = config.get("live_mode", False)

STATUS_FILE = "bot_status.json"
PORTFOLIO_FILE = "portfolio.json"
WALLETS_FILE = "wallets.json"
STARTUP_LOCK_FILE = "bot_started.lock"
TELEGRAM_LOCK_FILE = "telegram_listener.lock"
PID_LOCK_FILE = "snipe4solebot.pid"
TRADE_LOG_CSV = "trade_log.csv"

SOLANA_RPC_URL = config.get("solana_rpc_url", "https://api.mainnet-beta.solana.com")
solana_client = Client(SOLANA_RPC_URL)

start_time = time.time()
trade_count = 0
profit = 0
wallet_index = 0

ALLOWED_TOKENS = set(config.get("allowed_tokens", []))

# ========== PID Locking ===========

def enforce_singleton():
    try:
        pidfile = open(PID_LOCK_FILE, 'w')
        fcntl.flock(pidfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pidfile.write(str(os.getpid()))
        pidfile.flush()
        atexit.register(cleanup_pid_lock)
        atexit.register(cleanup_telegram_lock)
    except IOError:
        print("❌ Another instance is already running. Exiting.")
        sys.exit(1)

def cleanup_pid_lock():
    if os.path.exists(PID_LOCK_FILE):
        os.remove(PID_LOCK_FILE)

def cleanup_telegram_lock():
    if os.path.exists(TELEGRAM_LOCK_FILE):
        os.remove(TELEGRAM_LOCK_FILE)

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

# ========== Solana Wallet Balance ===========

def get_wallet_balance(wallet_address):
    try:
        response = solana_client.get_balance(wallet_address)
        return response['result']['value'] / 1e9  # Convert lamports to SOL
    except Exception as e:
        print(f"⚠️ Error fetching balance for {wallet_address}: {e}")
        return 0

# ========== Portfolio Management ===========

def load_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump({}, f)
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
            del portfolio[wallet][token]
        if not portfolio[wallet]:
            del portfolio[wallet]

    save_portfolio(portfolio)
    log_trade_csv(token, action, price, quantity, wallet)

# ========== Trade Logging ===========

def log_trade_csv(token, action, price, quantity, wallet):
    headers = ["timestamp", "wallet", "token", "action", "price", "quantity"]
    row = [time.strftime("%Y-%m-%d %H:%M:%S"), wallet, token, action, f"{price:.6f}", f"{quantity:.6f}"]
    write_headers = not os.path.exists(TRADE_LOG_CSV)
    with open(TRADE_LOG_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        if write_headers:
            writer.writerow(headers)
        writer.writerow(row)

# ========== Bot Threads & Startup ===========

async def bot_main_loop():
    global trade_count, profit
    while True:
        await asyncio.sleep(10)  # Replace with trading logic if needed

async def async_main():
    enforce_singleton()
    nest_asyncio.apply()
    start_sniper_thread()
    safe_send_telegram_message("✅ Snipe4SoleBot is now running.")
    asyncio.create_task(run_telegram_command_listener(TELEGRAM_BOT_TOKEN))
    while True:
        await asyncio.sleep(3600)

def main():
    try:
        asyncio.run(async_main())
    except Exception as fatal:
        print(f"❌ Fatal crash in __main__: {fatal}")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(send_telegram_message_async(f"❌ Fatal crash on boot: {fatal}"))
            loop.close()
        except:
            print("⚠️ Failed to send fatal crash alert (event loop unavailable)")

if __name__ == "__main__":
    main()
