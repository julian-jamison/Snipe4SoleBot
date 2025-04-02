import time
import requests
import os
import random
import json
import base64
import asyncio
from utils import fetch_price, log_trade_result
from telegram_notifications import safe_send_telegram_message
from decrypt_config import config
from portfolio import add_position, remove_position, get_position, get_all_positions
from solana.rpc.api import Client
from solana.transaction import Transaction
from solana.keypair import Keypair
from solana.rpc.types import TxOpts
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import VersionedTransaction

trade_settings = config["trade_settings"]
BACKTEST_MODE = False
MOCK_DATA_FILE = "mock_pools.json"
SOLANA_RPC_URL = config.get("solana_rpc_url", "https://api.mainnet-beta.solana.com")

TRADE_COOLDOWN_SECONDS = trade_settings.get("trade_cooldown", 30)
MAX_SESSION_BUDGET_SOL = trade_settings.get("max_session_budget", 15)
MIN_WALLET_BALANCE_SOL = 0.1

session_spent = 0
last_trade_time = 0

BAD_TOKENS = set(["BAD1", "SCAM2", "FAKE3"])

signer = Keypair.from_secret_key(bytes.fromhex(config["wallets"]["signer_private_key"]))

client = Client(SOLANA_RPC_URL)


def get_wallet_balance(wallet_address=None):
    try:
        wallet_address = wallet_address or str(signer.pubkey())
        response = client.get_balance(wallet_address)
        lamports = response['result']['value']
        return lamports / 1e9
    except Exception as e:
        print(f"⚠️ Failed to fetch balance: {e}")
        return 0


def get_market_volatility():
    return round(random.uniform(0.01, 0.06), 4)


def calculate_trade_size(volatility):
    base_quantity = 100
    if volatility > trade_settings["dynamic_risk_management"]["volatility_threshold"]:
        return base_quantity * 0.5
    elif volatility < 0.02:
        return base_quantity * 1.5
    return base_quantity


def is_token_suspicious(token_address):
    try:
        url = f"https://public-api.solscan.io/token/meta?tokenAddress={token_address}"
        headers = {"accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=5)

        if response.status_code != 200:
            return True

        data = response.json()
        suspicious_indicators = [
            data.get("name", "").lower() in ["", "token", "unknown"],
            "scam" in data.get("name", "").lower(),
            data.get("symbol", "").lower() in ["scam", "fake"],
            not data.get("verified", False)
        ]

        return any(suspicious_indicators)

    except Exception as e:
        print(f"⚠️ Scam check failed: {e}")
        return True


def send_trade_transaction(token_address, quantity, price, side):
    try:
        quote_url = "https://quote-api.jup.ag/v6/swap"
        user_pubkey = str(signer.pubkey())
        params = {
            "inputMint": "So11111111111111111111111111111111111111112" if side == "buy" else token_address,
            "outputMint": token_address if side == "buy" else "So11111111111111111111111111111111111111112",
            "amount": int(quantity * 1e9),
            "slippage": 1.0,
            "userPublicKey": user_pubkey,
            "wrapUnwrapSOL": True,
            "dynamicSlippage": True
        }
        route_response = requests.get(quote_url, params=params).json()
        if "swapTransaction" not in route_response:
            print(f"❌ No swapTransaction in Jupiter response: {route_response}")
            return None

        swap_tx = base64.b64decode(route_response["swapTransaction"])
        txn = VersionedTransaction.deserialize(swap_tx)
        txn.sign([signer])

        sig = client.send_raw_transaction(txn.serialize(), opts=TxOpts(skip_confirmation=False, preflight_commitment="processed"))
        print(f"🚀 Trade TX sent: https://solscan.io/tx/{sig['result']}")
        return sig
    except Exception as e:
        print(f"❌ Trade TX failed: {e}")
        return None


def execute_trade(action, token_address):
    global session_spent, last_trade_time

    if token_address in BAD_TOKENS or is_token_suspicious(token_address):
        print(f"🚫 Skipping suspicious token: {token_address}")
        return

    if time.time() - last_trade_time < TRADE_COOLDOWN_SECONDS:
        print("🕒 Cooldown active. Waiting before next trade.")
        return

    if get_wallet_balance() < MIN_WALLET_BALANCE_SOL:
        print("🚫 Wallet balance too low. Skipping trade.")
        return

    if session_spent >= MAX_SESSION_BUDGET_SOL:
        print("💰 Max session budget reached. Skipping trade.")
        return

    volatility = get_market_volatility()
    quantity = calculate_trade_size(volatility)

    price = fetch_price(token_address)
    if price is None:
        print("❌ Could not fetch price. Trade aborted.")
        return

    stop_loss = max(trade_settings["dynamic_risk_management"]["min_stop_loss"],
                    trade_settings["dynamic_risk_management"]["max_stop_loss"] * volatility)
    profit_target = min(trade_settings["dynamic_risk_management"]["max_profit_target"],
                        trade_settings["dynamic_risk_management"]["min_profit_target"] * (1 / volatility))

    if action == "buy":
        print(f"🛒 Buying {quantity} of {token_address} at ${price:.4f} (Volatility: {volatility})")
        send_trade_transaction(token_address, quantity, price, side="buy")
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(safe_send_telegram_message(
                f"✅ Bought {quantity} of {token_address} at ${price:.4f} (Volatility: {volatility})"
            ))
        except RuntimeError:
            asyncio.run(safe_send_telegram_message(
                f"✅ Bought {quantity} of {token_address} at ${price:.4f} (Volatility: {volatility})"
            ))
        log_trade_result("buy", token_address, price, quantity, 0, "success")
        add_position(token_address, quantity, price, "dex")

    elif action == "sell":
        position = get_position(token_address)
        entry_price = position["price"] if position else price
        profit_loss = round((price - entry_price) * quantity, 6)
        print(f"📤 Selling {quantity} of {token_address} at ${price:.4f} with P/L: ${profit_loss:.4f} (Volatility: {volatility})")
        send_trade_transaction(token_address, quantity, price, side="sell")
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(safe_send_telegram_message(
                f"✅ Sold {quantity} of {token_address} at ${price:.4f} with P/L: ${profit_loss:.4f} (Volatility: {volatility})"
            ))
        except RuntimeError:
            asyncio.run(safe_send_telegram_message(
                f"✅ Sold {quantity} of {token_address} at ${price:.4f} with P/L: ${profit_loss:.4f} (Volatility: {volatility})"
            ))
        log_trade_result("sell", token_address, price, quantity, profit_loss, "success")
        remove_position(token_address)

    session_spent += price * quantity
    last_trade_time = time.time()
    time.sleep(2)
    return price


def check_for_auto_sell():
    for token in get_all_positions():
        position = get_position(token)
        if not position:
            continue

        current_price = fetch_price(token)
        if current_price is None:
            continue

        entry_price = position["price"]
        profit_pct = ((current_price - entry_price) / entry_price) * 100

        if profit_pct >= trade_settings["profit_target"]:
            print(f"💰 Profit target hit for {token}. Auto-selling.")
            execute_trade("sell", token)
        elif profit_pct <= trade_settings["stop_loss"]:
            print(f"🔻 Stop-loss triggered for {token}. Auto-selling.")
            execute_trade("sell", token)
