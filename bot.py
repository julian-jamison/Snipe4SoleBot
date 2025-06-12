#!/usr/bin/env python3
"""
Main entry-point for Snipe4SoleBot

• Global PID lock  → /var/run/snipe4solebot.pid
• Spawns telegram_listener.py as a child process
• Health-check loop & graceful restart
"""

from __future__ import annotations

###############################################################################
# ── stdlib ────────────────────────────────────────────────────────────────────
###############################################################################
import atexit
import asyncio
import csv
import fcntl
import gc
import json
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Final, Optional

###############################################################################
# ── third-party ───────────────────────────────────────────────────────────────
###############################################################################
import nest_asyncio
import psutil
from solana.rpc.api import Client
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

###############################################################################
# ── local modules ────────────────────────────────────────────────────────────
###############################################################################
from decrypt_config import config
from monitor_and_trade import STRATEGY_CONFIG, start_all_strategies, stop_all_strategies
from telegram_notifications import send_telegram_message as safe_send_telegram_message

###############################################################################
# ── live-mode confirmation ───────────────────────────────────────────────────
###############################################################################
if config["api_keys"].get("live_mode") and os.getenv("S4S_CONFIRM_LIVE") != "YES":
    print("🛑  LIVE trading is enabled but S4S_CONFIRM_LIVE is not set – aborting.")
    sys.exit(1)

###############################################################################
# ── constants & runtime globals ──────────────────────────────────────────────
###############################################################################
BASE_DIR: Final[Path] = Path(__file__).resolve().parent

PID_LOCK_FILE: Final[Path] = Path("/var/run/snipe4solebot.pid")
if not PID_LOCK_FILE.parent.exists():
    print(f"⚠️  {PID_LOCK_FILE.parent} does not exist – create it or change PID path.")
    sys.exit(1)

HEARTBEAT_FILE: Final[Path] = BASE_DIR / "bot_heartbeat.json"
HEALTH_LOG_FILE: Final[Path] = BASE_DIR / "bot_health.log"
STATUS_FILE: Final[Path] = BASE_DIR / "bot_status.json"
PORTFOLIO_FILE: Final[Path] = BASE_DIR / "portfolio.json"
WALLETS_FILE: Final[Path] = BASE_DIR / "wallets.json"
TRADE_LOG_CSV: Final[Path] = BASE_DIR / "trade_log.csv"

HEALTH_CHECK_INTERVAL = 300          # seconds
MEMORY_LIMIT_MB       = 500
STALE_TIME_MINUTES    = 30

print("DEBUG decrypted config:", json.dumps(config, indent=2))

# ── Telegram credentials – abort if missing ──────────────────────────────
TELEGRAM_BOT_TOKEN: str = config["telegram"].get("bot_token", "").strip()
if not TELEGRAM_BOT_TOKEN:
    print("❌ Telegram bot token missing – check CONFIG_ENCRYPTION_KEY or config.json")
    sys.exit(1)

TELEGRAM_CHAT_ID      = config["telegram"]["chat_id"]
bot                   = Bot(token=TELEGRAM_BOT_TOKEN)

# ── Solana RPC ────────────────────────────────────────────────────────────
SOLANA_RPC_URL = config["api_keys"].get(
    "solana_rpc_url", "https://api.mainnet-beta.solana.com"
)
solana_client = Client(SOLANA_RPC_URL)

# runtime state
start_time          = time.time()
trade_count         = 0
profit              = 0.0
wallet_index        = 0
last_activity_time  = time.time()
strategy_threads: list[asyncio.Task] = []
telegram_proc: Optional[asyncio.subprocess.Process] = None

###############################################################################
# ── helper: PID-file / singleton ────────────────────────────────────────────
###############################################################################
def enforce_singleton() -> None:
    try:
        pid_file = PID_LOCK_FILE.open("w")
    except PermissionError:
        print(f"🚫 Need sudo to write {PID_LOCK_FILE}")
        sys.exit(1)

    try:
        fcntl.flock(pid_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("❌ Another instance is already running – exiting.")
        sys.exit(1)

    pid_file.write(str(os.getpid()))
    pid_file.flush()

    def _cleanup() -> None:
        try:
            PID_LOCK_FILE.unlink(missing_ok=True)
        except PermissionError:
            pass

    atexit.register(_cleanup)

###############################################################################
# ── telegram listener subprocess management ────────────────────────────────
###############################################################################
LISTENER_PATH: Final[Path] = BASE_DIR / "telegram_listener.py"

async def start_telegram_listener() -> None:
    global telegram_proc
    if telegram_proc and telegram_proc.returncode is None:
        return  # already running

    telegram_proc = await asyncio.create_subprocess_exec(
        sys.executable, str(LISTENER_PATH), TELEGRAM_BOT_TOKEN
    )
    print(f"✅ telegram_listener started (pid {telegram_proc.pid})")

async def stop_telegram_listener() -> None:
    global telegram_proc
    if telegram_proc and telegram_proc.returncode is None:
        telegram_proc.terminate()
        try:
            await asyncio.wait_for(telegram_proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            telegram_proc.kill()
    telegram_proc = None

###############################################################################
# ── heartbeat & health-check ────────────────────────────────────────────────
###############################################################################
def log_health_issue(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with HEALTH_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"⚠️  {msg}")

def update_heartbeat() -> None:
    global last_activity_time
    last_activity_time = time.time()
    p = psutil.Process()
    data = {
        "timestamp": time.time(),
        "memory_mb": p.memory_info().rss / 1024 / 1024,
        "cpu_percent": p.cpu_percent(interval=0.1),
    }
    HEARTBEAT_FILE.write_text(json.dumps(data, indent=2))

async def health_check_loop() -> None:
    while True:
        await asyncio.sleep(HEALTH_CHECK_INTERVAL)
        update_heartbeat()

        # memory
        if psutil.Process().memory_info().rss / 1024 / 1024 > MEMORY_LIMIT_MB:
            await safe_send_telegram_message("⚠️  High memory usage – restarting.")
            os.execv(sys.executable, ["python"] + sys.argv)

        # stalled?
        if time.time() - last_activity_time > STALE_TIME_MINUTES * 60:
            await safe_send_telegram_message("⚠️  Bot stalled – restarting.")
            os.execv(sys.executable, ["python"] + sys.argv)

###############################################################################
# ── Extended Telegram commands (handled by main bot) ────────────────────────
###############################################################################
async def cmd_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global strategy_threads  # declared before first use

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /strategy <name> <on|off>")
        return

    name, action = context.args
    if name not in STRATEGY_CONFIG:
        await update.message.reply_text(f"Unknown strategy: {name}")
        return

    STRATEGY_CONFIG[name]["enabled"] = (action.lower() == "on")
    await update.message.reply_text(
        f"{'Enabled' if STRATEGY_CONFIG[name]['enabled'] else 'Disabled'} {name}"
    )

    # restart threads
    stop_all_strategies()
    strategy_threads = start_all_strategies()

async def cmd_strategies(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    lines = ["📊 Strategies:"]
    for k, v in STRATEGY_CONFIG.items():
        lines.append(f"• {k}: {'ON' if v['enabled'] else 'OFF'}")
    await update.message.reply_text("\n".join(lines))

###############################################################################
# ── startup / main coroutine ────────────────────────────────────────────────
###############################################################################
async def main_coro() -> None:
    enforce_singleton()
    nest_asyncio.apply()

    await start_telegram_listener()

    # health check
    asyncio.create_task(health_check_loop())

    # strategies
    global strategy_threads
    strategy_threads = start_all_strategies()

    # minimal command interface (optional)
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("strategy", cmd_strategy))
    app.add_handler(CommandHandler("strategies", cmd_strategies))
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    await safe_send_telegram_message("🚀 Snipe4SoleBot main process up & running")

    # run forever
    while True:
        await asyncio.sleep(3600)

def main() -> None:
    try:
        asyncio.run(main_coro())
    except KeyboardInterrupt:
        pass
    finally:
        asyncio.run(stop_telegram_listener())
        stop_all_strategies()
        PID_LOCK_FILE.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
