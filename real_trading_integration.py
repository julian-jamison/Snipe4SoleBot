import time
import asyncio
import threading
import requests
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import the real trader module
from solana_real_trader import get_real_trader

# Import from existing modules
from telegram_notifications import send_telegram_message_async
from decrypt_config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("real_trading_integration")

# Track processed pools to avoid duplicates
processed_pools = set()

# Global flag for real trading mode
REAL_TRADING_ENABLED = config.get("api_keys", {}).get("live_mode", False)

def is_real_trading_enabled():
    """Check if real trading is enabled in config"""
    return REAL_TRADING_ENABLED

def get_new_liquidity_pools_real():
    """
    Get new liquidity pools using real API calls
    
    Returns:
        list: New liquidity pools data
    """
    if not is_real_trading_enabled():
        logger.info("Real trading mode is disabled. Skipping real API calls.")
        return []
        
    # Get real trader instance
    trader = get_real_trader()
    
    # Get new pools
    return trader.monitor_new_liquidity_pools()

def buy_token_multi_wallet(token_address, wallets, dex="jupiter"):
    """
    Buy token using multiple wallets - real implementation
    
    Args:
        token_address (str): Token address to buy
        wallets (list): List of wallet objects
        dex (str): DEX to use
        
    Returns:
        dict: Transaction result
    """
    if not is_real_trading_enabled():
        logger.info(f"Mock buying {token_address} (real trading disabled)")
        # Return mock success
        return {
            "token_address": token_address,
            "successful_buys": 1,
            "total_tokens_bought": 1000,
            "total_eth_spent": 0.1,
            "wallet_results": [{"wallet": "MockWallet", "success": True}]
        }
        
    # Log real buy attempt
    logger.info(f"Executing REAL buy for {token_address}")
   await send_telegram_message_async(f"🔴 REAL TRADING: Buying {token_address}")
    
    # Get real trader instance
    trader = get_real_trader()
    
    # Convert wallet list to format expected by real trader
    wallet_addresses = []
    for wallet in wallets:
        if isinstance(wallet, str):
            wallet_addresses.append(wallet)
        elif hasattr(wallet, 'pubkey'):
            wallet_addresses.append(wallet.pubkey()
        elif isinstance(wallet, dict) and 'wallet' in wallet:
            wallet_addresses.append(wallet['wallet'])
            
    # Execute real buy
    result = trader.buy_token_multi_wallet(token_address, wallet_addresses)
    
    if result and result.get("successful_buys", 0) > 0:
        token_info = trader.get_token_metadata(token_address)
        token_symbol = token_info.get("symbol", "Unknown")
        
        # Send notification
       await send_telegram_message_async(
            f"✅ REAL BUY EXECUTED:\n"
            f"Token: {token_symbol}\n"
            f"Token Address: {token_address}\n"
            f"Amount: {result.get('total_tokens_bought', 0):.6f} tokens\n"
            f"Spent: {result.get('total_sol_spent', 0):.4f} SOL"
        )
        
    return result

def sell_token_multi_wallet(token_address, wallets, dex="jupiter"):
    """
    Sell token using multiple wallets - real implementation
    
    Args:
        token_address (str): Token address to sell
        wallets (list): List of wallet objects
        dex (str): DEX to use
        
    Returns:
        dict: Transaction result
    """
    if not is_real_trading_enabled():
        logger.info(f"Mock selling {token_address} (real trading disabled)")
        # Return mock success
        return {
            "token_address": token_address,
            "successful_sells": 1,
            "total_tokens_sold": 1000,
            "wallet_results": [{"wallet": "MockWallet", "success": True}]
        }
        
    # Log real sell attempt
    logger.info(f"Executing REAL sell for {token_address}")
   await send_telegram_message_async(f"🔴 REAL TRADING: Selling {token_address}")
    
    # Get real trader instance
    trader = get_real_trader()
    
    # Convert wallet list to format expected by real trader
    wallet_addresses = []
    for wallet in wallets:
        if isinstance(wallet, str):
            wallet_addresses.append(wallet)
        elif hasattr(wallet, 'pubkey'):
            wallet_addresses.append(wallet.pubkey()
        elif isinstance(wallet, dict) and 'wallet' in wallet:
            wallet_addresses.append(wallet['wallet'])
            
    # Execute real sell
    result = trader.sell_token_multi_wallet(token_address, wallet_addresses)
    
    if result and result.get("successful_sells", 0) > 0:
        token_info = trader.get_token_metadata(token_address)
        token_symbol = token_info.get("symbol", "Unknown")
        
        # Send notification
       await send_telegram_message_async(
            f"✅ REAL SELL EXECUTED:\n"
            f"Token: {token_symbol}\n"
            f"Token Address: {token_address}\n"
            f"Amount: {result.get('total_tokens_sold', 0):.6f} tokens\n"
            f"Received: {result.get('total_sol_received', 0):.4f} SOL"
        )
        
    return result

def sell_token_auto_withdraw(token_address, wallets, dex="jupiter"):
    """
    Sell token and auto withdraw - real implementation
    
    Args:
        token_address (str): Token address to sell
        wallets (list): List of wallet objects
        dex (str): DEX to use
        
    Returns:
        dict: Transaction result
    """
    if not is_real_trading_enabled():
        logger.info(f"Mock selling {token_address} with auto withdraw (real trading disabled)")
        # Return mock success
        return {
            "token_address": token_address,
            "successful_sells": 1,
            "total_tokens_sold": 1000,
            "wallet_results": [{"wallet": "MockWallet", "success": True}]
        }
        
    # Log real sell attempt
    logger.info(f"Executing REAL sell with auto withdraw for {token_address}")
    
    # Get real trader instance
    trader = get_real_trader()
    
    # Get the cold wallet for withdrawal
    cold_wallet = config.get("solana_wallets", {}).get("cold_wallet")
    
    if not cold_wallet:
        logger.warning("No cold wallet configured for withdrawal, proceeding with regular sell")
        return sell_token_multi_wallet(token_address, wallets, dex)
        
    # Process each wallet
    results = []
    successful_sells = 0
    total_tokens_sold = 0
    total_sol_received = 0
    
    for wallet in wallets:
        if isinstance(wallet, str):
            wallet_address = wallet
        elif hasattr(wallet, 'pubkey'):
            wallet_address = wallet.pubkey()
        elif isinstance(wallet, dict) and 'wallet' in wallet:
            wallet_address = wallet['wallet']
        else:
            continue
            
        # Use default keypair for testing
        wallet_keypair = trader.keypair
        
        # Sell and withdraw
        result = trader.sell_token_auto_withdraw(token_address, wallet_keypair, cold_wallet)
        
        if result and result.get("success"):
            successful_sells += 1
            total_tokens_sold += result.get("token_amount", 0)
            total_sol_received += result.get("sol_received", 0)
            
            withdrawal_success = result.get("withdraw", {}).get("success", False)
            if withdrawal_success:
                result["withdrawal"] = {
                    "success": True,
                    "amount": result.get("withdraw", {}).get("amount", 0),
                    "destination": cold_wallet
                }
                
            results.append({
                "wallet": str(wallet_address),
                "success": True,
                "token_amount": result.get("token_amount", 0),
                "sol_received": result.get("sol_received", 0),
                "withdrawal": result.get("withdrawal", {"success": False})
            })
        else:
            results.append({
                "wallet": str(wallet_address),
                "success": False,
                "error": result.get("error") if result else "Failed to sell token"
            })
    
    # Send notification for successful transaction
    if successful_sells > 0:
        token_info = trader.get_token_metadata(token_address)
        token_symbol = token_info.get("symbol", "Unknown")
        
        # Send notification
       await send_telegram_message_async(
            f"✅ REAL SELL & WITHDRAW EXECUTED:\n"
            f"Token: {token_symbol}\n"
            f"Token Address: {token_address}\n"
            f"Amount: {total_tokens_sold:.6f} tokens\n"
            f"Received: {total_sol_received:.4f} SOL\n"
            f"Profits withdrawn to: {cold_wallet}"
        )
    
    # Return summary
    return {
        "token_address": token_address,
        "successful_sells": successful_sells,
        "total_tokens_sold": total_tokens_sold,
        "total_sol_received": total_sol_received,
        "wallet_results": results
    } if successful_sells > 0 else {"success": False, "error": "No successful sells"}

def get_wallet_balance(wallet_address, token_address=None):
    """
    Get wallet balance - real implementation
    
    Args:
        wallet_address (str): Wallet address
        token_address (str, optional): Token address
        
    Returns:
        float: Balance
    """
    if not is_real_trading_enabled():
        # Return mock balance for testing
        return 10.0 if token_address is None else 1000.0
        
    # Get real trader instance
    trader = get_real_trader()
    
    # Get real balance
    return trader.get_wallet_balance(wallet_address, token_address)

def fetch_token_price(token_address):
    """
    Fetch token price - real implementation
    
    Args:
        token_address (str): Token address
        
    Returns:
        float: Price in USD
    """
    if not is_real_trading_enabled():
        # Return mock price for testing
        return 0.01
        
    # Get real trader instance
    trader = get_real_trader()
    
    # Get real price
    return trader.get_token_price(token_address)

def should_buy_token(token_address, pool_info=None):
    """
    Determine if token should be bought
    
    Args:
        token_address (str): Token address
        pool_info (dict, optional): Pool information
        
    Returns:
        bool: True if should buy, False otherwise
    """
    # Get token price
    price = fetch_token_price(token_address)
    
    # Get minimum liquidity from config
    min_liquidity = config.get("trade_settings", {}).get("min_liquidity", 1000)
    
    # Check liquidity if pool_info is provided
    if pool_info:
        liquidity = float(pool_info.get("liquidity", 0)
        if liquidity < min_liquidity:
            logger.info(f"Skipping {token_address}: Liquidity (${liquidity}) below minimum (${min_liquidity})")
            return False
            
    # Check allowed tokens if configured
    allowed_tokens = config.get("trade_settings", {}).get("allowed_tokens", [])
    if allowed_tokens and token_address not in allowed_tokens:
        if token_address != "So11111111111111111111111111111111111111112":  # Always allow SOL
            logger.info(f"Skipping {token_address}: Not in allowed tokens list")
            return False
            
    # Additional checks can be added here
    
    # For now, return True if price is available
    return price > 0

def monitor_position(token_address, wallet, initial_price):
    """
    Monitor token position for profit/loss targets
    
    Args:
        token_address (str): Token address
        wallet: Wallet object or address
        initial_price (float): Initial buy price
    """
    # Extract profit target and stop loss from config
    trade_settings = config.get("trade_settings", {})
    profit_target = float(trade_settings.get("profit_target", 10)  # Default 10%
    stop_loss = float(trade_settings.get("stop_loss", -5)  # Default -5%
    check_interval = float(trade_settings.get("trade_cooldown", 5)  # Default 5 seconds
    
    # Get wallet address
    if isinstance(wallet, str):
        wallet_address = wallet
    elif hasattr(wallet, 'pubkey'):
        wallet_address = wallet.pubkey()
    elif isinstance(wallet, dict) and 'wallet' in wallet:
        wallet_address = wallet['wallet']
    else:
        wallet_address = "Unknown"
    
    # Get token info for better logging
    trader = get_real_trader()
    token_info = trader.get_token_metadata(token_address)
    token_symbol = token_info.get("symbol", "Unknown")
    
    logger.info(f"Starting to monitor {token_symbol} ({token_address}) position")
   await send_telegram_message_async(f"🔍 Monitoring {token_symbol} position for profit target ({profit_target}%) or stop loss ({stop_loss}%)")
    
    monitoring_active = True
    
    while monitoring_active:
        try:
            # Get current price
            current_price = fetch_token_price(token_address)
            
            if current_price <= 0:
                logger.warning(f"Could not fetch current price for {token_symbol}")
                time.sleep(check_interval)
                continue
                
            # Calculate profit percentage
            profit_percent = (current_price - initial_price) / initial_price) * 100
            
            logger.info(f"{token_symbol} current price: ${current_price:.8f}, profit: {profit_percent:.2f}%")
            
            # Check if profit target hit
            if profit_percent >= profit_target:
                logger.info(f"Profit target hit for {token_symbol}: {profit_percent:.2f}%")
                
                # Sell token
                if is_real_trading_enabled():
                   await send_telegram_message_async(f"🎯 Profit target hit for {token_symbol}! Selling at {profit_percent:.2f}% profit")
                    sell_result = sell_token_auto_withdraw(token_address, [wallet_address])
                    
                    if sell_result and (sell_result.get("successful_sells", 0) > 0 or sell_result.get("success", False):
                        logger.info(f"Successfully sold {token_symbol} at profit target")
                        monitoring_active = False
                    else:
                        logger.error(f"Failed to sell {token_symbol} at profit target")
                else:
                    # Simulate sell in mock mode
                    logger.info(f"Mock selling {token_symbol} at profit target")
                   await send_telegram_message_async(f"✅ Mock profit target hit: {token_symbol} would be sold at {profit_percent:.2f}% profit")
                    monitoring_active = False
            
            # Check if stop loss hit
            elif profit_percent <= stop_loss:
                logger.info(f"Stop loss hit for {token_symbol}: {profit_percent:.2f}%")
                
                # Sell token
                if is_real_trading_enabled():
                   await send_telegram_message_async(f"🛑 Stop loss triggered for {token_symbol}! Selling at {profit_percent:.2f}% loss")
                    sell_result = sell_token_auto_withdraw(token_address, [wallet_address])
                    
                    if sell_result and (sell_result.get("successful_sells", 0) > 0 or sell_result.get("success", False):
                        logger.info(f"Successfully sold {token_symbol} at stop loss")
                        monitoring_active = False
                    else:
                        logger.error(f"Failed to sell {token_symbol} at stop loss")
                else:
                    # Simulate sell in mock mode
                    logger.info(f"Mock selling {token_symbol} at stop loss")
                   await send_telegram_message_async(f"⛔ Mock stop loss hit: {token_symbol} would be sold at {profit_percent:.2f}% loss")
                    monitoring_active = False
            
        except Exception as e:
            logger.error(f"Error monitoring position for {token_symbol}: {e}")
            
        # Wait before next check
        time.sleep(check_interval)
        
    logger.info(f"Stopped monitoring {token_symbol} position")

def initialize_real_trading():
    """Initialize real trading functionality"""
    if is_real_trading_enabled():
        logger.info("Initializing REAL trading functionality")
        # Initialize the real trader
        trader = get_real_trader()
        
        # Send notification
       await send_telegram_message_async("🔴 REAL TRADING MODE ACTIVATED - Bot will execute actual trades on Solana!")
        
        # Return the trader instance
        return trader
    else:
        logger.info("Real trading is DISABLED. Running in simulation mode.")
       await send_telegram_message_async("🔵 Simulation mode active - No real trades will be executed")
        return None
