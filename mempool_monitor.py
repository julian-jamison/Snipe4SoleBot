import time
import requests
import json
import os
from telegram_notifications import send_telegram_message

# Replace with your actual Helius RPC endpoint
SOLANA_MEMPOOL_API = "https://mainnet.helius-rpc.com/?api-key=3b31521d-eeb6-4665-b500-08a071ba3263"

# Real DEX program IDs (confirmed)
DEX_PROGRAM_IDS = [
    "rvHXrsyTrcRhTbkTJchfU3T9iU21WLCGMDu9zT4TuDw",  # Raydium AMM
    "nExF8aV2KXMo8bJpu9A4gQ2T2xnKxB9EdKmXKj7iCsN",  # Orca AMM
    "8Y8n1xfkoEvXxBAaLw3mcQgw3m1ahdt9YrcmWZz5w5EZ"   # Pump.fun Liquidity
]

SEEN_SIGNATURES_FILE = "seen_signatures.json"

# Load seen signatures from file
if os.path.exists(SEEN_SIGNATURES_FILE):
    with open(SEEN_SIGNATURES_FILE, "r") as f:
        SEEN_SIGNATURES = set(json.load(f))
else:
    SEEN_SIGNATURES = set()

def persist_seen_signatures():
    """Save seen transaction signatures to disk."""
    with open(SEEN_SIGNATURES_FILE, "w") as f:
        json.dump(list(SEEN_SIGNATURES), f)

def check_mempool():
    """
    Monitors the Solana mempool using Helius `searchTransactions` for early liquidity events.
    """
    print("⏳ Scanning mempool for new liquidity pool transactions via Helius...")

    headers = {"Content-Type": "application/json"}

    for program_id in DEX_PROGRAM_IDS:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "searchTransactions",
            "params": {
                "query": f"accountKeys:{program_id}",
                "limit": 5,
                "sort": "desc"
            }
        }

        try:
            response = requests.post(SOLANA_MEMPOOL_API, json=payload, headers=headers, timeout=5)
            response.raise_for_status()
            transactions = response.json().get("result", [])

            for tx in transactions:
                sig = tx.get("signature")
                if sig and sig not in SEEN_SIGNATURES:
                    SEEN_SIGNATURES.add(sig)
                    persist_seen_signatures()

                    instructions = tx.get("instructions", [])
                    for ix in instructions:
                        if "initialize" in ix.get("parsedInstructionType", ""):
                            token = tx.get("description", {}).get("tokenTransfers", [{}])[0].get("mint", "Unknown")
                            print(f"🚀 Potential new pool: {token} via {program_id}")
                            send_telegram_message(f"🚀 Mempool: New liquidity pool or token detected: {token}")
                            return token

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error fetching mempool via Helius for {program_id}: {e}")
            send_telegram_message(f"⚠️ Mempool check failed for {program_id}")

    return None

# Optional manual testing loop
if __name__ == "__main__":
    while True:
        pool = check_mempool()
        if pool:
            print(f"🔥 Found new liquidity pool: {pool}")
        time.sleep(10)
