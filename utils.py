import requests
import json
import os
from datetime import datetime

LOG_FILE = "trade_log.json"
CONFIG_FILE = "config.json"
BACKUP_LOG_FILE = "trade_log_backup.json"

def fetch_price(token_address):
    """Fetches the latest price of a token from CoinGecko and other DEX APIs as a backup."""
    urls = [
        f"https://api.coingecko.com/api/v3/simple/token_price/solana?contract_addresses={token_address}&vs_currencies=usd",
        f"https://quote-api.jup.ag/v4/quote?inputMint={token_address}&outputMint=SOL"  # Jupiter API as backup
    ]
    
    for url in urls:
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Check the response structure for valid pricing
            price = data.get(token_address, {}).get("usd", None)
            if price is not None:
                return price

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error fetching price from {url}: {e}")

    return None  # Return None if no valid price found

def log_trade_result(action, token, price, quantity, profit_loss, status):
    """Logs trade results to a JSON file."""
    
    trade_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,  # "buy" or "sell"
        "token": token,
        "price": price,
        "quantity": quantity,
        "profit_loss": profit_loss,
        "status": status  # "success" or "failed"
    }

    # Load existing logs if the file exists
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            trade_logs = json.load(f)
    else:
        trade_logs = []

    trade_logs.append(trade_entry)

    # Save updated logs
    with open(LOG_FILE, "w") as f:
        json.dump(trade_logs, f, indent=4)

    print(f"📝 Trade logged: {trade_entry}")

def load_config():
    """Loads bot configuration settings."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    else:
        print("⚠️ Configuration file not found!")
        return {}

def backup_trade_log():
    """Backs up the trade log in case of unexpected crashes."""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            trade_logs = json.load(f)

        with open(BACKUP_LOG_FILE, "w") as f:
            json.dump(trade_logs, f, indent=4)

        print("✅ Trade log backup completed.")

def restore_trade_log():
    """Restores the trade log from backup if needed."""
    if os.path.exists(BACKUP_LOG_FILE):
        with open(BACKUP_LOG_FILE, "r") as f:
            trade_logs = json.load(f)

        with open(LOG_FILE, "w") as f:
            json.dump(trade_logs, f, indent=4)

        print("✅ Trade log restored from backup.")
