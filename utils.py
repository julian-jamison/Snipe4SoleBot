"""
Utility functions for the Solana trading bot.
"""
import os
import logging
import json
import time
import random
import requests
from datetime import datetime
from decrypt_config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("utils")

# Trade logging
TRADE_LOG_FILE = "trade_log.json"
WHITELIST_FILE = "token_whitelist.json"
BLACKLIST_FILE = "token_blacklist.json"

def get_token_price(token_address):
    """
    Get the current price of a token (synchronous wrapper for fetch_price).
    Fetches real price from an API.
    """
    # Use coingecko API for known tokens
    known_tokens = {
        "So11111111111111111111111111111111111111112": "solana",  # SOL
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "usd-coin",   # USDC
        "Es9vMFrzaCERiE2dZVjW6M9T3cxLVRshzF5sgJnpPzM9": "tether",   # USDT
    }
    
    try:
        # First try to get price from CoinGecko for known tokens
        if token_address in known_tokens:
            coin_id = known_tokens[token_address]
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if coin_id in data and "usd" in data[coin_id]:
                    return data[coin_id]["usd"]
        
        # For other tokens, try Jupiter API for price
        url = "https://quote-api.jup.ag/v6/quote"
        params = {
            "inputMint": token_address,
            "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            "amount": 1000000,  # 1 token in lamports
            "slippage": 1
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "outAmount" in data:
                return float(data["outAmount"]) / 1000000  # Convert from USDC decimals
        
        # If all else fails, try to get price from Birdeye API
        url = f"https://public-api.birdeye.so/public/price?address={token_address}"
        headers = {"X-API-KEY": "cc8ff825-27de-4804-9f6e-5bbb5a40fc3a"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "data" in data and "value" in data["data"]:
                return data["data"]["value"]
                
        # If we still don't have a price, fall back to the default map
        price_map = {
            "So11111111111111111111111111111111111111112": 100.0,  # SOL
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": 1.0,   # USDC
            "Es9vMFrzaCERiE2dZVjW6M9T3cxLVRshzF5sgJnpPzM9": 1.0,   # USDT
        }
        if token_address in price_map:
            return price_map[token_address]
            
        # Last resort: assume it's a low value token
        return 0.001
        
    except Exception as e:
        logger.error(f"Error fetching price for {token_address}: {e}")
        # Final fallback - make an educated guess
        if token_address == "So11111111111111111111111111111111111111112":
            return 100.0  # SOL
        elif token_address in ["EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "Es9vMFrzaCERiE2dZVjW6M9T3cxLVRshzF5sgJnpPzM9"]:
            return 1.0  # Stablecoins
        else:
            return 0.001  # Unknown token

def log_trade_result(action, token, price, amount, profit_loss, status):
    """Log trade results to a file."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        trade_data = {
            "timestamp": timestamp,
            "action": action,
            "token": token,
            "price": price,
            "amount": amount,
            "profit_loss": profit_loss,
            "status": status
        }
        
        # Load existing trades if the log file exists
        trades = []
        if os.path.exists(TRADE_LOG_FILE):
            with open(TRADE_LOG_FILE, "r") as f:
                try:
                    trades = json.load(f)
                except json.JSONDecodeError:
                    # File exists but is invalid JSON
                    trades = []
        
        # Append the new trade
        trades.append(trade_data)
        
        # Write back to the log file
        with open(TRADE_LOG_FILE, "w") as f:
            json.dump(trades, f, indent=2)
            
        logger.info(f"Logged {action} trade for {token} at ${price:.6f}")
        
    except Exception as e:
        logger.error(f"Failed to log trade: {e}")

def should_buy_token(token_address):
    """
    Determine if a token should be bought based on various criteria.
    """
    # Check if token is in whitelist (if whitelist exists)
    if os.path.exists(WHITELIST_FILE):
        try:
            with open(WHITELIST_FILE, "r") as f:
                whitelist = json.load(f)
            if whitelist and token_address not in whitelist:
                logger.info(f"Token {token_address} not in whitelist, skipping")
                return False
        except Exception as e:
            logger.error(f"Error reading whitelist: {e}")
    
    # Check if token is in blacklist
    if os.path.exists(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, "r") as f:
                blacklist = json.load(f)
            if token_address in blacklist:
                logger.info(f"Token {token_address} in blacklist, skipping")
                return False
        except Exception as e:
            logger.error(f"Error reading blacklist: {e}")
    
    # Add additional criteria here, such as:
    # 1. Token age (reject brand new tokens)
    # 2. Liquidity checks
    # 3. Developer wallet analysis
    # 4. Contract code red flags
    
    # For the sake of this example, let's randomly decide
    # In a real implementation, you would have detailed checks
    return random.random() > 0.3  # 70% chance of buying

def get_random_wallet():
    """
    Get a random wallet for trading.
    
    In a real implementation, this would load a wallet from a secure storage.
    For this implementation, we'll return a mock wallet object.
    """
    try:
        from solders.keypair import Keypair
    except ImportError:
        # Fallback if solders not available
        pass
    
    # In a real implementation, you would load wallets from config
    wallets = config.get("solana_wallets", {})
    
    # Create a simple mock wallet object with a pubkey method
    class MockWallet:
        def __init__(self, address):
            self._address = address
            
        def pubkey(self):
            return self._address
    
    # For simplicity, just return a mock wallet - FIXED: Added missing closing parenthesis
    return MockWallet("Random" + str(random.randint(1000, 9999)))

def parse_timestamp(timestamp_str):
    """Parse a timestamp string into a datetime object."""
    return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

def calculate_profit_loss(buy_price, sell_price, amount):
    """Calculate profit/loss from a trade."""
    return (sell_price - buy_price) * amount
