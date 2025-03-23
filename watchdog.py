# watchdog.py
import time
import os
import subprocess

CHECK_INTERVAL = 15  # seconds
RESTART_COMMAND = ["python3", "bot.py"]


def is_bot_running():
    try:
        with open("bot_status.json", "r") as f:
            import json
            data = json.load(f)
            start_time = data.get("start_time")
            return start_time is not None
    except Exception:
        return False


def restart_bot():
    print("🔄 Restarting bot...")
    subprocess.Popen(RESTART_COMMAND)


def watchdog_loop():
    while True:
        if not is_bot_running():
            restart_bot()
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    print("👁️ Watchdog is monitoring the bot...")
    watchdog_loop()
