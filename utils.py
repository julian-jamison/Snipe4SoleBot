import aiohttp
import json
import os
import logging
from datetime import datetime

LOG_FILE = "trade_log.json"
CONFIG_FILE = "config.json"
BACKUP_LOG_FILE = "trade_log_backup.json"

# Configure logging
logger = logging.getLogger("Snipe4SoleBot")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler("bot_debug.log")
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Async function to fetch the price
async def fetch_price(token_address):
    """Fetches the latest price of a token from CoinGecko and other DEX APIs as a backup."""
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

    return None

def log_trade_result(action, token, price, quantity, profit_loss, status):
    """Logs trade results to a JSON file."""
    trade_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "token": token,
        "price": price,
        "quantity": quantity,
        "profit_loss": profit_loss,
        "status": status
    }

    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                trade_logs = json.load(f)
        else:
            trade_logs = []

        trade_logs.append(trade_entry)

        with open(LOG_FILE, "w") as f:
            json.dump(trade_logs, f, indent=4)

        logger.info(f"📝 Trade logged: {trade_entry}")

    except Exception as e:
        logger.error(f"❌ Failed to log trade: {e}")

def load_config():
    """Loads bot configuration settings."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    else:
        logger.warning("⚠️ Configuration file not found!")
        return {}

def backup_trade_log():
    """Backs up the trade log in case of unexpected crashes."""
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
    """Restores the trade log from backup if needed."""
    try:
        if os.path.exists(BACKUP_LOG_FILE):
            with open(BACKUP_LOG_FILE, "r") as f:
                trade_logs = json.load(f)

            with open(LOG_FILE, "w") as f:
                json.dump(trade_logs, f, indent=4)

            logger.info("✅ Trade log restored from backup.")
    except Exception as e:
        logger.error(f"❌ Failed to restore trade log: {e}")
