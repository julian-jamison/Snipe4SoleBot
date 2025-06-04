import json
import os
import sys
import fcntl
import gc
import psutil
import subprocess
from threading import Thread
import asyncio
import random
import time
import requests
import atexit
import csv
import signal
from datetime import datetime, timedelta

import nest_asyncio
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from decrypt_config import config
from utils import log_trade_result
from solana.rpc.api import Client

from monitor_and_trade import start_all_strategies, stop_all_strategies, STRATEGY_CONFIG
from telegram_notifications import safe_send_telegram_message

# ========== Health Check Configuration ==========
HEALTH_CHECK_INTERVAL = 300  # 5 minutes
MEMORY_LIMIT_MB = 500  # Restart if memory usage exceeds this
STALE_TIME_MINUTES = 30  # Consider unhealthy if no activity for this long
HEARTBEAT_FILE = "bot_heartbeat.json"
HEALTH_LOG_FILE = "bot_health.log"

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
LIVE_MODE = config.get("api_keys", {}).get("live_mode", False)

STATUS_FILE = "bot_status.json"
PORTFOLIO_FILE = "portfolio.json"
WALLETS_FILE = "wallets.json"
STARTUP_LOCK_FILE = "bot_started.lock"
TELEGRAM_LOCK_FILE = "telegram_listener.lock"

PID_LOCK_FILE = "/var/run/snipe4solebot.pid"  # GLOBAL PID LOCK
TRADE_LOG_CSV = "trade_log.csv"
BOT_RUNNING_FLAG = "bot_running.flag"

SOLANA_RPC_URL = config.get("api_keys", {}).get("solana_rpc_url", "https://api.mainnet-beta.solana.com")
solana_client = Client(SOLANA_RPC_URL)

start_time = time.time()
trade_count = 0
profit = 0
wallet_index = 0
last_activity_time = time.time()
health_check_thread = None
strategy_threads = []  # Track strategy threads

ALLOWED_TOKENS = set(TRADE_SETTINGS.get("allowed_tokens", []))

telegram_proc = None  # Global handle for the telegram child process

# ========== Telegram Subprocess Management ==========

def start_telegram_command_listener():
    global telegram_proc
    if telegram_proc is not None and telegram_proc.poll() is None:
        print("Telegram command handler already running.")
        return
    telegram_cmd = [
        sys.executable,
        "telegram_command_handler.py",
        TELEGRAM_BOT_TOKEN
    ]
    try:
        telegram_proc = subprocess.Popen(telegram_cmd)
        print(f"✅ Telegram command handler subprocess started with PID {telegram_proc.pid}")
    except Exception as e:
        print(f"❌ Failed to start telegram_command_handler.py: {e}")

def stop_telegram_command_listener():
    global telegram_proc
    if telegram_proc and telegram_proc.poll() is None:
        print(f"🛑 Terminating Telegram command handler PID {telegram_proc.pid} ...")
        telegram_proc.terminate()
        try:
            telegram_proc.wait(timeout=5)
            print("✅ Telegram command handler stopped.")
        except subprocess.TimeoutExpired:
            print("⚠️ Telegram handler did not exit, killing forcibly.")
            telegram_proc.kill()
    else:
        print("Telegram command handler not running.")

# ========== Strategy Management Functions ==========

def enable_strategy(strategy_name):
    if strategy_name in STRATEGY_CONFIG:
        STRATEGY_CONFIG[strategy_name]["enabled"] = True
        return True
    return False

def disable_strategy(strategy_name):
    if strategy_name in STRATEGY_CONFIG:
        STRATEGY_CONFIG[strategy_name]["enabled"] = False
        return True
    return False

def get_active_strategies():
    return [name for name, config in STRATEGY_CONFIG.items() if config.get("enabled")]

# ========== Health Check Functions ==========

def update_heartbeat():
    global last_activity_time
    last_activity_time = time.time()
    try:
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent(interval=1)
        active_strategies = get_active_strategies()
        heartbeat_data = {
            "timestamp": time.time(),
            "last_activity": last_activity_time,
            "memory_mb": memory_mb,
            "cpu_percent": cpu_percent,
            "trade_count": trade_count,
            "profit": profit,
            "uptime_minutes": (time.time() - start_time) / 60,
            "pid": os.getpid(),
            "active_strategies": active_strategies
        }
        with open(HEARTBEAT_FILE, "w") as f:
            json.dump(heartbeat_data, f, indent=2)
    except Exception as e:
        log_health_issue(f"Failed to update heartbeat: {e}")

def check_memory_usage():
    try:
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        if memory_mb > MEMORY_LIMIT_MB:
            log_health_issue(f"High memory usage: {memory_mb:.2f}MB")
            gc.collect()
            memory_mb_after_gc = process.memory_info().rss / 1024 / 1024
            if memory_mb_after_gc > MEMORY_LIMIT_MB:
                log_health_issue(f"Memory still high after GC: {memory_mb_after_gc:.2f}MB")
                return False
        return True
    except Exception as e:
        log_health_issue(f"Memory check failed: {e}")
        return True

def check_responsiveness():
    try:
        time_since_activity = time.time() - last_activity_time
        if time_since_activity > (STALE_TIME_MINUTES * 60):
            log_health_issue(f"No activity for {time_since_activity/60:.1f} minutes")
            return False
        response = solana_client.get_health()
        if response.get('result') != 'ok':
            log_health_issue(f"Solana RPC unhealthy: {response}")
            return False
        return True
    except Exception as e:
        log_health_issue(f"Responsiveness check failed: {e}")
        return False

def log_health_issue(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    print(f"⚠️ Health Issue: {message}")
    try:
        with open(HEALTH_LOG_FILE, "a") as f:
            f.write(log_entry)
    except:
        pass

async def health_check_loop():
    while True:
        try:
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)
            update_heartbeat()
            if not check_memory_usage():
                await safe_send_telegram_message("⚠️ High memory usage detected. Restarting bot...")
                restart_bot()
            if not check_responsiveness():
                await safe_send_telegram_message("⚠️ Bot appears unresponsive. Restarting...")
                restart_bot()
        except Exception as e:
            log_health_issue(f"Health check error: {e}")

def restart_bot():
    try:
        print("🔄 Initiating bot restart...")
        stop_all_strategies()
        save_state_before_restart()
        stop_telegram_command_listener()
        cleanup_pid_lock()
        cleanup_telegram_lock()
        os.execv(sys.executable, ['python'] + sys.argv)
    except Exception as e:
        print(f"❌ Failed to restart: {e}")
        sys.exit(1)

def save_state_before_restart():
    try:
        active_strategies = get_active_strategies()
        state_data = {
            "trade_count": trade_count,
            "profit": profit,
            "wallet_index": wallet_index,
            "restart_time": time.time(),
            "reason": "health_check",
            "active_strategies": active_strategies
        }
        with open("bot_restart_state.json", "w") as f:
            json.dump(state_data, f, indent=2)
    except Exception as e:
        print(f"⚠️ Failed to save restart state: {e}")

def load_state_after_restart():
    global trade_count, profit, wallet_index
    try:
        if os.path.exists("bot_restart_state.json"):
            with open("bot_restart_state.json", "r") as f:
                state = json.load(f)
            trade_count = state.get("trade_count", 0)
            profit = state.get("profit", 0)
            wallet_index = state.get("wallet_index", 0)
            active_strategies = state.get("active_strategies", ["sniper"])
            for strategy in STRATEGY_CONFIG.keys():
                STRATEGY_CONFIG[strategy]["enabled"] = strategy in active_strategies
            restart_time = state.get("restart_time", 0)
            time_since_restart = time.time() - restart_time
            print(f"✅ Recovered from restart. Time elapsed: {time_since_restart:.1f}s")
            print(f"✅ Active strategies: {active_strategies}")
            os.remove("bot_restart_state.json")
    except Exception as e:
        print(f"⚠️ Failed to load restart state: {e}")

# ========== Signal Handlers ==========

def signal_handler(signum, frame):
    print(f"\n🛑 Received signal {signum}. Shutting down gracefully...")
    stop_all_strategies()
    save_state_before_restart()
    stop_telegram_command_listener()
    cleanup_pid_lock()
    cleanup_telegram_lock()
    cleanup_running_flag()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ========== PID Locking ===========

def enforce_singleton():
    try:
        pidfile = open(PID_LOCK_FILE, 'w')
        fcntl.flock(pidfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pidfile.write(str(os.getpid()))
        pidfile.flush()
        with open(BOT_RUNNING_FLAG, 'w') as f:
            f.write(str(os.getpid()))
        atexit.register(cleanup_pid_lock)
        atexit.register(cleanup_telegram_lock)
        atexit.register(cleanup_running_flag)
    except IOError:
        print("❌ Another instance is already running. Exiting.")
        sys.exit(1)

def cleanup_pid_lock():
    if os.path.exists(PID_LOCK_FILE):
        os.remove(PID_LOCK_FILE)

def cleanup_telegram_lock():
    if os.path.exists(TELEGRAM_LOCK_FILE):
        os.remove(TELEGRAM_LOCK_FILE)

def cleanup_running_flag():
    if os.path.exists(BOT_RUNNING_FLAG):
        os.remove(BOT_RUNNING_FLAG)

# ========== Load Wallets ===========
def load_wallets_config():
    if not os.path.exists(WALLETS_FILE):
        wallet_data = {
            "wallets": {
                "wallet_1": config["solana_wallets"]["wallet_1"],
                "wallet_2": config["solana_wallets"]["wallet_2"],
                "wallet_3": config["solana_wallets"]["wallet_3"]
            },
            "profit_split": {"cold_wallet": 0.5},
            "auto_withdrawal": {"enabled": True, "threshold": 1.0}
        }
        with open(WALLETS_FILE, "w") as f:
            json.dump(wallet_data, f, indent=2)
        return wallet_data
    with open(WALLETS_FILE, "r") as f:
        return json.load(f)

try:
    wallet_config = load_wallets_config()
    wallets = wallet_config["wallets"]
    wallet_keys = list(wallets.values())
    profit_split = wallet_config.get("profit_split", {})
    auto_withdrawal_cfg = wallet_config.get("auto_withdrawal", {})
except Exception as e:
    print(f"⚠️ Error loading wallets: {e}")
    wallets = {
        "wallet_1": config["solana_wallets"]["wallet_1"],
        "wallet_2": config["solana_wallets"]["wallet_2"],
        "wallet_3": config["solana_wallets"]["wallet_3"]
    }
    wallet_keys = list(wallets.values())
    profit_split = {}
    auto_withdrawal_cfg = {"enabled": True, "threshold": 1.0}

def get_next_wallet():
    global wallet_index
    if not wallet_keys:
        raise ValueError("No wallets found for trading.")
    wallet = wallet_keys[wallet_index % len(wallet_keys)]
    wallet_index += 1
    return wallet

def get_wallet_balance(wallet_address):
    try:
        response = solana_client.get_balance(wallet_address)
        return response['result']['value'] / 1e9
    except Exception as e:
        print(f"⚠️ Error fetching balance for {wallet_address}: {e}")
        return 0

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
    global last_activity_time
    last_activity_time = time.time()
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

def log_trade_csv(token, action, price, quantity, wallet):
    headers = ["timestamp", "wallet", "token", "action", "price", "quantity"]
    row = [time.strftime("%Y-%m-%d %H:%M:%S"), wallet, token, action, f"{price:.6f}", f"{quantity:.6f}"]
    write_headers = not os.path.exists(TRADE_LOG_CSV)
    with open(TRADE_LOG_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        if write_headers:
            writer.writerow(headers)
        writer.writerow(row)

def get_bot_status():
    try:
        uptime_seconds = time.time() - start_time
        uptime_str = str(timedelta(seconds=int(uptime_seconds)))
        active_strategies = get_active_strategies()
        wallet_balances = {}
        for name, address in wallets.items():
            wallet_balances[name] = get_wallet_balance(address)
        portfolio = load_portfolio()
        position_count = sum(len(tokens) for wallet, tokens in portfolio.items())
        strategy_stats = {}
        for strategy in STRATEGY_CONFIG.keys():
            strategy_stats[strategy] = {
                "enabled": STRATEGY_CONFIG[strategy]["enabled"],
                "trades": 0,
                "profit": 0.0
            }
        status = {
            "status": "running",
            "uptime": uptime_str,
            "trade_count": trade_count,
            "profit": profit,
            "memory_mb": psutil.Process().memory_info().rss / 1024 / 1024,
            "active_strategies": active_strategies,
            "wallet_balances": wallet_balances,
            "open_positions": position_count,
            "strategy_stats": strategy_stats,
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return status
    except Exception as e:
        print(f"⚠️ Error getting bot status: {e}")
        return {"status": "error", "error": str(e)}

def save_bot_status():
    try:
        status = get_bot_status()
        with open(STATUS_FILE, "w") as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        print(f"⚠️ Error saving bot status: {e}")

# ========== Extended Telegram Commands ===========

async def handle_strategy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("Usage: /strategy <name> <on|off>")
            return
        strategy_name = args[0].lower()
        action = args[1].lower()
        if strategy_name not in STRATEGY_CONFIG:
            available_strategies = list(STRATEGY_CONFIG.keys())
            await update.message.reply_text(f"Unknown strategy '{strategy_name}'. Available strategies: {', '.join(available_strategies)}")
            return
        if action == "on":
            STRATEGY_CONFIG[strategy_name]["enabled"] = True
            await update.message.reply_text(f"✅ Strategy '{strategy_name}' enabled")
            if strategy_threads:
                stop_all_strategies()
                global strategy_threads
                strategy_threads = start_all_strategies()
        elif action == "off":
            STRATEGY_CONFIG[strategy_name]["enabled"] = False
            await update.message.reply_text(f"❌ Strategy '{strategy_name}' disabled")
            if strategy_threads:
                stop_all_strategies()
                global strategy_threads
                strategy_threads = start_all_strategies()
        else:
            await update.message.reply_text("Invalid action. Use 'on' or 'off'")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def handle_strategies_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        status_text = "📊 Current Strategy Status:\n\n"
        for name, config in STRATEGY_CONFIG.items():
            status = "✅ Enabled" if config.get("enabled") else "❌ Disabled"
            details = []
            if name == "sniper":
                details.append(f"Max positions: {config.get('max_concurrent_positions', 3)}")
                details.append(f"Profit target: {config.get('profit_target_percent', 10)}%")
                details.append(f"Stop loss: {config.get('stop_loss_percent', -5)}%")
            elif name == "arbitrage":
                details.append(f"Min price diff: {config.get('min_price_difference_percent', 1.0)}%")
                details.append(f"Check interval: {config.get('check_interval_seconds', 30)}s")
            elif name == "market_making":
                details.append(f"Min spread: {config.get('min_spread_percent', 1.0)}%")
                details.append(f"Order refresh: {config.get('order_refresh_seconds', 60)}s")
            elif name == "trend_following":
                details.append(f"Timeframes: {', '.join(config.get('timeframes', ['4h']))}")
                token_count = len(config.get('tokens_to_monitor', []))
                details.append(f"Monitored tokens: {token_count}")
            details_text = "\n  - " + "\n  - ".join(details) if details else ""
            status_text += f"*{name.capitalize()}*: {status}{details_text}\n\n"
        await update.message.reply_text(status_text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# ========== Bot Threads & Startup ===========

async def bot_main_loop():
    global trade_count, profit, last_activity_time
    while True:
        last_activity_time = time.time()
        save_bot_status()
        await asyncio.sleep(30)

async def register_extended_commands(application):
    application.add_handler(CommandHandler("strategy", handle_strategy_command))
    application.add_handler(CommandHandler("strategies", handle_strategies_status))

async def async_main():
    enforce_singleton()
    nest_asyncio.apply()
    load_state_after_restart()
    health_task = asyncio.create_task(health_check_loop())
    update_heartbeat()
    global strategy_threads
    strategy_threads = start_all_strategies()
    asyncio.create_task(bot_main_loop())
    active_strategies = get_active_strategies()
    await safe_send_telegram_message(f"🚀 Enhanced Solana Trading Bot is now running!\n\nActive strategies: {', '.join(active_strategies)}")
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    await register_extended_commands(application)
    # ----- START Telegram Command Handler as Subprocess -----
    start_telegram_command_listener()
    while True:
        await asyncio.sleep(3600)

def main():
    try:
        asyncio.run(async_main())
    except Exception as fatal:
        print(f"❌ Fatal crash in __main__: {fatal}")
        log_health_issue(f"Fatal crash: {fatal}")
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(safe_send_telegram_message(f"❌ Fatal crash: {fatal}"))
            loop.close()
        except:
            print("⚠️ Failed to send fatal crash alert")
        stop_telegram_command_listener()
        time.sleep(5)
        restart_bot()

if __name__ == "__main__":
    main()
