import time
import json
import os
import sys
import fcntl
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
PID_LOCK_FILE = "snipe4solebot.pid"

start_time = time.time()
trade_count = 0
profit = 0
wallet_index = 0  # For round-robin

ALLOWED_TOKENS = set(config.get("allowed_tokens", []))

# ========== PID Locking ===========

def enforce_singleton():
    try:
        pidfile = open(PID_LOCK_FILE, 'w')
        fcntl.flock(pidfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pidfile.write(str(os.getpid()))
        pidfile.flush()
    except IOError:
        print("❌ Another instance is already running. Exiting.")
        sys.exit(1)

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
            del portfolio[wallet][token]
        if not portfolio[wallet]:
            del portfolio[wallet]

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

# ========== Get New Liquidity Pools ===========

def get_new_liquidity_pools():
    pools = []
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get("https://api.raydium.io/v2/main/pairs", timeout=10, headers=headers)
        response.raise_for_status()
        raydium_data = response.json()
        for pool_data in raydium_data:
            base_mint = pool_data.get("baseMint")
            quote_mint = pool_data.get("quoteMint")
            if base_mint and (not ALLOWED_TOKENS or base_mint in ALLOWED_TOKENS):
                pools.append({"dex": "Raydium", "token": base_mint})
            if quote_mint and (not ALLOWED_TOKENS or quote_mint in ALLOWED_TOKENS):
                pools.append({"dex": "Raydium", "token": quote_mint})
    except requests.exceptions.HTTPError as e:
        if response.status_code == 429:
            print("❌ Raydium rate limited. Retrying after short delay...")
            time.sleep(random.uniform(3, 10))
        else:
            print(f"❌ Error fetching Raydium liquidity pools: {e}")
    except Exception as e:
        print(f"❌ Error fetching Raydium liquidity pools: {e}")
    return pools

# ========== Profit Distribution ===========

def distribute_profit(amount):
    summary_lines = [f"💸 Distributing total profit of {amount:.4f} SOL:"]
    for wallet, percent in profit_split.items():
        share = (percent / 100) * amount
        summary_lines.append(f"- {wallet}: {share:.4f} SOL ({percent}%)")
    send_telegram_message("\n".join(summary_lines))

# ========== Auto Withdrawals ===========

def check_auto_withdrawal():
    if not auto_withdrawal_cfg.get("enabled"):
        return
    if auto_withdrawal_cfg.get("emergency_stop", {}).get("enabled"):
        crash_threshold = auto_withdrawal_cfg["emergency_stop"].get("market_crash_threshold", -15)
        if profit < crash_threshold:
            if auto_withdrawal_cfg["emergency_stop"].get("telegram_alert"):
                send_telegram_message("🚨 Emergency Stop: Market crash threshold triggered. Withdrawals paused.")
            return
    threshold = auto_withdrawal_cfg.get("threshold", 0)
    if profit >= threshold:
        send_telegram_message(f"💸 Profit threshold of {threshold} SOL reached. Triggering auto-withdrawal!")
        distribute_profit(profit)

# ========== Prevent Multiple Telegram Alerts ===========

def send_startup_message_once():
    if not os.path.exists(STARTUP_LOCK_FILE):
        send_telegram_message("✅ Snipe4SoleBot is now running with auto sell enabled!")
        with open(STARTUP_LOCK_FILE, "w") as f:
            f.write("sent")

# ========== Telegram Command Listener ===========

async def run_telegram_command_listener(token):
    if os.path.exists(TELEGRAM_LOCK_FILE):
        print("⚠️ Telegram listener already running.")
        return

    print("🤖 Telegram command listener running...")
    with open(TELEGRAM_LOCK_FILE, "w") as f:
        f.write("started")

    from telegram_command_handler import status, wallets, pause, resume

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
    enforce_singleton()

    # Clean up stale lock files on reboot or crash
    for lock_file in [STARTUP_LOCK_FILE, TELEGRAM_LOCK_FILE]:
      # Clean up stale lock file for Telegram only
        if os.path.exists(TELEGRAM_LOCK_FILE):
            os.remove(TELEGRAM_LOCK_FILE)

    send_startup_message_once()
    Thread(target=bot_main_loop, daemon=True).start()
    nest_asyncio.apply()
    try:
        asyncio.run(run_telegram_command_listener(TELEGRAM_BOT_TOKEN))
    except RuntimeError as e:
        print(f"❌ Telegram listener failed to start: {e}")
