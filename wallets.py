import json
import logging

WALLET_FILE = "wallets.json"

def load_wallets():
    try:
        with open(WALLET_FILE, "r") as f:
            data = json.load(f)
            wallets = data.get("wallets", {})
            if not wallets:
                raise ValueError("No wallets found in config.")
            return wallets
    except Exception as e:
        logging.error(f"Error loading wallets: {e}")
        return {}
