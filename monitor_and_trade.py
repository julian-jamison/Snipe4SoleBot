import time
import asyncio
import threading
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
import random

from trade_execution import (
    buy_token_multi_wallet, 
    sell_token_auto_withdraw,
    fetch_price
)
from telegram_notifications import safe_send_telegram_message
from whale_tracking import get_whale_transactions
from utils import get_token_price, should_buy_token, get_random_wallet
from portfolio import get_all_positions, get_position
from decrypt_config import config

# ---------------------------------------------------------------------------
# >>> PRIVATE KEY ACCESS <<<
private_key_hex = config["solana_wallets"].get("private_key_hex")
if not private_key_hex or len(private_key_hex) != 128:
    raise ValueError(
        f"Private key not valid hex: must be 128 hex chars (64 bytes for Solana keypair), got {len(private_key_hex) if private_key_hex else 0}"
    )
def get_trading_key():
    return private_key_hex
# ---------------------------------------------------------------------------

# Logger
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# Token constants
SOLANA_NATIVE_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_MINT = "Es9vMFrzaCERiE2dZVjW6M9T3cxLVRshzF5sgJnpPzM9"

# Strategy config
STRATEGY_CONFIG = {
    "sniper": {
        "enabled": True,
        "max_concurrent_positions": 3,
        "profit_target_percent": 10,
        "stop_loss_percent": -5,
        "check_interval_seconds": 2
    },
    "arbitrage": {
        "enabled": True,
        "min_price_difference_percent": 1.0,
        "max_concurrent_trades": 2,
        "check_interval_seconds": 30,
        "tokens_to_monitor": [SOLANA_NATIVE_MINT, USDC_MINT, USDT_MINT]
    },
    "market_making": {
        "enabled": True,
        "min_spread_percent": 1.0,
        "max_concurrent_pools": 2,
        "order_refresh_seconds": 60,
        "check_interval_seconds": 300
    },
    "trend_following": {
        "enabled": True,
        "timeframes": ["4h"],
        "max_concurrent_positions": 3,
        "position_size_percent": 10,  # Percent of available capital
        "check_interval_seconds": 3600,  # 1 hour
        "tokens_to_monitor": []  # Will be populated from config
    }
}

try:
    STRATEGY_CONFIG["trend_following"]["tokens_to_monitor"] = config.get("trend_following_tokens", [])
except Exception as e:
    LOGGER.error(f"Failed to load trend following tokens: {e}")
    STRATEGY_CONFIG["trend_following"]["tokens_to_monitor"] = [
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        "9vMJfxuKxXBoEa7rM12gYLMwTacLMLDJqHozw96WQL8i",  # UST
        "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj",  # stSOL
        "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",    # mSOL
    ]

active_trades = {
    "sniper": set(),
    "arbitrage": set(),
    "market_making": set(),
    "trend_following": set()
}

running = True
threads = []

async def send_telegram_message_async(message):
    """Send telegram message asynchronously"""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(safe_send_telegram_message(message))
    except RuntimeError:
        asyncio.run(safe_send_telegram_message(message))

# Or if it should be a regular function:
def send_telegram_message(message):
    """Send telegram message"""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(safe_send_telegram_message(message))
    except RuntimeError:
        asyncio.run(safe_send_telegram_message(message))

def get_new_liquidity_pools():
    try:
        return []
    except Exception as e:
        LOGGER.error(f"Error fetching new liquidity pools: {e}")
        return []

def find_arbitrage_opportunities(tokens_to_monitor):
    try:
        return []
    except Exception as e:
        LOGGER.error(f"Error finding arbitrage opportunities: {e}")
        return []

def execute_arbitrage(opportunity, wallet):
    try:
        return {"profit": 0.01}
    except Exception as e:
        LOGGER.error(f"Error executing arbitrage: {e}")
        return None

def find_market_making_opportunities(min_spread_percent):
    try:
        return []
    except Exception as e:
        LOGGER.error(f"Error finding market making opportunities: {e}")
        return []

async def execute_market_making(pool_info, wallet):
    try:
        return {"spread_percent": 1.5}
    except Exception as e:
        LOGGER.error(f"Error executing market making: {e}")
        return None

async def analyze_token_trend(token_mint, timeframe):
    try:
        return {
            "token_mint": token_mint,
            "timeframe": timeframe,
            "trend": random.choice(["bullish", "bearish", "neutral"])
        }
    except Exception as e:
        LOGGER.error(f"Error analyzing token trend: {e}")
        return {"token_mint": token_mint, "trend": "neutral"}

async def execute_trend_following_trade(trend_data, wallet):
    try:
        return {
            "action": "buy",
            "price": 1.0
        }
    except Exception as e:
        LOGGER.error(f"Error executing trend following trade: {e}")
        return None

async def update_trend_following_stops():
    try:
        pass
    except Exception as e:
        LOGGER.error(f"Error updating trend following stops: {e}")

def sniper_loop():
    LOGGER.info("🚀 Sniper bot running with Automatic Withdrawals...")
    send_telegram_message("🚀 Snipe4SoleBot is LIVE and scanning for new liquidity pools!")

    while running:
        if len(active_trades["sniper"]) >= STRATEGY_CONFIG["sniper"]["max_concurrent_positions"]:
            time.sleep(STRATEGY_CONFIG["sniper"]["check_interval_seconds"])
            continue
        try:
            new_pools = get_new_liquidity_pools()
            for pool in new_pools:
                if not running:
                    break
                token_address = pool.get("baseMint") or pool.get("mint") or pool.get("token_a")
                if not token_address:
                    continue
                LOGGER.info(f"🔹 New liquidity detected: {token_address}")
                send_telegram_message(f"🚀 New liquidity detected: {token_address}")
                whale_buys, whale_sells = get_whale_transactions(token_address)
                if whale_buys > 100:
                    send_telegram_message(f"🐋 WHALE ALERT! {whale_buys} SOL worth of {token_address} just bought!")
                if whale_sells > 50:
                    send_telegram_message(f"⚠️ Warning! {whale_sells} SOL worth of {token_address} just sold!")
                if should_buy_token(token_address) and token_address not in active_trades["sniper"]:
                    selected_wallet = get_random_wallet()
                    send_telegram_message(f"🛒 Buying {token_address} with wallet {selected_wallet.pubkey()}.")
                    active_trades["sniper"].add(token_address)
                    buy_result = buy_token_multi_wallet(token_address, selected_wallet)
                    if not buy_result:
                        LOGGER.error(f"Failed to buy {token_address}")
                        active_trades["sniper"].remove(token_address)
                        continue
                    initial_price = get_token_price(token_address)
                    monitor_thread = threading.Thread(
                        target=monitor_sniper_position,
                        args=(token_address, selected_wallet, initial_price),
                        daemon=True
                    )
                    monitor_thread.start()
                    threads.append(monitor_thread)
                else:
                    send_telegram_message(f"❌ Skipping {token_address}. Doesn't meet buy criteria.")
        except Exception as e:
            LOGGER.error(f"Error in sniper loop: {e}")
        time.sleep(STRATEGY_CONFIG["sniper"]["check_interval_seconds"])

def monitor_sniper_position(token_address, wallet, initial_price):
    LOGGER.info(f"🔍 Monitoring position for {token_address}")
    profit_target = STRATEGY_CONFIG["sniper"]["profit_target_percent"]
    stop_loss = STRATEGY_CONFIG["sniper"]["stop_loss_percent"]
    while running and token_address in active_trades["sniper"]:
        try:
            current_price = get_token_price(token_address)
            if not current_price:
                time.sleep(STRATEGY_CONFIG["sniper"]["check_interval_seconds"])
                continue
            profit = (current_price - initial_price) / initial_price * 100
            if profit >= profit_target:
                LOGGER.info(f"🎯 Profit target reached for {token_address}: {profit:.2f}%")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                sell_result = loop.run_until_complete(sell_token_auto_withdraw(token_address, wallet))
                if sell_result:
                    send_telegram_message(f"✅ Sold {token_address} for {profit:.2f}% profit! Profits withdrawn.")
                    active_trades["sniper"].remove(token_address)
                    break
            elif profit <= stop_loss:
                LOGGER.info(f"🛑 Stop loss triggered for {token_address}: {profit:.2f}%")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                sell_result = loop.run_until_complete(sell_token_auto_withdraw(token_address, wallet))
                if sell_result:
                    send_telegram_message(f"❌ Stop-loss triggered! Sold {token_address} at {profit:.2f}% loss.")
                    active_trades["sniper"].remove(token_address)
                    break
        except Exception as e:
            LOGGER.error(f"Error monitoring {token_address}: {e}")
        time.sleep(STRATEGY_CONFIG["sniper"]["check_interval_seconds"])

def arbitrage_loop():
    LOGGER.info("💱 Cross-DEX Arbitrage bot running...")
    send_telegram_message("💱 Cross-DEX Arbitrage bot is now active and searching for opportunities!")
    while running:
        if len(active_trades["arbitrage"]) >= STRATEGY_CONFIG["arbitrage"]["max_concurrent_trades"]:
            time.sleep(STRATEGY_CONFIG["arbitrage"]["check_interval_seconds"])
            continue
        try:
            opportunities = find_arbitrage_opportunities(STRATEGY_CONFIG["arbitrage"]["tokens_to_monitor"])
            opportunities.sort(key=lambda x: x.get("price_diff_percent", 0), reverse=True)
            for opportunity in opportunities:
                if not running or len(active_trades["arbitrage"]) >= STRATEGY_CONFIG["arbitrage"]["max_concurrent_trades"]:
                    break
                token_mint = opportunity.get("token_mint")
                price_diff = opportunity.get("price_diff_percent", 0)
                if price_diff >= STRATEGY_CONFIG["arbitrage"]["min_price_difference_percent"] and token_mint not in active_trades["arbitrage"]:
                    LOGGER.info(f"💹 Found arbitrage opportunity for {token_mint} with {price_diff:.2f}% difference")
                    send_telegram_message(f"💹 Executing arbitrage for {token_mint} with {price_diff:.2f}% price difference")
                    active_trades["arbitrage"].add(token_mint)
                    arb_thread = threading.Thread(
                        target=execute_arbitrage_trade,
                        args=(opportunity,),
                        daemon=True
                    )
                    arb_thread.start()
                    threads.append(arb_thread)
        except Exception as e:
            LOGGER.error(f"Error in arbitrage loop: {e}")
        time.sleep(STRATEGY_CONFIG["arbitrage"]["check_interval_seconds"])

def execute_arbitrage_trade(opportunity):
    token_mint = opportunity.get("token_mint")
    try:
        wallet = get_random_wallet()
        result = execute_arbitrage(opportunity, wallet)
        if result:
            profit = result.get("profit", 0)
            send_telegram_message(f"✅ Arbitrage complete for {token_mint}! Profit: ${profit:.4f}")
        else:
            send_telegram_message(f"❌ Arbitrage failed for {token_mint}")
    except Exception as e:
        LOGGER.error(f"Error executing arbitrage for {token_mint}: {e}")
    finally:
        if token_mint in active_trades["arbitrage"]:
            active_trades["arbitrage"].remove(token_mint)

def market_making_loop():
    LOGGER.info("📊 Market Making bot running...")
    send_telegram_message("📊 Market Making bot is now active and searching for wide-spread pools!")
    active_mm_pools = {}
    while running:
        if len(active_trades["market_making"]) >= STRATEGY_CONFIG["market_making"]["max_concurrent_pools"]:
            current_time = time.time()
            for pool_address, pool_data in list(active_mm_pools.items()):
                if current_time - pool_data.get("last_refresh", 0) >= STRATEGY_CONFIG["market_making"]["order_refresh_seconds"]:
                    refresh_thread = threading.Thread(
                        target=refresh_market_making_orders,
                        args=(pool_address, pool_data),
                        daemon=True
                    )
                    refresh_thread.start()
                    threads.append(refresh_thread)
            time.sleep(STRATEGY_CONFIG["market_making"]["check_interval_seconds"])
            continue
        try:
            wide_spread_pools = find_market_making_opportunities(STRATEGY_CONFIG["market_making"]["min_spread_percent"])
            wide_spread_pools.sort(key=lambda x: x.get("spread_percent", 0), reverse=True)
            for pool in wide_spread_pools:
                if not running or len(active_trades["market_making"]) >= STRATEGY_CONFIG["market_making"]["max_concurrent_pools"]:
                    break
                pool_address = pool.get("pool_address")
                spread_percent = pool.get("spread_percent", 0)
                if pool_address not in active_trades["market_making"]:
                    LOGGER.info(f"📈 Found market making opportunity for pool {pool_address} with {spread_percent:.2f}% spread")
                    send_telegram_message(f"📈 Setting up market making for pool with {spread_percent:.2f}% spread")
                    active_trades["market_making"].add(pool_address)
                    mm_thread = threading.Thread(
                        target=setup_market_making,
                        args=(pool,),
                        daemon=True
                    )
                    mm_thread.start()
                    threads.append(mm_thread)
        except Exception as e:
            LOGGER.error(f"Error in market making loop: {e}")
        time.sleep(STRATEGY_CONFIG["market_making"]["check_interval_seconds"])

def setup_market_making(pool_info):
    pool_address = pool_info.get("pool_address")
    try:
        wallet = get_random_wallet()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(execute_market_making(pool_info, wallet))
        if result:
            active_mm_pools[pool_address] = {
                "pool_info": pool_info,
                "orders": result,
                "wallet": wallet,
                "last_refresh": time.time()
            }
            send_telegram_message(f"✅ Market making set up for pool with {result.get('spread_percent', 0):.2f}% spread")
        else:
            send_telegram_message(f"❌ Failed to set up market making for pool")
            if pool_address in active_trades["market_making"]:
                active_trades["market_making"].remove(pool_address)
    except Exception as e:
        LOGGER.error(f"Error setting up market making for {pool_address}: {e}")
        if pool_address in active_trades["market_making"]:
            active_trades["market_making"].remove(pool_address)

def refresh_market_making_orders(pool_address, pool_data):
    try:
        pool_info = pool_data.get("pool_info")
        wallet = pool_data.get("wallet")
        LOGGER.info(f"🔄 Refreshing market making orders for pool {pool_address}")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(execute_market_making(pool_info, wallet))
        if result:
            pool_data["orders"] = result
            pool_data["last_refresh"] = time.time()
            LOGGER.info(f"✅ Refreshed market making orders for pool {pool_address}")
        else:
            LOGGER.error(f"❌ Failed to refresh market making orders for pool {pool_address}")
    except Exception as e:
        LOGGER.error(f"Error refreshing market making orders for {pool_address}: {e}")

def trend_following_loop():
    LOGGER.info("📈 Trend Following bot running...")
    send_telegram_message("📈 Trend Following bot is now active and analyzing token trends!")
    time.sleep(60)
    while running:
        try:
            update_stops_thread = threading.Thread(
                target=update_trend_stops,
                daemon=True
            )
            update_stops_thread.start()
            threads.append(update_stops_thread)
            if len(active_trades["trend_following"]) < STRATEGY_CONFIG["trend_following"]["max_concurrent_positions"]:
                for token_mint in STRATEGY_CONFIG["trend_following"]["tokens_to_monitor"]:
                    if token_mint in active_trades["trend_following"]:
                        continue
                    for timeframe in STRATEGY_CONFIG["trend_following"]["timeframes"]:
                        LOGGER.info(f"📊 Analyzing trend for {token_mint} on {timeframe} timeframe")
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        trend_data = loop.run_until_complete(analyze_token_trend(token_mint, timeframe))
                        if trend_data.get("trend") == "bullish":
                            LOGGER.info(f"📈 Bullish trend detected for {token_mint} on {timeframe}")
                            send_telegram_message(f"📈 Bullish trend detected for {token_mint} - Entering position")
                            active_trades["trend_following"].add(token_mint)
                            trend_thread = threading.Thread(
                                target=execute_trend_trade,
                                args=(trend_data,),
                                daemon=True
                            )
                            trend_thread.start()
                            threads.append(trend_thread)
                            break
        except Exception as e:
            LOGGER.error(f"Error in trend following loop: {e}")
        time.sleep(STRATEGY_CONFIG["trend_following"]["check_interval_seconds"])

def execute_trend_trade(trend_data):
    token_mint = trend_data.get("token_mint")
    try:
        wallet = get_random_wallet()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(execute_trend_following_trade(trend_data, wallet))
        if result:
            action = result.get("action")
            price = result.get("price", 0)
            if action == "buy":
                send_telegram_message(f"✅ Entered trend following position for {token_mint} at ${price:.6f}")
            elif action == "sell":
                send_telegram_message(f"✅ Exited trend following position for {token_mint} at ${price:.6f}")
                if token_mint in active_trades["trend_following"]:
                    active_trades["trend_following"].remove(token_mint)
        else:
            if token_mint in active_trades["trend_following"]:
                active_trades["trend_following"].remove(token_mint)
    except Exception as e:
        LOGGER.error(f"Error executing trend trade for {token_mint}: {e}")
        if token_mint in active_trades["trend_following"]:
            active_trades["trend_following"].remove(token_mint)

def update_trend_stops():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(update_trend_following_stops())
    except Exception as e:
        LOGGER.error(f"Error updating trend following stops: {e}")

def start_all_strategies():
    global threads
    if STRATEGY_CONFIG["sniper"]["enabled"]:
        sniper_thread = threading.Thread(target=sniper_loop, daemon=True)
        sniper_thread.start()
        threads.append(sniper_thread)
        LOGGER.info("🚀 Started Sniper strategy")
    if STRATEGY_CONFIG["arbitrage"]["enabled"]:
        arbitrage_thread = threading.Thread(target=arbitrage_loop, daemon=True)
        arbitrage_thread.start()
        threads.append(arbitrage_thread)
        LOGGER.info("💱 Started Cross-DEX Arbitrage strategy")
    if STRATEGY_CONFIG["market_making"]["enabled"]:
        market_making_thread = threading.Thread(target=market_making_loop, daemon=True)
        market_making_thread.start()
        threads.append(market_making_thread)
        LOGGER.info("📊 Started Market Making strategy")
    if STRATEGY_CONFIG["trend_following"]["enabled"]:
        trend_following_thread = threading.Thread(target=trend_following_loop, daemon=True)
        trend_following_thread.start()
        threads.append(trend_following_thread)
        LOGGER.info("📈 Started Trend Following strategy")
    return threads

def stop_all_strategies():
    global running
    running = False
    LOGGER.info("🛑 Stopping all strategies...")
    send_telegram_message("🛑 Stopping all trading strategies. Please wait...")
    for thread in threads:
        if thread.is_alive():
            thread.join(timeout=5)
    LOGGER.info("✅ All strategies stopped")
    send_telegram_message("✅ All trading strategies have been stopped")

def start_sniper_thread():
    if STRATEGY_CONFIG["sniper"]["enabled"]:
        thread = threading.Thread(target=sniper_loop, daemon=True)
        thread.start()
        threads.append(thread)
        return thread
    return None

if __name__ == "__main__":
    send_telegram_message("🚀 Snipe4SoleBot starting all trading strategies...")
    strategy_threads = start_all_strategies()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_all_strategies()
