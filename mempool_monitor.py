import time
import requests
from telegram_notifications import send_telegram_message

# Replace with your actual Helius RPC endpoint
SOLANA_MEMPOOL_API = "https://mainnet.helius-rpc.com/?api-key=3b31521d-eeb6-4665-b500-08a071ba3263"

# Example: Replace with actual DEX program ID for Raydium, Orca, or Pump.fun
DEX_PROGRAM_IDS = [
    "AMMProgramPublicKey1",  # Placeholder
    "AMMProgramPublicKey2",  # Placeholder
]

SEEN_SIGNATURES = set()  # Memory-based signature cache (could be persisted)

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
