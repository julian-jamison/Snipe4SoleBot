import time
import json
import os
import sys
import fcntl
import gc
import psutil
from threading import Thread
import asyncio
import random
import requests
import atexit
import csv
import signal
from datetime import datetime, timedelta

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
LIVE_MODE = config.get("live_mode", False)

STATUS_FILE = "bot_status.json"
PORTFOLIO_FILE = "portfolio.json"
WALLETS_FILE = "wallets.json"
STARTUP_LOCK_FILE = "bot_started.lock"
TELEGRAM_LOCK_FILE = "telegram_listener.lock"
PID_LOCK_FILE = "snipe4solebot.pid"
TRADE_LOG_CSV = "trade_log.csv"
BOT_RUNNING_FLAG = "bot_running.flag"

SOLANA_RPC_URL = config.get("solana_rpc_url", "https://api.mainnet-beta.solana.com")
solana_client = Client(SOLANA_RPC_URL)

start_time = time.time()
trade_count = 0
profit = 0
wallet_index = 0
last_activity_time = time.time()
health_check_thread = None

ALLOWED_TOKENS = set(config.get("allowed_tokens", []))

# ========== Health Check Functions ==========

def update_heartbeat():
    """Update heartbeat file with current timestamp and stats."""
    global last_activity_time
    last_activity_time = time.time()
    
    try:
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent(interval=1)
        
        heartbeat_data = {
            "timestamp": time.time(),
            "last_activity": last_activity_time,
            "memory_mb": memory_mb,
            "cpu_percent": cpu_percent,
            "trade_count": trade_count,
            "profit": profit,
            "uptime_minutes": (time.time() - start_time) / 60,
            "pid": os.getpid()
        }
        
        with open(HEARTBEAT_FILE, "w") as f:
            json.dump(heartbeat_data, f, indent=2)
            
    except Exception as e:
        log_health_issue(f"Failed to update heartbeat: {e}")

def check_memory_usage():
    """Check if memory usage is within limits."""
    try:
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb > MEMORY_LIMIT_MB:
            log_health_issue(f"High memory usage: {memory_mb:.2f}MB")
            
            # Try garbage collection first
            gc.collect()
            
            # Check again after GC
            memory_mb_after_gc = process.memory_info().rss / 1024 / 1024
            if memory_mb_after_gc > MEMORY_LIMIT_MB:
                log_health_issue(f"Memory still high after GC: {memory_mb_after_gc:.2f}MB")
                return False
        
        return True
    except Exception as e:
        log_health_issue(f"Memory check failed: {e}")
        return True  # Don't restart on check failure

def check_responsiveness():
    """Check if the bot is still responsive."""
    try:
        # Check if last activity was too long ago
        time_since_activity = time.time() - last_activity_time
        if time_since_activity > (STALE_TIME_MINUTES * 60):
            log_health_issue(f"No activity for {time_since_activity/60:.1f} minutes")
            return False
        
        # Check if we can still connect to Solana RPC
        response = solana_client.get_health()
        if response.get('result') != 'ok':
            log_health_issue(f"Solana RPC unhealthy: {response}")
            return False
            
        return True
    except Exception as e:
        log_health_issue(f"Responsiveness check failed: {e}")
        return False

def log_health_issue(message):
    """Log health issues to file and console."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    print(f"⚠️ Health Issue: {message}")
    
    try:
        with open(HEALTH_LOG_FILE, "a") as f:
            f.write(log_entry)
    except:
        pass

async def health_check_loop():
    """Main health check loop."""
    while True:
        try:
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)
            
            # Update heartbeat
            update_heartbeat()
            
            # Check memory
            if not check_memory_usage():
                await safe_send_telegram_message("⚠️ High memory usage detected. Restarting bot...")
                restart_bot()
            
            # Check responsiveness
            if not check_responsiveness():
                await safe_send_telegram_message("⚠️ Bot appears unresponsive. Restarting...")
                restart_bot()
                
        except Exception as e:
            log_health_issue(f"Health check error: {e}")

def restart_bot():
    """Restart the bot process."""
    try:
        print("🔄 Initiating bot restart...")
        
        # Save current state
        save_state_before_restart()
        
        # Clean up
        cleanup_pid_lock()
        cleanup_telegram_lock()
        
        # Restart the process
        os.execv(sys.executable, ['python'] + sys.argv)
        
    except Exception as e:
        print(f"❌ Failed to restart: {e}")
        sys.exit(1)

def save_state_before_restart():
    """Save important state before restarting."""
    try:
        state_data = {
            "trade_count": trade_count,
            "profit": profit,
            "wallet_index": wallet_index,
            "restart_time": time.time(),
            "reason": "health_check"
        }
        
        with open("bot_restart_state.json", "w") as f:
            json.dump(state_data, f, indent=2)
            
    except Exception as e:
        print(f"⚠️ Failed to save restart state: {e}")

def load_state_after_restart():
    """Load state after restart if available."""
    global trade_count, profit, wallet_index
    
    try:
        if os.path.exists("bot_restart_state.json"):
            with open("bot_restart_state.json", "r") as f:
                state = json.load(f)
                
            trade_count = state.get("trade_count", 0)
            profit = state.get("profit", 0)
            wallet_index = state.get("wallet_index", 0)
            
            # Calculate restart delay
            restart_time = state.get("restart_time", 0)
            time_since_restart = time.time() - restart_time
            
            print(f"✅ Recovered from restart. Time elapsed: {time_since_restart:.1f}s")
            
            # Remove the state file
            os.remove("bot_restart_state.json")
            
    except Exception as e:
        print(f"⚠️ Failed to load restart state: {e}")

# ========== Signal Handlers ==========

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print(f"\n🛑 Received signal {signum}. Shutting down gracefully...")
    
    # Save state
    save_state_before_restart()
    
    # Clean up
    cleanup_pid_lock()
    cleanup_telegram_lock()
    cleanup_running_flag()
    
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ========== PID Locking ===========

def enforce_singleton():
    try:
        pidfile = open(PID_LOCK_FILE, 'w')
        fcntl.flock(pidfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pidfile.write(str(os.getpid()))
        pidfile.flush()
        
        # Create running flag
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
    global last_activity_time
    last_activity_time = time.time()  # Update activity on trades
    
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
    global trade_count, profit, last_activity_time
    while True:
        last_activity_time = time.time()  # Keep updating activity
        await asyncio.sleep(10)  # Replace with trading logic if needed

async def async_main():
    enforce_singleton()
    nest_asyncio.apply()
    
    # Load state from previous restart if available
    load_state_after_restart()
    
    # Start health monitoring
    health_task = asyncio.create_task(health_check_loop())
    
    # Initial health check
    update_heartbeat()
    
    start_sniper_thread()
    await safe_send_telegram_message("✅ Snipe4SoleBot is now running with health monitoring.")
    
    asyncio.create_task(run_telegram_command_listener(TELEGRAM_BOT_TOKEN))
    
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
        
        # Attempt restart on fatal crash
        time.sleep(5)  # Brief delay before restart
        restart_bot()

if __name__ == "__main__":
    main()
