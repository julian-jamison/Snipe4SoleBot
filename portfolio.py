"""
Portfolio management module for the Solana trading bot.
"""
import os
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("portfolio")

# File to store portfolio data
PORTFOLIO_FILE = "portfolio.json"

def get_all_positions():
    """
    Get all current positions.
    
    Returns:
        list: List of token addresses with open positions
    """
    portfolio = load_portfolio()
    positions = []
    
    for wallet, tokens in portfolio.items():
        positions.extend(tokens.keys())
    
    return positions

def get_position(token_address):
    """
    Get position information for a specific token.
    
    Args:
        token_address: The address of the token
        
    Returns:
        dict: Position information or None if no position exists
    """
    portfolio = load_portfolio()
    
    for wallet, tokens in portfolio.items():
        if token_address in tokens:
            return tokens[token_address]
    
    return None

def add_position(token_address, quantity, price, source="dex", wallet="default"):
    """
    Add a new position to the portfolio.
    
    Args:
        token_address: The address of the token
        quantity: The quantity purchased
        price: The purchase price
        source: The source of the trade (e.g., "dex", "jupiter", etc.)
        wallet: The wallet used for the trade
    """
    portfolio = load_portfolio()
    
    # Ensure wallet exists in portfolio
    if wallet not in portfolio:
        portfolio[wallet] = {}
    
    # Add or update the position
    if token_address in portfolio[wallet]:
        # Update existing position with average price
        existing = portfolio[wallet][token_address]
        existing_quantity = existing["quantity"]
        existing_price = existing["price"]
        
        # Calculate new average price
        total_quantity = existing_quantity + quantity
        if total_quantity > 0:
            new_avg_price = (existing_quantity * existing_price + quantity * price) / total_quantity
        else:
            new_avg_price = price
        
        portfolio[wallet][token_address] = {
            "quantity": total_quantity,
            "price": new_avg_price,
            "source": source,
            "last_updated": datetime.now().isoformat()
        }
    else:
        # Add new position
        portfolio[wallet][token_address] = {
            "quantity": quantity,
            "price": price,
            "source": source,
            "entry_time": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
    
    save_portfolio(portfolio)
    logger.info(f"Added position: {quantity} of {token_address} at ${price:.6f}")

def remove_position(token_address, wallet=None):
    """
    Remove a position from the portfolio.
    
    Args:
        token_address: The address of the token
        wallet: The specific wallet to remove from (or all if None)
    """
    portfolio = load_portfolio()
    position_removed = False
    
    if wallet is not None and wallet in portfolio:
        # Remove from specific wallet
        if token_address in portfolio[wallet]:
            del portfolio[wallet][token_address]
            position_removed = True
            # Remove wallet if empty
            if not portfolio[wallet]:
                del portfolio[wallet]
    else:
        # Remove from all wallets
        for w in list(portfolio.keys()):
            if token_address in portfolio[w]:
                del portfolio[w][token_address]
                position_removed = True
                # Remove wallet if empty
                if not portfolio[w]:
                    del portfolio[w]
    
    if position_removed:
        save_portfolio(portfolio)
        logger.info(f"Removed position for {token_address}")
    else:
        logger.warning(f"No position found for {token_address}")

def update_position(token_address, quantity=None, price=None, wallet=None):
    """
    Update an existing position in the portfolio.
    
    Args:
        token_address: The address of the token
        quantity: The new quantity (or None to keep current)
        price: The new price (or None to keep current)
        wallet: The specific wallet to update (or first found if None)
    """
    portfolio = load_portfolio()
    position_updated = False
    
    if wallet is not None and wallet in portfolio and token_address in portfolio[wallet]:
        # Update in specific wallet
        position = portfolio[wallet][token_address]
        if quantity is not None:
            position["quantity"] = quantity
        if price is not None:
            position["price"] = price
        position["last_updated"] = datetime.now().isoformat()
        position_updated = True
    else:
        # Update in first wallet found
        for w in portfolio:
            if token_address in portfolio[w]:
                position = portfolio[w][token_address]
                if quantity is not None:
                    position["quantity"] = quantity
                if price is not None:
                    position["price"] = price
                position["last_updated"] = datetime.now().isoformat()
                position_updated = True
                break
    
    if position_updated:
        save_portfolio(portfolio)
        logger.info(f"Updated position for {token_address}")
    else:
        logger.warning(f"No position found to update for {token_address}")

def load_portfolio():
    """
    Load the portfolio from file.
    
    Returns:
        dict: The portfolio data
    """
    if not os.path.exists(PORTFOLIO_FILE):
        return {}
    
    try:
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in {PORTFOLIO_FILE}")
        return {}
    except Exception as e:
        logger.error(f"Error loading portfolio: {e}")
        return {}

def save_portfolio(portfolio):
    """
    Save the portfolio to file.
    
    Args:
        portfolio: The portfolio data to save
    """
    try:
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump(portfolio, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving portfolio: {e}")

def get_portfolio_value():
    """
    Calculate the total value of the portfolio.
    
    Returns:
        float: The total value in USD
    """
    portfolio = load_portfolio()
    total_value = 0.0
    
    for wallet, tokens in portfolio.items():
        for token_address, position in tokens.items():
            quantity = position["quantity"]
            price = position["price"]
            value = quantity * price
            total_value += value
    
    return total_value

def get_positions_summary():
    """
    Get a summary of all positions.
    
    Returns:
        list: A list of position summaries
    """
    portfolio = load_portfolio()
    summaries = []
    
    for wallet, tokens in portfolio.items():
        for token_address, position in tokens.items():
            quantity = position["quantity"]
            price = position["price"]
            value = quantity * price
            entry_time = position.get("entry_time", "Unknown")
            
            summary = {
                "token": token_address,
                "wallet": wallet,
                "quantity": quantity,
                "price": price,
                "value": value,
                "entry_time": entry_time
            }
            
            summaries.append(summary)
    
    return summaries

# For testing
if __name__ == "__main__":
    # Example usage
    print("Current positions:", get_all_positions())
    print("Portfolio value:", get_portfolio_value())
