import json
import time
from utils import load_config
from telegram_notifications import send_telegram_message_async

TRANSACTION_FEE = 0.0001  # Estimated SOL transaction fee (adjust as needed)
WITHDRAWAL_THRESHOLD = 5  # Minimum profit (SOL) before auto-withdrawal

def distribute_profits(profit_amount):
    """Distributes profits across wallets based on the percentage split and auto-withdraws when necessary."""
    config = load_config()
    wallets = config["solana_wallets"]
    split = config.get("profit_split", {"main": 70, "backup": 20, "cold_storage": 10})

    if profit_amount < WITHDRAWAL_THRESHOLD:
        print(f"🔹 Profit ({profit_amount} SOL) is below threshold ({WITHDRAWAL_THRESHOLD} SOL). Skipping withdrawal.")
       await send_telegram_message_async(f"⚠️ Profit too low for withdrawal: {profit_amount} SOL")
        return

    distributions = {
        "main": (profit_amount * split["main"]) / 100,
        "backup": (profit_amount * split["backup"]) / 100,
        "cold_storage": (profit_amount * split["cold_storage"]) / 100
    }

    for wallet, amount in distributions.items():
        if amount > TRANSACTION_FEE:  # Ensure there’s enough to cover fees
            final_amount = amount - TRANSACTION_FEE
            print(f"💰 Transferring {final_amount:.6f} SOL to {wallets[wallet]} (after fees)")
           await send_telegram_message_async(f"✅ {final_amount:.6f} SOL sent to {wallet} wallet.")
        else:
            print(f"⚠️ Not enough balance to transfer to {wallet}. Skipping.")
           await send_telegram_message_async(f"❌ Skipped transfer to {wallet}. Amount too low.")

    print("✅ Profit distribution completed.")

# Example call (Replace with actual profit tracking logic)
time.sleep(2)  # Simulate trade cycle delay
distribute_profits(10)  # Example profit in SOL
