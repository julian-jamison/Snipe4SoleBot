import os
import json
import logging

# Initialize logger
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# Constants
PORTFOLIO_FILE = "portfolio.json"

def _load_portfolio():
    """Load the portfolio from file."""
    if not os.path.exists(PORTFOLIO_FILE):
        return {}
        
    try:
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        LOGGER.error(f"Error loading portfolio: {e}")
        return {}

def _save_portfolio(portfolio):
    """Save the portfolio to file."""
    try:
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump(portfolio, f, indent=2)
    except Exception as e:
        LOGGER.error(f"Error saving portfolio: {e}")

def add_position(token_address, quantity, price, strategy="dex"):
    """
    Add a position to the portfolio.
    
    Args:
        token_address: The address of the token
        quantity: The quantity of tokens
        price: The price per token
        strategy: The strategy used (default: 'dex')
    """
    try:
        portfolio = _load_portfolio()
        
        if token_address not in portfolio:
            portfolio[token_address] = {
                "quantity": 0,
                "price": 0,
                "strategy": strategy
            }
            
        # Calculate new average price
        old_quantity = portfolio[token_address]["quantity"]
        old_price = portfolio[token_address]["price"]
        new_quantity = old_quantity + quantity
        
        if new_quantity > 0:
            new_price = (old_quantity * old_price) + (quantity * price) / new_quantity
        else:
            new_price = price
            
        # Update portfolio
        portfolio[token_address]["quantity"] = new_quantity
        portfolio[token_address]["price"] = new_price
        portfolio[token_address]["strategy"] = strategy
        
        _save_portfolio(portfolio)
        
        LOGGER.info(f"Added position: {quantity} {token_address} at ${price}")
        
    except Exception as e:
        LOGGER.error(f"Error adding position: {e}")

def remove_position(token_address, quantity=None):
    """
    Remove a position from the portfolio.
    
    Args:
        token_address: The address of the token
        quantity: The quantity to remove (default: all)
    """
    try:
        portfolio = _load_portfolio()
        
        if token_address not in portfolio:
            LOGGER.warning(f"Position not found: {token_address}")
            return
            
        if quantity is None or quantity >= portfolio[token_address]["quantity"]:
            # Remove entire position
            del portfolio[token_address]
            LOGGER.info(f"Removed position: {token_address}")
        else:
            # Remove partial position
            portfolio[token_address]["quantity"] -= quantity
            LOGGER.info(f"Removed {quantity} from position: {token_address}")
            
        _save_portfolio(portfolio)
        
    except Exception as e:
        LOGGER.error(f"Error removing position: {e}")

def get_position(token_address):
    """
    Get a position from the portfolio.
    
    Args:
        token_address: The address of the token
        
    Returns:
        dict: The position data or None if not found
    """
    try:
        portfolio = _load_portfolio()
        return portfolio.get(token_address)
    except Exception as e:
        LOGGER.error(f"Error getting position: {e}")
        return None

def get_all_positions():
    """
    Get all positions in the portfolio.
    
    Returns:
        dict: All positions
    """
    return _load_portfolio()
