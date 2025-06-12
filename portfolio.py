"""
Portfolio management module for the Solana trading bot.
This module handles tracking of token positions, profit/loss, and portfolio analytics.
"""
import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("portfolio")

# Portfolio file
PORTFOLIO_FILE = "portfolio.json"

def load_portfolio():
    """Load portfolio from file."""
    try:
        if os.path.exists(PORTFOLIO_FILE):
            with open(PORTFOLIO_FILE, "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading portfolio: {e}")
        return {}

def save_portfolio(portfolio):
    """Save portfolio to file."""
    try:
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump(portfolio, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving portfolio: {e}")

def get_all_positions():
    """Get all token positions across all wallets."""
    portfolio = load_portfolio()
    positions = []
    for wallet, tokens in portfolio.items():
        for token_address in tokens.keys():
            positions.append(token_address)
    return positions

def get_position(token_address, wallet=None):
    """
    Get position details for a specific token.
    
    Args:
        token_address (str): Token address
        wallet (str, optional): Specific wallet to check
        
    Returns:
        dict: Position details or None if not found
    """
    portfolio = load_portfolio()
    
    if wallet:
        # Check specific wallet
        wallet_positions = portfolio.get(wallet, {})
        return wallet_positions.get(token_address)
    else:
        # Check all wallets
        for wallet_name, tokens in portfolio.items():
            if token_address in tokens:
                return tokens[token_address]
        return None

def add_position(token_address, quantity, price, dex, wallet="default"):
    """
    Add or update a position.
    
    Args:
        token_address (str): Token address
        quantity (float): Quantity of tokens
        price (float): Entry price
        dex (str): DEX used for the trade
        wallet (str): Wallet identifier
    """
    portfolio = load_portfolio()
    
    # Initialize wallet if it doesn't exist
    if wallet not in portfolio:
        portfolio[wallet] = {}
    
    # Check if position already exists
    if token_address in portfolio[wallet]:
        # Update existing position (average price)
        existing = portfolio[wallet][token_address]
        existing_quantity = existing.get("quantity", 0)
        existing_price = existing.get("price", 0)
        
        # Calculate new average price
        total_value = (existing_quantity * existing_price) + (quantity * price)
        total_quantity = existing_quantity + quantity
        new_avg_price = total_value / total_quantity if total_quantity > 0 else 0
        
        portfolio[wallet][token_address] = {
            "quantity": total_quantity,
            "price": new_avg_price,
            "dex": dex,
            "last_updated": datetime.now().isoformat(),
            "trades": existing.get("trades", 0) + 1
        }
    else:
        # Add new position
        portfolio[wallet][token_address] = {
            "quantity": quantity,
            "price": price,
            "dex": dex,
            "entry_time": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "trades": 1
        }
    
    save_portfolio(portfolio)
    logger.info(f"Added position: {quantity} {token_address} at ${price:.6f}")

def remove_position(token_address, wallet=None):
    """
    Remove a position completely.
    
    Args:
        token_address (str): Token address
        wallet (str, optional): Specific wallet, if None removes from all wallets
    """
    portfolio = load_portfolio()
    removed = False
    
    if wallet:
        # Remove from specific wallet
        if wallet in portfolio and token_address in portfolio[wallet]:
            del portfolio[wallet][token_address]
            removed = True
    else:
        # Remove from all wallets
        for wallet_name in portfolio:
            if token_address in portfolio[wallet_name]:
                del portfolio[wallet_name][token_address]
                removed = True
    
    if removed:
        save_portfolio(portfolio)
        logger.info(f"Removed position: {token_address}")
    
    return removed

def update_position_quantity(token_address, new_quantity, wallet="default"):
    """
    Update the quantity of an existing position.
    
    Args:
        token_address (str): Token address
        new_quantity (float): New quantity
        wallet (str): Wallet identifier
    """
    portfolio = load_portfolio()
    
    if wallet in portfolio and token_address in portfolio[wallet]:
        if new_quantity <= 0:
            # Remove position if quantity is 0 or negative
            remove_position(token_address, wallet)
        else:
            portfolio[wallet][token_address]["quantity"] = new_quantity
            portfolio[wallet][token_address]["last_updated"] = datetime.now().isoformat()
            save_portfolio(portfolio)
            logger.info(f"Updated position quantity: {token_address} = {new_quantity}")
    else:
        logger.warning(f"Position not found: {token_address} in wallet {wallet}")

def get_portfolio_summary():
    """
    Get a summary of the entire portfolio.
    
    Returns:
        dict: Portfolio summary with total value, positions count, etc.
    """
    portfolio = load_portfolio()
    summary = {
        "total_positions": 0,
        "wallets": len(portfolio),
        "tokens": set(),
        "positions_by_wallet": {}
    }
    
    for wallet, tokens in portfolio.items():
        wallet_positions = len(tokens)
        summary["total_positions"] += wallet_positions
        summary["positions_by_wallet"][wallet] = wallet_positions
        
        for token_address in tokens.keys():
            summary["tokens"].add(token_address)
    
    summary["unique_tokens"] = len(summary["tokens"])
    summary["tokens"] = list(summary["tokens"])  # Convert set to list for JSON serialization
    
    return summary

def get_wallet_positions(wallet="default"):
    """
    Get all positions for a specific wallet.
    
    Args:
        wallet (str): Wallet identifier
        
    Returns:
        dict: All positions for the wallet
    """
    portfolio = load_portfolio()
    return portfolio.get(wallet, {})

def calculate_position_pnl(token_address, current_price, wallet=None):
    """
    Calculate profit/loss for a position.
    
    Args:
        token_address (str): Token address
        current_price (float): Current token price
        wallet (str, optional): Specific wallet
        
    Returns:
        dict: PnL details
    """
    position = get_position(token_address, wallet)
    if not position:
        return None
    
    entry_price = position.get("price", 0)
    quantity = position.get("quantity", 0)
    
    if entry_price == 0 or quantity == 0:
        return None
    
    current_value = current_price * quantity
    entry_value = entry_price * quantity
    pnl = current_value - entry_value
    pnl_percentage = (pnl / entry_value) * 100 if entry_value > 0 else 0
    
    return {
        "token_address": token_address,
        "entry_price": entry_price,
        "current_price": current_price,
        "quantity": quantity,
        "entry_value": entry_value,
        "current_value": current_value,
        "pnl": pnl,
        "pnl_percentage": pnl_percentage
    }

# For testing
if __name__ == "__main__":
    print("Portfolio module loaded successfully!")
    
    # Test basic functionality
    summary = get_portfolio_summary()
    print(f"Portfolio summary: {summary}")
