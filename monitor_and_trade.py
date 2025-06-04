import time
import asyncio
import threading
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
import random
import requests

# Import from existing modules
from telegram_notifications import send_telegram_message
from whale_tracking import get_whale_transactions
from portfolio import get_all_positions, get_position
from decrypt_config import config

# Import real trading functionality
from real_trading_integration import (
    is_real_trading_enabled, 
    get_new_liquidity_pools_real,
    buy_token_multi_wallet, 
    sell_token_auto_withdraw,
    get_wallet_balance,
    fetch_token_price,
    should_buy_token,
    monitor_position,
    initialize_real_trading
)

# Initialize logger
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# Define token constants
SOLANA_NATIVE_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_MINT = "Es9vMFrzaCERiE2dZVjW6M9T3cxLVRshzF5sgJnpPzM9"

# Track processed pools to avoid duplicates
processed_pools = set()

# Initialize real trading if enabled
REAL_TRADER = None
if is_real_trading_enabled():
    REAL_TRADER = initialize_real_trading()

# Define additional utility functions that were removed from imports
def get_random_wallet():
    """
    Get a random wallet for trading.
    For testing, we'll return a simple object with a pubkey method.
    """
    class MockWallet:
        def __init__(self, address):
            self._address = address
            
        def pubkey(self):
            return self._address
    
    return MockWallet(f"Random{random.randint(1000, 9999)}")

def get_token_price(token_address):
    """Get token price using real or mock implementation."""
    return fetch_token_price(token_address)

def get_new_liquidity_pools():
    """Get new liquidity pools from the market."""
    # First try to get real pools if real trading is enabled
    if is_real_trading_enabled():
        real_pools = get_new_liquidity_pools_real()
        if real_pools:
            return real_pools
    
    # Fall back to mock implementation if real trading disabled or no real pools found
    try:
        # Get recent liquidity pools via Birdeye API
        url = "https://public-api.birdeye.so/defi/new_pools"
        headers = {"X-API-KEY": "cc8ff825-27de-4804-9f6e-5bbb5a40fc3a"}
        params = {
            "time_after": int(time.time() - 180),  # Pools in the last 3 minutes
            "offset": 0,
            "limit": 5
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code != 200:
            LOGGER.warning(f"Error fetching new pools: {response.status_code} - {response.text}")
            return []
            
        data = response.json()
        if "data" not in data or "items" not in data["data"]:
            LOGGER.warning(f"Unexpected response format: {data}")
            return []
            
        pools = []
        for item in data["data"]["items"]:
            pool = {
                "baseMint": item.get("base_mint", item.get("token_address", "")),
                "quoteMint": item.get("quote_mint", ""),
                "liquidity": item.get("liquidity", 0),
                "volume24h": item.get("volume24h", 0),
                "created_at": item.get("created_at", ""),
                "pool_id": item.get("pool_id", ""),
                "dex": item.get("dex", "")
            }
            pools.append(pool)
            
        LOGGER.info(f"Found {len(pools)} new liquidity pools")
        return pools
    except Exception as e:
        LOGGER.error(f"Error fetching new liquidity pools: {e}")
        return []

def find_arbitrage_opportunities(tokens_to_monitor):
    """Find arbitrage opportunities for the given tokens (mock implementation)."""
    # For testing, just return 0-1 random opportunities
    if random.random() < 0.7:  # 70% chance of no opportunities
        return []
    
    token_mint = random.choice(tokens_to_monitor)
    price_diff = random.uniform(1.0, 5.0)
    
    opportunity = {
        "token_mint": token_mint,
        "price_diff_percent": price_diff,
        "exchange_a": "Exchange" + str(random.randint(1, 3)),
        "exchange_b": "Exchange" + str(random.randint(4, 6)),
        "price_a": random.uniform(0.9, 1.1),
        "price_b": random.uniform(1.1, 1.2)
    }
    
    return [opportunity]

def execute_arbitrage(opportunity, wallet):
    """Execute an arbitrage trade (mock implementation)."""
    # 80% chance of successful arbitrage
    if random.random() < 0.8:
        profit = opportunity["price_diff_percent"] / 100.0 * random.uniform(0.1, 1.0)
        return {
            "success": True,
            "profit": profit,
            "token": opportunity["token_mint"],
            "timestamp": datetime.now().isoformat()
        }
    else:
        return None

def find_market_making_opportunities(min_spread_percent):
    """Find market making opportunities (mock implementation)."""
    # For testing, just return 0-1 random opportunities
    if random.random() < 0.7:  # 70% chance of no opportunities
        return []
    
    # Generate a random pool address
    pool_address = ''.join(random.choice('0123456789abcdef') for _ in range(44))
    spread_percent = random.uniform(min_spread_percent, min_spread_percent * 3)
    
    pool = {
        "pool_address": pool_address,
        "spread_percent": spread_percent,
        "token_a": "Token" + str(random.randint(1, 10)),
        "token_b": "Token" + str(random.randint(11, 20)),
        "liquidity": random.uniform(10000, 100000)
    }
    
    return [pool]

async def execute_market_making(pool_info, wallet):
    """Execute market making for a pool (mock implementation)."""
    # 80% chance of successful market making
    if random.random() < 0.8:
        return {
            "success": True,
            "spread_percent": pool_info["spread_percent"],
            "pool": pool_info["pool_address"],
            "timestamp": datetime.now().isoformat()
        }
    else:
        return None

async def analyze_token_trend(token_mint, timeframe):
    """Analyze the trend for a token (mock implementation)."""
    # Return random trend
    trends = ["bullish", "bearish", "neutral"]
    weights = [0.4, 0.3, 0.3]  # Slightly biased towards bullish
    
    trend = random.choices(trends, weights=weights, k=1)[0]
    
    return {
        "token_mint": token_mint,
        "timeframe": timeframe,
        "trend": trend,
        "confidence": random.uniform(0.6, 0.9),
        "indicators": {
            "rsi": random.uniform(30, 70),
            "macd": random.uniform(-1, 1),
            "volume_change": random.uniform(-10, 20)
        }
    }

async def execute_trend_following_trade(trend_data, wallet):
    """Execute a trend following trade (mock implementation)."""
    # 80% chance of successful trade
    if random.random() < 0.8:
        action = "buy" if trend_data["trend"] == "bullish" else "sell"
        price = random.uniform(0.1, 10.0)
        
        return {
            "success": True,
            "action": action,
            "token": trend_data["token_mint"],
            "price": price,
            "timestamp": datetime.now().isoformat()
        }
    else:
        return None

async def update_trend_following_stops():
    """Update stop losses for trend following positions (mock implementation)."""
    # This function would normally update stop losses for active positions
    # For now, we'll just simulate a delay
    await asyncio.sleep(1)

# Configuration for strategies
STRATEGY_CONFIG = {
    "sniper": {
        "enabled": True,
        "max_concurrent_positions": 3,
        "profit_target_percent": 10,
        "stop_loss_percent": -5,
        "check_interval_seconds": 60
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

# Load tokens for trend following from config
try:
    STRATEGY_CONFIG["trend_following"]["tokens_to_monitor"] = config.get("trend_following_tokens", [])
except Exception as e:
    LOGGER.error(f"Failed to load trend following tokens: {e}")
    STRATEGY_CONFIG["trend_following"]["tokens_to_monitor"] = [
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        "9vMJfxuKxXBoEa7rM12mYLMwTacLMLDJqHozw96WQL8i",  # UST
        "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj",  # stSOL
        "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",  # mSOL
    ]

# Track active trades by strategy
active_trades = {
    "sniper": set(),
    "arbitrage": set(),
    "market_making": set(),
    "trend_following": set()
}

# Global variables
running = True
threads = []
active_mm_pools = {}

def sniper_loop():
    """Main sniper loop with automatic profit withdrawals."""
    LOGGER.info("sniper_loop started")
    if is_real_trading_enabled():
        LOGGER.info("🚀 Sniper bot running with REAL TRADING enabled!")
    else:
        LOGGER.info("sniper_loop started (dummy)")
    
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
                    
                # Skip if already processed
                pool_id = pool.get("pool_id")
                if pool_id and pool_id in processed_pools:
                    continue
                    
                # Add to processed pools
                if pool_id:
                    processed_pools.add(pool_id)

                LOGGER.info(f"🔹 New liquidity detected: {token_address}")
                send_telegram_message(f"🚀 New liquidity detected: {token_address}")

                # Fetch whale transactions (non-async function)
                whale_buys, whale_sells = get_whale_transactions(token_address)

                if whale_buys > 100:
                    send_telegram_message(f"🐋 WHALE ALERT! {whale_buys} SOL worth of {token_address} just bought!")

                if whale_sells > 50:
                    send_telegram_message(f"⚠️ Warning! {whale_sells} SOL worth of {token_address} just sold!")

                # Decide whether to buy
                if should_buy_token(token_address, pool) and token_address not in active_trades["sniper"]:
                    selected_wallet = get_random_wallet()
                    send_telegram_message(f"🛒 Buying {token_address} with wallet {selected_wallet.pubkey()}.")
                    
                    # Add to active trades
                    active_trades["sniper"].add(token_address)
                    
                    # Use real trading implementation
                    buy_result = buy_token_multi_wallet(token_address, [selected_wallet])
                    if not buy_result:
                        LOGGER.error(f"Failed to buy {token_address}")
                        active_trades["sniper"].remove(token_address)
                        continue
                        
                    initial_price = get_token_price(token_address)

                    # Start a monitoring thread for this token
                    monitor_thread = threading.Thread(
                        target=monitor_position,
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

def arbitrage_loop():
    """Loop to find and execute cross-DEX arbitrage opportunities."""
    LOGGER.info("arbitrage_loop started (dummy)")
    send_telegram_message("💱 Cross-DEX Arbitrage bot is now active and searching for opportunities!")
    
    while running:
        if len(active_trades["arbitrage"]) >= STRATEGY_CONFIG["arbitrage"]["max_concurrent_trades"]:
            time.sleep(STRATEGY_CONFIG["arbitrage"]["check_interval_seconds"])
            continue
            
        try:
            # Get arbitrage opportunities for monitored tokens
            opportunities = find_arbitrage_opportunities(STRATEGY_CONFIG["arbitrage"]["tokens_to_monitor"])
            
            # Sort by price difference (highest first)
            opportunities.sort(key=lambda x: x.get("price_diff_percent", 0), reverse=True)
            
            for opportunity in opportunities:
                if not running or len(active_trades["arbitrage"]) >= STRATEGY_CONFIG["arbitrage"]["max_concurrent_trades"]:
                    break
                    
                token_mint = opportunity.get("token_mint")
                price_diff = opportunity.get("price_diff_percent", 0)
                
                # Check if opportunity meets minimum threshold and is not already being traded
                if price_diff >= STRATEGY_CONFIG["arbitrage"]["min_price_difference_percent"] and token_mint not in active_trades["arbitrage"]:
                    LOGGER.info(f"💹 Found arbitrage opportunity for {token_mint} with {price_diff:.2f}% difference")
                    send_telegram_message(f"💹 Executing arbitrage for {token_mint} with {price_diff:.2f}% price difference")
                    
                    # Add to active trades
                    active_trades["arbitrage"].add(token_mint)
                    
                    # Execute arbitrage in a separate thread
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
    """Execute an arbitrage trade and monitor its completion."""
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
        # Remove from active trades
        if token_mint in active_trades["arbitrage"]:
            active_trades["arbitrage"].remove(token_mint)

def market_making_loop():
    """Loop to find and execute market making opportunities."""
    LOGGER.info("market_making_loop started (dummy)")
    send_telegram_message("📊 Market Making bot is now active and searching for wide-spread pools!")
    
    # Track active market making pools
    global active_mm_pools
    active_mm_pools = {}
    
    while running:
        if len(active_trades["market_making"]) >= STRATEGY_CONFIG["market_making"]["max_concurrent_pools"]:
            # Check if any existing pools need order refreshing
            current_time = time.time()
            for pool_address, pool_data in list(active_mm_pools.items()):
                if current_time - pool_data.get("last_refresh", 0) >= STRATEGY_CONFIG["market_making"]["order_refresh_seconds"]:
                    # Refresh orders for this pool
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
            # Find pools with wide spreads
            wide_spread_pools = find_market_making_opportunities(STRATEGY_CONFIG["market_making"]["min_spread_percent"])
            
            # Sort by spread (highest first)
            wide_spread_pools.sort(key=lambda x: x.get("spread_percent", 0), reverse=True)
            
            for pool in wide_spread_pools:
                if not running or len(active_trades["market_making"]) >= STRATEGY_CONFIG["market_making"]["max_concurrent_pools"]:
                    break
                    
                pool_address = pool.get("pool_address")
                spread_percent = pool.get("spread_percent", 0)
                
                # Check if pool is not already being market made
                if pool_address not in active_trades["market_making"]:
                    LOGGER.info(f"📈 Found market making opportunity for pool {pool_address} with {spread_percent:.2f}% spread")
                    send_telegram_message(f"📈 Setting up market making for pool with {spread_percent:.2f}% spread")
                    
                    # Add to active trades
                    active_trades["market_making"].add(pool_address)
                    
                    # Execute market making in a separate thread
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
    """Set up market making for a pool and add it to active pools."""
    pool_address = pool_info.get("pool_address")
    
    try:
        wallet = get_random_wallet()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(execute_market_making(pool_info, wallet))
        
        if result:
            # Add to active market making pools
            active_mm_pools[pool_address] = {
                "pool_info": pool_info,
                "orders": result,
                "wallet": wallet,
                "last_refresh": time.time()
            }
            
            send_telegram_message(f"✅ Market making set up for pool with {result.get('spread_percent', 0):.2f}% spread")
        else:
            send_telegram_message(f"❌ Failed to set up market making for pool")
            
            # Remove from active trades
            if pool_address in active_trades["market_making"]:
                active_trades["market_making"].remove(pool_address)
    
    except Exception as e:
        LOGGER.error(f"Error setting up market making for {pool_address}: {e}")
        
        # Remove from active trades
        if pool_address in active_trades["market_making"]:
            active_trades["market_making"].remove(pool_address)

def refresh_market_making_orders(pool_address, pool_data):
    """Refresh market making orders for a pool."""
    try:
        pool_info = pool_data.get("pool_info")
        wallet = pool_data.get("wallet")
        
        LOGGER.info(f"🔄 Refreshing market making orders for pool {pool_address}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(execute_market_making(pool_info, wallet))
        
        if result:
            # Update pool data
            pool_data["orders"] = result
            pool_data["last_refresh"] = time.time()
            
            LOGGER.info(f"✅ Refreshed market making orders for pool {pool_address}")
        else:
            LOGGER.error(f"❌ Failed to refresh market making orders for pool {pool_address}")
    
    except Exception as e:
        LOGGER.error(f"Error refreshing market making orders for {pool_address}: {e}")

def trend_following_loop():
    """Loop to execute trend following strategy."""
    LOGGER.info("trend_following_loop started (dummy)")
    send_telegram_message("📈 Trend Following bot is now active and analyzing token trends!")
    
    # Initial delay to stagger strategy execution
    time.sleep(60)
    
    while running:
        try:
            # Update stop losses for existing positions
            update_stops_thread = threading.Thread(
                target=update_trend_stops,
                daemon=True
            )
            update_stops_thread.start()
            threads.append(update_stops_thread)
            
            # Check for new trend opportunities if we have capacity
            if len(active_trades["trend_following"]) < STRATEGY_CONFIG["trend_following"]["max_concurrent_positions"]:
                for token_mint in STRATEGY_CONFIG["trend_following"]["tokens_to_monitor"]:
                    if token_mint in active_trades["trend_following"]:
                        continue
                        
                    # Analyze trend for each timeframe
                    for timeframe in STRATEGY_CONFIG["trend_following"]["timeframes"]:
                        LOGGER.info(f"📊 Analyzing trend for {token_mint} on {timeframe} timeframe")
                        
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        trend_data = loop.run_until_complete(analyze_token_trend(token_mint, timeframe))
                        
                        if trend_data.get("trend") == "bullish":
                            LOGGER.info(f"📈 Bullish trend detected for {token_mint} on {timeframe}")
                            send_telegram_message(f"📈 Bullish trend detected for {token_mint} - Entering position")
                            
                            # Add to active trades
                            active_trades["trend_following"].add(token_mint)
                            
                            # Execute trend following trade
                            trend_thread = threading.Thread(
                                target=execute_trend_trade,
                                args=(trend_data,),
                                daemon=True
                            )
                            trend_thread.start()
                            threads.append(trend_thread)
                            
                            # Break to avoid analyzing other timeframes for this token
                            break
        
        except Exception as e:
            LOGGER.error(f"Error in trend following loop: {e}")
            
        time.sleep(STRATEGY_CONFIG["trend_following"]["check_interval_seconds"])

def execute_trend_trade(trend_data):
    """Execute a trend following trade."""
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
                
                # Remove from active trades on sell
                if token_mint in active_trades["trend_following"]:
                    active_trades["trend_following"].remove(token_mint)
        else:
            # If trade failed, remove from active trades
            if token_mint in active_trades["trend_following"]:
                active_trades["trend_following"].remove(token_mint)
    
    except Exception as e:
        LOGGER.error(f"Error executing trend trade for {token_mint}: {e}")
        
        # Remove from active trades if error
        if token_mint in active_trades["trend_following"]:
            active_trades["trend_following"].remove(token_mint)

def update_trend_stops():
    """Update stop losses for trend following positions."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        loop.run_until_complete(update_trend_following_stops())
    except Exception as e:
        LOGGER.error(f"Error updating trend following stops: {e}")

def start_all_strategies():
    """Start all enabled trading strategies."""
    global threads
    
    # Start sniper strategy
    if STRATEGY_CONFIG["sniper"]["enabled"]:
        sniper_thread = threading.Thread(target=sniper_loop, daemon=True)
        sniper_thread.start()
        threads.append(sniper_thread)
        LOGGER.info("🚀 Started Sniper strategy")
    
    # Start arbitrage strategy
    if STRATEGY_CONFIG["arbitrage"]["enabled"]:
        arbitrage_thread = threading.Thread(target=arbitrage_loop, daemon=True)
        arbitrage_thread.start()
        threads.append(arbitrage_thread)
        LOGGER.info("💱 Started Cross-DEX Arbitrage strategy")
    
    # Start market making strategy
    if STRATEGY_CONFIG["market_making"]["enabled"]:
        market_making_thread = threading.Thread(target=market_making_loop, daemon=True)
        market_making_thread.start()
        threads.append(market_making_thread)
        LOGGER.info("📊 Started Market Making strategy")
    
    # Start trend following strategy
    if STRATEGY_CONFIG["trend_following"]["enabled"]:
        trend_following_thread = threading.Thread(target=trend_following_loop, daemon=True)
        trend_following_thread.start()
        threads.append(trend_following_thread)
        LOGGER.info("📈 Started Trend Following strategy")
    
    return threads

def stop_all_strategies():
    """Stop all running strategies."""
    global running
    running = False
    
    LOGGER.info("🛑 Stopping all strategies...")
    send_telegram_message("🛑 Stopping all trading strategies. Please wait...")
    
    # Wait for all threads to finish
    for thread in threads:
        if thread.is_alive():
            thread.join(timeout=5)
    
    LOGGER.info("✅ All strategies stopped")
    send_telegram_message("✅ All trading strategies have been stopped")

def start_sniper_thread():
    """Start only the sniper strategy (for backward compatibility)."""
    if STRATEGY_CONFIG["sniper"]["enabled"]:
        thread = threading.Thread(target=sniper_loop, daemon=True)
        thread.start()
        threads.append(thread)
        return thread
    return None

if __name__ == "__main__":
    # Start all strategies
    send_telegram_message("🚀 Snipe4SoleBot starting all trading strategies...")
    
    strategy_threads = start_all_strategies()
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_all_strategies()
