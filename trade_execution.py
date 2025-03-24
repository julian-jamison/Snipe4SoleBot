import time
import requests
import os
import random
import json
from utils import fetch_price, log_trade_result
from telegram_notifications import send_telegram_message
from decrypt_config import config
from portfolio import add_position, remove_position, get_position

trade_settings = config["trade_settings"]
BACKTEST_MODE = os.getenv("BACKTEST_MODE", "false").lower() == "true"
MOCK_DATA_FILE = "mock_pools.json"

DEX_APIS = {
    "raydium": "https://api.raydium.io/v2/sdk/liquidity_pools",
    "jupiter": "https://quote-api.jup.ag/v4/quote?inputMint=SOL",
    "orca": "https://api.orca.so/pools",
    "pumpfun": "https://pump.fun/api/liquidity_pools"
}

def get_new_liquidity_pools():
    """Fetches new liquidity pools across all supported DEXs."""
    if BACKTEST_MODE:
        return load_mock_pools()

    new_pools = []

    for dex, api_url in DEX_APIS.items():
        try:
            response = requests.get(api_url, timeout=5)
            response.raise_for_status()
            data = response.json()

            for pool in data:
                token_address = pool.get("baseMint") or pool.get("mint")
                liquidity = pool.get("liquidity", 0)

                if token_address and liquidity >= trade_settings["min_liquidity"]:
                    new_pools.append({"dex": dex, "token": token_address, "liquidity": liquidity})

        except Exception as e:
            print(f"❌ Error fetching {dex} liquidity pools: {e}")
            continue

    return sorted(new_pools, key=lambda x: x["liquidity"], reverse=True)

def load_mock_pools():
    """Loads mock liquidity pool data for backtesting."""
    try:
        with open(MOCK_DATA_FILE, "r") as f:
            mock_data = json.load(f)
            return sorted(mock_data, key=lambda x: x["liquidity"], reverse=True)
    except Exception as e:
        print(f"⚠️ Could not load mock pool data: {e}")
        return []

def get_market_volatility():
    """Simulates fetching market volatility (replace with real API if needed)."""
    return round(random.uniform(0.01, 0.06), 4)  # Example volatility range

def calculate_trade_size(volatility):
    """Dynamically adjusts trade size based on market volatility."""
    base_quantity = 100
    if volatility > trade_settings["dynamic_risk_management"]["volatility_threshold"]:
        return base_quantity * 0.5
    elif volatility < 0.02:
        return base_quantity * 1.5
    return base_quantity

def execute_trade(action, token_address):
    """Executes a trade (buy/sell) based on the given action and market conditions."""
    volatility = get_market_volatility()
    quantity = calculate_trade_size(volatility)

    if BACKTEST_MODE:
        price = round(random.uniform(0.001, 0.02), 6)  # Simulate price
        print(f"[BACKTEST] {action.upper()} {quantity} of {token_address} at ${price:.4f}")
        send_telegram_message(f"[BACKTEST] {action.upper()} {quantity} of {token_address} at ${price:.4f}")
        log_trade_result(action, token_address, price, quantity, 0, "simulated")
        return price

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
        send_telegram_message(f"✅ Bought {quantity} of {token_address} at ${price:.4f} (Volatility: {volatility})")
        log_trade_result("buy", token_address, price, quantity, 0, "success")
        add_position(token_address, quantity, price, "dex")

    elif action == "sell":
        position = get_position(token_address)
        entry_price = position["price"] if position else price
        profit_loss = round((price - entry_price) * quantity, 6)
        print(f"📤 Selling {quantity} of {token_address} at ${price:.4f} with P/L: ${profit_loss:.4f} (Volatility: {volatility})")
        send_telegram_message(f"✅ Sold {quantity} of {token_address} at ${price:.4f} with P/L: ${profit_loss:.4f} (Volatility: {volatility})")
        log_trade_result("sell", token_address, price, quantity, profit_loss, "success")
        remove_position(token_address)

    time.sleep(2)
    return price
