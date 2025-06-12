import time
from telegram_notifications import send_telegram_message_async

def send_health_update():
    """Sends a health update to Telegram every hour."""
    while True:
        message = "✅ Health Check: Bot is running smoothly."
        print(message)
       await send_telegram_message_async(message)
        time.sleep(3600)  # Every hour
