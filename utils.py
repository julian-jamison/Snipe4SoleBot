import json
import os
import logging
import random
import time
import aiohttp
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from config_manager import load_decrypted_config

LOG_FILE = "trade_log.json"
CONFIG_FILE = "config.json"
BACKUP_LOG_FILE = "trade_log_backup.json"

# Configure logging
logger = logging.getLogger("Snipe4SoleBot")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler("bot_debug.log")
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Async function to fetch the price
async def fetch_price_async(token_address):
    """Fetches the latest price of a token from CoinGecko and other DEX APIs as a backup."""
    urls = [
        f"https://api.coingecko.com/api/v3/simple/token_price/solana?contract_addresses={token_address}&vs_currencies=usd",
        f"https://quote-api.jup.ag/v4/quote?inputMint={token_address}&outputMint=So11111111111111111111111111111111111111112"
    ]

    async with aiohttp.ClientSession() as session:
        for url in urls:
            try:
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()

                    if "usd" in data.get(token_address, {}):
                        return data[token_address]["usd"]
                    if "data" in data:
                        quotes = data.get("data", [])
                        if quotes and isinstance(quotes, list):
                            return quotes[0].get("outAmount", 0)

            except aiohttp.ClientError as e:
                logger.warning(f"⚠️ Error fetching price from {url}: {e}")
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Error decoding JSON response from {url}: {e}")

    return None

# Synchronous wrapper for fetch_price (for backward compatibility)
def fetch_price(token_address):
    """Synchronous wrapper for fetch_price_async."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(fetch_price_async(token_address))

def log_trade_result(action, token, price, quantity, profit_loss, status):
    """Logs trade results to a JSON file."""
    trade_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "token": token,
        "price": price,
        "quantity": quantity,
        "profit_loss": profit_loss,
        "status": status
    }

    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                trade_logs = json.load(f)
        else:
            trade_logs = []

        trade_logs.append(trade_entry)

        with open(LOG_FILE, "w") as f:
            json.dump(trade_logs, f, indent=4)

        logger.info(f"📝 Trade logged: {trade_entry}")

    except Exception as e:
        logger.error(f"❌ Failed to log trade: {e}")

def load_config():
    """Loads bot configuration settings."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    else:
        logger.warning("⚠️ Configuration file not found!")
        return {}

def backup_trade_log():
    """Backs up the trade log in case of unexpected crashes."""
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                trade_logs = json.load(f)

            with open(BACKUP_LOG_FILE, "w") as f:
                json.dump(trade_logs, f, indent=4)

            logger.info("✅ Trade log backup completed.")
    except Exception as e:
        logger.error(f"❌ Failed to back up trade log: {e}")

def restore_trade_log():
    """Restores the trade log from backup if needed."""
    try:
        if os.path.exists(BACKUP_LOG_FILE):
            with open(BACKUP_LOG_FILE, "r") as f:
                trade_logs = json.load(f)

            with open(LOG_FILE, "w") as f:
                json.dump(trade_logs, f, indent=4)

            logger.info("✅ Trade log restored from backup.")
    except Exception as e:
        logger.error(f"❌ Failed to restore trade log: {e}")

# New functions needed by monitor_and_trade.py

# Token price cache to avoid excessive API calls
price_cache = {}
CACHE_DURATION = 60  # seconds

async def get_token_price_async(token_address: str, vs_currency: str = "usd") -> Optional[float]:
    """Get token price from Jupiter Price API asynchronously."""
    try:
        # Check cache first
        cache_key = f"{token_address}_{vs_currency}"
        if cache_key in price_cache:
            cached_price, timestamp = price_cache[cache_key]
            if time.time() - timestamp < CACHE_DURATION:
                return cached_price
        
        # Use the existing fetch_price function
        price = await fetch_price_async(token_address)
        if price:
            # Cache the price
            price_cache[cache_key] = (price, time.time())
            return price
                        
    except Exception as e:
        logger.error(f"Error fetching price for {token_address}: {e}")
    
    return None

def get_token_price(token_address: str, vs_currency: str = "usd") -> Optional[float]:
    """Get token price synchronously."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(get_token_price_async(token_address, vs_currency))

def should_buy_token(token_address: str, pool_info: Dict[str, Any]) -> bool:
    """Determine if a token should be bought based on various criteria."""
    config = load_decrypted_config()
    trade_settings = config.get('trade_settings', {})
    
    # Check if token is in allowed list (if specified)
    allowed_tokens = trade_settings.get('allowed_tokens', [])
    if allowed_tokens and token_address not in allowed_tokens:
        logger.info(f"Token {token_address} not in allowed list")
        return False
    
    # Check minimum liquidity
    min_liquidity = trade_settings.get('min_liquidity', 1000)
    liquidity = pool_info.get('liquidity', 0)
    
    if liquidity < min_liquidity:
        logger.info(f"Token {token_address} liquidity {liquidity} below minimum {min_liquidity}")
        return False
    
    # Additional checks can be added here:
    # - Token age
    # - Developer holdings
    # - Contract verification
    # - Social signals
    
    return True

def get_random_wallet(wallet_addresses: Dict[str, str]) -> str:
    """Get a random wallet address from the configured wallets."""
    # Exclude special wallets like 'cold_wallet' and key-related entries
    trading_wallets = {k: v for k, v in wallet_addresses.items() 
                      if k.startswith('wallet_') and not k.endswith('_key')}
    
    if not trading_wallets:
        raise ValueError("No trading wallets configured")
    
    return random.choice(list(trading_wallets.values()))

def calculate_slippage(current_price: float, expected_price: float) -> float:
    """Calculate slippage percentage between current and expected price."""
    if expected_price == 0:
        return 0
    
    slippage = ((current_price - expected_price) / expected_price) * 100
    return abs(slippage)

def is_honeypot(token_address: str) -> bool:
    """Check if a token might be a honeypot."""
    # This is a placeholder - you'd want to implement proper honeypot detection
    # by checking:
    # - If the token can be sold
    # - High buy/sell tax
    # - Disabled transfers
    # - Contract permissions
    
    HONEYPOT_ADDRESSES = {
        # Add known honeypot addresses here
    }
    
    return token_address in HONEYPOT_ADDRESSES

def format_sol_amount(lamports: int) -> str:
    """Format lamports to SOL with proper decimal places."""
    sol = lamports / 1e9
    return f"{sol:.6f} SOL"

def get_dex_fee(dex_program: str) -> float:
    """Get the fee percentage for a specific DEX."""
    dex_fees = {
        "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": 0.25,  # Raydium
        "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": 0.3,   # Orca
        "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBymtzvT": 0.3,   # Meteora
    }
    
    return dex_fees.get(dex_program, 0.3)  # Default 0.3%

async def validate_pool_info(pool_info: Dict[str, Any]) -> bool:
    """Validate pool information before trading."""
    required_fields = ['pool_address', 'token_a', 'token_b']
    
    for field in required_fields:
        if field not in pool_info:
            logger.error(f"Missing required field: {field}")
            return False
    
    # Additional validation
    if pool_info.get('liquidity', 0) <= 0:
        logger.error("Invalid liquidity amount")
        return False
    
    return True

def estimate_gas_fee() -> float:
    """Estimate gas fee for a transaction."""
    config = load_decrypted_config()
    max_gas = config.get('trade_settings', {}).get('max_gas_fee', 0.002)
    
    # Typical Solana transaction fee
    base_fee = 0.000005  # 5000 lamports
    
    # Add some buffer for compute units
    estimated_fee = base_fee * 2
    
    return min(estimated_fee, max_gas)
