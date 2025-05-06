import schedule
import time
import logging
from watchdog import restart_bot_if_crashed
from health_check import check_health
from portfolio import update_portfolio_status
from telegram_notifications import send_telegram_message

# Configure logging
logging.basicConfig(
    filename='logs/agent_activity.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_health_check():
    try:
        check_health()
        msg = "✅ Bot Health Check Passed."
        logging.info(msg)
        send_telegram_message(msg)
    except Exception as e:
        msg = f"❌ Health Check Failed: {e}"
        logging.error(msg)
        send_telegram_message(msg)

def run_portfolio_update():
    try:
        update_portfolio_status()
        msg = "📊 Portfolio Updated."
        logging.info(msg)
        send_telegram_message(msg)
    except Exception as e:
        msg = f"⚠️ Portfolio Update Failed: {e}"
        logging.error(msg)
        send_telegram_message(msg)

def run_crash_monitor():
    try:
        restart_bot_if_crashed()
        msg = "🔁 Bot status OK or restarted successfully."
        logging.info(msg)
    except Exception as e:
        msg = f"🔁 Restart Watchdog Error: {e}"
        logging.error(msg)
        send_telegram_message(msg)

# Schedule tasks every 5 minutes
schedule.every(5).minutes.do(run_health_check)
schedule.every(5).minutes.do(run_portfolio_update)
schedule.every(5).minutes.do(run_crash_monitor)

startup_msg = "🧠 Snipe4Sol Agent with Logging Started."
logging.info(startup_msg)
send_telegram_message(startup_msg)

# Keep the agent running
while True:
    schedule.run_pending()
    time.sleep(1)
