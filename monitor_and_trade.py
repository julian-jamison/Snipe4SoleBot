import time
import asyncio
import threading
from trade_execution import buy_token_multi_wallet, sell_token_auto_withdraw
from mempool_monitor import get_new_liquidity_pools
from telegram_notifications import safe_send_telegram_message
from whale_tracking import get_whale_transactions
from utils import get_token_price, should_buy_token, get_random_wallet

def send_telegram_message(message):
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(safe_send_telegram_message(message))
    except RuntimeError:
        asyncio.run(safe_send_telegram_message(message))

def sniper_loop():
    """Main sniper loop with automatic profit withdrawals."""
    print("🚀 Sniper bot running with Automatic Withdrawals...")
    send_telegram_message("🚀 Snipe4SoleBot is LIVE and scanning for new liquidity pools!")

    while True:
        new_pools = get_new_liquidity_pools()

        for pool in new_pools:
            token_address = pool.get("baseMint") or pool.get("mint")
            if not token_address:
                continue

            print(f"🔹 New liquidity detected: {token_address}")
            send_telegram_message(f"🚀 New liquidity detected: {token_address}")

            # Fetch whale transactions
            whale_buys, whale_sells = get_whale_transactions(token_address)

            if whale_buys > 100:
                send_telegram_message(f"🐋 WHALE ALERT! {whale_buys} SOL worth of {token_address} just bought!")

            if whale_sells > 50:
                send_telegram_message(f"⚠️ Warning! {whale_sells} SOL worth of {token_address} just sold!")

            # Decide whether to buy
            if should_buy_token(token_address):
                selected_wallet = get_random_wallet()
                send_telegram_message(f"🛒 Buying {token_address} with wallet {selected_wallet.pubkey()}.")

                buy_token_multi_wallet(token_address, selected_wallet)
                initial_price = get_token_price(token_address)

                # Monitor price and auto-sell if conditions met
                while True:
                    current_price = get_token_price(token_address)
                    if not current_price:
                        continue

                    profit = (current_price - initial_price) / initial_price * 100

                    if profit >= 10:
                        sell_token_auto_withdraw(token_address, selected_wallet)
                        send_telegram_message(f"✅ Sold {token_address} for {profit:.2f}% profit! Profits withdrawn.")
                        break
                    elif profit <= -5:
                        sell_token_auto_withdraw(token_address, selected_wallet)
                        send_telegram_message(f"❌ Stop-loss triggered! Sold {token_address} at {profit:.2f}% loss.")
                        break

                    time.sleep(2)
            else:
                send_telegram_message(f"❌ Skipping {token_address}. Doesn't meet buy criteria.")

        time.sleep(1)

def start_sniper_thread():
    thread = threading.Thread(target=sniper_loop, daemon=True)
    thread.start()
    return thread
