import os
import time
import subprocess
from telegram import Bot
from decrypt_config import config

TELEGRAM_BOT_TOKEN = config["telegram"]["bot_token"]
TELEGRAM_CHAT_ID = config["telegram"]["chat_id"]
CHECK_INTERVAL = 60  # seconds

bot = Bot(token=TELEGRAM_BOT_TOKEN)

def send_alert(message):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        print(f"⚠️ Telegram alert failed: {e}")

def is_bot_running():
    result = subprocess.run(["systemctl", "is-active", "--quiet", "snipe4solebot.service"])
    return result.returncode == 0

def restart_bot():
    subprocess.run(["systemctl", "restart", "snipe4solebot.service"])
    message = f"⚠️ Watchdog triggered a restart of Snipe4SoleBot at {time.strftime('%Y-%m-%d %H:%M:%S')} UTC."
    send_alert(message)
    print(message)

if __name__ == "__main__":
    while True:
        if not is_bot_running():
            restart_bot()
        time.sleep(CHECK_INTERVAL)
