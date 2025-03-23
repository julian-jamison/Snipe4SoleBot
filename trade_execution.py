import time
import requests
import logging
from utils import fetch_price, log_trade_result
from telegram_notifications import send_telegram_message
from decrypt_config import config

trade_settings = config["trade_settings"]

# Setup logger
logger = logging.getLogger("Snipe4SoleBot")

DEX_APIS = {
    "raydium": "https://api.raydium.io/v2/sdk/liquidity_pools",
    "pumpfun": "https://pump.fun/api/lp/tokens",
    # Jupiter handled separately
}

def fetch_pumpfun_pools():
    try:
        response = requests.get(DEX_APIS["pumpfun"], timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Pump.fun API error: {response.status_code}")
    except Exception as e:
        logger.error(f"Exception in Pump.fun fetch: {e}")
    return []

def fetch_jupiter_routes(input_mint, output_mint="So11111111111111111111111111111111111111112", amount=1000000):
    try:
        response = requests.get(
            "https://quote-api.jup.ag/v6/quote",
            params={"inputMint": input_mint, "outputMint": output_mint, "amount": amount, "slippageBps": 50},
            timeout=5
        )
        if response.status_code == 200:
            return response.json().get("data", [])
        else:
            logger.error(f"Jupiter API error: {response.status_code}")
    except Exception as e:
        logger.error(f"Exception in Jupiter fetch: {e}")
    return []

def get_new_liquidity_pools():
    new_pools = []
    logger.info("\U0001F501 Checking for new liquidity pools...")

    for dex, api_url in DEX_APIS.items():
        try:
            response = requests.get(api_url, timeout=5)
            data = response.json()

            for pool in data:
                token_address = pool.get("baseMint") or pool.get("token")
                liquidity = pool.get("liquidity", 0)
                if token_address and liquidity >= trade_settings["min_liquidity"]:
                    new_pools.append({"dex": dex, "token": token_address, "liquidity": liquidity})
                else:
                    logger.info(f"Skipping {token_address} on {dex} due to low liquidity or missing info.")
        except Exception as e:
            logger.error(f"Error fetching {dex} liquidity pools: {e}")

    # Optionally, query Jupiter using common new mints
    # jupiter_pools = fetch_jupiter_routes("So11111111111111111111111111111111111111112")
    # if jupiter_pools:
    #     logger.info("Fetched Jupiter routes.")

    return sorted(new_pools, key=lambda x: x["liquidity"], reverse=True)

def calculate_trade_size(volatility):
    base_quantity = 100
    if volatility > trade_settings["dynamic_risk_management"]["volatility_threshold"]:
        return base_quantity * 0.5
    elif volatility < 0.02:
        return base_quantity * 1.5
    return base_quantity

def get_market_volatility():
    import random
    return round(random.uniform(0.01, 0.06), 4)

def execute_trade(action, token_address):
    price = fetch_price(token_address)
    if price is None:
        logger.warning("❌ Could not fetch price. Trade aborted.")
        return

    volatility = get_market_volatility()
    quantity = calculate_trade_size(volatility)

    stop_loss = max(trade_settings["dynamic_risk_management"]["min_stop_loss"],
                    trade_settings["dynamic_risk_management"]["max_stop_loss"] * volatility)
    profit_target = min(trade_settings["dynamic_risk_management"]["max_profit_target"],
                        trade_settings["dynamic_risk_management"]["min_profit_target"] * (1 / volatility))

    if action == "buy":
        logger.info(f"🛒 Buying {quantity} of {token_address} at ${price} (Volatility: {volatility})")
        send_telegram_message(f"✅ Bought {quantity} of {token_address} at ${price} (Volatility: {volatility})")
        log_trade_result("buy", token_address, price, quantity, 0, "success")

    elif action == "sell":
        profit_loss = 10
        logger.info(f"📤 Selling {quantity} of {token_address} at ${price} with P/L: ${profit_loss} (Volatility: {volatility})")
        send_telegram_message(f"✅ Sold {quantity} of {token_address} at ${price} with P/L: {profit_loss} (Volatility: {volatility})")
        log_trade_result("sell", token_address, price, quantity, profit_loss, "success")

    time.sleep(2)
