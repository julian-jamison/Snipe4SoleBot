import time
import requests
from utils import fetch_price, log_trade_result
from telegram_notifications import send_telegram_message
from decrypt_config import config
trade_settings = config["trade_settings"]

DEX_APIS = {
    "raydium": "https://api.raydium.io/v2/sdk/liquidity_pools",
    "jupiter": "https://quote-api.jup.ag/v4/quote?inputMint=SOL",
    "orca": "https://api.orca.so/pools",
    # "serum": "https://serum-api.bonfida.com/pools",
    # "meteora": "https://api.meteora.ag/pools",
    "pumpfun": "https://pump.fun/api/liquidity_pools"
}

def get_new_liquidity_pools():
    """Fetches new liquidity pools across all supported DEXs."""
    new_pools = []
    
    for dex, api_url in DEX_APIS.items():
        try:
            try:
    response = requests.get(api_url, timeout=5)
    response.raise_for_status()
    data = response.json()
except Exception as e:
    print(f"❌ Failed to fetch from {dex}: {e}")
    continue
            
            for pool in response:
                if "baseMint" in pool:
                    token_address = pool["baseMint"]
                    liquidity = pool.get("liquidity", 0)
                    
                    if liquidity < trade_settings["min_liquidity"]:
                        print(f"🚨 Skipping {token_address} on {dex} due to low liquidity ({liquidity}).")
                        continue  # Skip pools with low liquidity
                    
                    new_pools.append({"dex": dex, "token": token_address, "liquidity": liquidity})
                    
        except Exception as e:
            print(f"❌ Error fetching {dex} liquidity pools: {e}")

    return sorted(new_pools, key=lambda x: x["liquidity"], reverse=True)  # Prioritize highest liquidity

def calculate_trade_size(volatility):
    """Dynamically adjusts trade size based on market volatility."""
    base_quantity = 100  # Default trade size
    if volatility > trade_settings["dynamic_risk_management"]["volatility_threshold"]:
        return base_quantity * 0.5  # Reduce trade size in high volatility
    elif volatility < 0.02:
        return base_quantity * 1.5  # Increase trade size in low volatility
    return base_quantity

def get_market_volatility():
    """Simulates fetching market volatility (replace with real API if available)."""
    import random
    return round(random.uniform(0.01, 0.06), 4)  # Example volatility range

def execute_trade(action, token_address):
    """Executes a trade (buy/sell) based on the given action and market conditions."""
    
    price = fetch_price(token_address)
    if price is None:
        print("❌ Could not fetch price. Trade aborted.")
        return

    volatility = get_market_volatility()
    quantity = calculate_trade_size(volatility)
    
    # Dynamic Stop-Loss & Profit-Target Adjustment
    stop_loss = max(trade_settings["dynamic_risk_management"]["min_stop_loss"],
                    trade_settings["dynamic_risk_management"]["max_stop_loss"] * volatility)
    profit_target = min(trade_settings["dynamic_risk_management"]["max_profit_target"],
                        trade_settings["dynamic_risk_management"]["min_profit_target"] * (1/volatility))

    if action == "buy":
        print(f"🛒 Buying {quantity} of {token_address} at ${price} (Volatility: {volatility})")
        send_telegram_message(f"✅ Bought {quantity} of {token_address} at ${price} (Volatility: {volatility})")
        log_trade_result("buy", token_address, price, quantity, 0, "success")

    elif action == "sell":
        profit_loss = 10  # Example P/L calculation
        print(f"📤 Selling {quantity} of {token_address} at ${price} with P/L: ${profit_loss} (Volatility: {volatility})")
        send_telegram_message(f"✅ Sold {quantity} of {token_address} at ${price} with P/L: {profit_loss} (Volatility: {volatility})")
        log_trade_result("sell", token_address, price, quantity, profit_loss, "success")

    time.sleep(2)
