import aiohttp
import json
import os
import logging
import csv
import time
from datetime import datetime

LOG_FILE = "trade_log.json"
BACKUP_LOG_FILE = "trade_log_backup.json"
CONFIG_FILE = "config.json"
TRADE_LOG_CSV = "trade_log.csv"
ERROR_LOG_CSV = "error_log.csv"

# Configure logging
logger = logging.getLogger("Snipe4SoleBot")
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler("bot_debug.log")
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

async def fetch_price(token_address):
    urls = [
        f"https://api.coingecko.com/api/v3/simple/token_price/solana?contract_addresses={token_address}&vs_currencies=usd",
        f"https://quote-api.jup.ag/v4/quote?inputMint={token_address}&outputMint=So11111111111111111111111111111111111111112"
    ]
    async with aiohttp.ClientSession() as session:
        for url in urls:
            try:
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if "usd" in data.get(token_address, {}):
                        return data[token_address]["usd"]
                    if "data" in data:
                        quotes = data.get("data", [])
                        if quotes and isinstance(quotes, list):
                            return quotes[0].get("outAmount", 0)
            except aiohttp.ClientError as e:
                logger.warning(f"⚠️ Error fetching price from {url}: {e}")
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Error decoding JSON response from {url}: {e}")
    return None

def log_trade_result(action, token, price, quantity, profit_loss, status, wallet="N/A"):
    trade_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "token": token,
        "price": price,
        "quantity": quantity,
        "profit_loss": profit_loss,
        "status": status,
        "wallet": wallet
    }
    try:
        # JSON log
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                trade_logs = json.load(f)
        else:
            trade_logs = []
        trade_logs.append(trade_entry)
        with open(LOG_FILE, "w") as f:
            json.dump(trade_logs, f, indent=4)
        # CSV log
        headers = ["timestamp", "wallet", "token", "action", "price", "quantity", "profit_loss", "status"]
        write_headers = not os.path.exists(TRADE_LOG_CSV)
        with open(TRADE_LOG_CSV, "a", newline="") as f:
            writer = csv.writer(f)
            if write_headers:
                writer.writerow(headers)
            writer.writerow([
                trade_entry["timestamp"], wallet, token, action,
                f"{price:.6f}", f"{quantity:.6f}", f"{profit_loss:.6f}", status
            ])
        logger.info(f"📝 Trade logged: {trade_entry}")
    except Exception as e:
        log_error_csv("log_trade_result", e)
        logger.error(f"❌ Failed to log trade: {e}")

def log_error_csv(context, error):
    headers = ["timestamp", "context", "error"]
    row = [time.strftime("%Y-%m-%d %H:%M:%S"), context, str(error)]
    write_headers = not os.path.exists(ERROR_LOG_CSV)
    try:
        with open(ERROR_LOG_CSV, "a", newline="") as f:
            writer = csv.writer(f)
            if write_headers:
                writer.writerow(headers)
            writer.writerow(row)
    except Exception as log_fail:
        logger.error(f"❌ Failed to log error in CSV: {log_fail}")

def log_event_console(msg, level="info"):
    if level == "info":
        logger.info(msg)
    elif level == "warn":
        logger.warning(msg)
    elif level == "error":
        logger.error(msg)
    else:
        logger.debug(msg)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    else:
        logger.warning("⚠️ Configuration file not found!")
        return {}

def backup_trade_log():
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                trade_logs = json.load(f)
            with open(BACKUP_LOG_FILE, "w") as f:
                json.dump(trade_logs, f, indent=4)
            logger.info("✅ Trade log backup completed.")
    except Exception as e:
        logger.error(f"❌ Failed to back up trade log: {e}")

def restore_trade_log():
    try:
        if os.path.exists(BACKUP_LOG_FILE):
            with open(BACKUP_LOG_FILE, "r") as f:
                trade_logs = json.load(f)
            with open(LOG_FILE, "w") as f:
                json.dump(trade_logs, f, indent=4)
            logger.info("✅ Trade log restored from backup.")
    except Exception as e:
        logger.error(f"❌ Failed to restore trade log: {e}")
