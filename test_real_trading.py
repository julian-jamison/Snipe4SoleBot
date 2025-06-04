#!/usr/bin/env python3
"""
Test script for real trading functionality
"""
import time
import logging
import argparse
from solana_real_trader import get_real_trader
from telegram_notifications import send_telegram_message
from decrypt_config import config

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("real_trading_test")

def test_balance():
    """Test getting wallet balance"""
    try:
        trader = get_real_trader()
        
        # Get wallet address from config
        wallet_address = config.get("solana_wallets", {}).get("wallet_1")
        if not wallet_address:
            logger.warning("No wallet_1 found in config. Using a mock address.")
            wallet_address = "5NY7AetzYAiNFu78mzcUcVKWWmSC2XFADyhUZFBQgVrL"
            
        logger.info(f"Testing balance for wallet: {wallet_address}")
            
        # Get SOL balance
        try:
            sol_balance = trader.get_wallet_balance(wallet_address)
            logger.info(f"SOL Balance: {sol_balance} SOL")
        except Exception as e:
            logger.error(f"Error getting SOL balance: {e}")
            logger.info("Falling back to mock SOL balance")
            sol_balance = 5.0
            logger.info(f"Mock SOL Balance: {sol_balance} SOL")
        
        # Get USDC balance
        try:
            usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
            usdc_balance = trader.get_wallet_balance(wallet_address, usdc_mint)
            logger.info(f"USDC Balance: {usdc_balance} USDC")
        except Exception as e:
            logger.error(f"Error getting USDC balance: {e}")
            logger.info("Falling back to mock USDC balance")
            usdc_balance = 100.0
            logger.info(f"Mock USDC Balance: {usdc_balance} USDC")
        
        # Try USDT balance too
        try:
            usdt_mint = "Es9vMFrzaCERiE2dZVjW6M9T3cxLVRshzF5sgJnpPzM9"  # USDT
            usdt_balance = trader.get_wallet_balance(wallet_address, usdt_mint)
            logger.info(f"USDT Balance: {usdt_balance} USDT")
        except Exception as e:
            logger.warning(f"Error getting USDT balance (this is okay): {e}")
        
        # Send a notification with the balances
        send_telegram_message(
            f"💰 Wallet Balance Check:\n"
            f"Wallet: {wallet_address[:8]}...{wallet_address[-4:]}\n"
            f"SOL: {sol_balance:.4f}\n"
            f"USDC: {usdc_balance:.2f}"
        )
        
        return {
            "sol": sol_balance,
            "usdc": usdc_balance
        }
    except Exception as e:
        logger.error(f"Error in test_balance: {e}")
        return {"sol": 0.0, "usdc": 0.0}

def test_price():
    """Test getting token prices"""
    trader = get_real_trader()
    
    # Test common tokens
    test_tokens = [
        ("SOL", "So11111111111111111111111111111111111111112"),
        ("USDC", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"),
        ("USDT", "Es9vMFrzaCERiE2dZVjW6M9T3cxLVRshzF5sgJnpPzM9"),
        ("BONK", "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263")
    ]
    
    results = {}
    
    for name, mint in test_tokens:
        price = trader.get_token_price(mint)
        logger.info(f"{name} Price: ${price:.6f}")
        results[name] = price
    
    return results

def test_new_pools():
    """Test fetching new pools"""
    trader = get_real_trader()
    
    # Get new pools
    pools = trader.monitor_new_liquidity_pools()
    
    logger.info(f"Found {len(pools)} new liquidity pools")
    
    for i, pool in enumerate(pools):
        token_mint = pool.get("baseMint", "")
        dex = pool.get("dex", "Unknown")
        liquidity = float(pool.get("liquidity", 0))
        
        # Get token info
        token_info = trader.get_token_metadata(token_mint)
        symbol = token_info.get("symbol", "Unknown")
        
        logger.info(f"Pool {i+1}: {symbol} ({token_mint}) on {dex}, Liquidity: ${liquidity:.2f}")
        
        # Get token price
        price = trader.get_token_price(token_mint)
        logger.info(f"  Price: ${price:.8f}")
    
    return pools

def test_buy(token_mint=None, amount=0.01):
    """Test buying a token"""
    trader = get_real_trader()
    
    if not token_mint:
        # Default to BONK if no token provided
        token_mint = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # BONK
    
    # Get token info
    token_info = trader.get_token_metadata(token_mint)
    symbol = token_info.get("symbol", "Unknown")
    
    logger.info(f"Testing buy for {symbol} ({token_mint})")
    logger.info(f"Using amount: {amount} SOL")
    
    # Confirm with user
    confirm = input(f"Are you sure you want to buy {symbol} with {amount} SOL? (y/n): ")
    if confirm.lower() != 'y':
        logger.info("Buy cancelled")
        return
    
    # Execute buy
    result = trader.buy_token(token_mint, amount)
    
    if result and result.get("success"):
        logger.info(f"Buy successful!")
        logger.info(f"Transaction ID: {result.get('txid')}")
        logger.info(f"Tokens received: {result.get('token_amount'):.8f} {symbol}")
        
        # Send notification
        send_telegram_message(
            f"✅ Test Buy Successful\n"
            f"Token: {symbol}\n"
            f"Amount: {result.get('token_amount'):.8f} {symbol}\n"
            f"Price: ${result.get('price'):.8f}\n"
            f"SOL spent: {amount}"
        )
    else:
        logger.error(f"Buy failed: {result.get('error') if result else 'Unknown error'}")
    
    return result

def test_sell(token_mint=None):
    """Test selling a token"""
    trader = get_real_trader()
    
    if not token_mint:
        # Default to BONK if no token provided
        token_mint = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # BONK
    
    # Get token info
    token_info = trader.get_token_metadata(token_mint)
    symbol = token_info.get("symbol", "Unknown")
    
    # Get token balance (mock)
    balance = 100  # Mock for testing
    
    logger.info(f"Testing sell for {symbol} ({token_mint})")
    logger.info(f"Current balance (mock): {balance:.8f} {symbol}")
    
    # Confirm with user
    confirm = input(f"Are you sure you want to sell {balance:.8f} {symbol}? (y/n): ")
    if confirm.lower() != 'y':
        logger.info("Sell cancelled")
        return
    
    # Execute sell
    result = trader.sell_token(token_mint)
    
    if result and result.get("success"):
        logger.info(f"Sell successful!")
        logger.info(f"Transaction ID: {result.get('txid')}")
        logger.info(f"Tokens sold: {result.get('token_amount'):.8f} {symbol}")
        logger.info(f"SOL received: {result.get('sol_received'):.8f} SOL")
        
        # Send notification
        send_telegram_message(
            f"✅ Test Sell Successful\n"
            f"Token: {symbol}\n"
            f"Amount: {result.get('token_amount'):.8f} {symbol}\n"
            f"Price: ${result.get('price'):.8f}\n"
            f"SOL received: {result.get('sol_received'):.8f} SOL"
        )
    else:
        logger.error(f"Sell failed: {result.get('error') if result else 'Unknown error'}")
    
    return result

def test_withdraw(amount=None, to_address=None):
    """Test withdrawing SOL"""
    trader = get_real_trader()
    
    # Get SOL balance
    sol_balance = trader.get_wallet_balance(trader.keypair.public_key)
    
    if sol_balance <= 0.01:
        logger.error(f"Insufficient SOL balance: {sol_balance} SOL (need > 0.01)")
        return
    
    # Use cold wallet from config if no address provided
    if not to_address:
        to_address = config.get("solana_wallets", {}).get("cold_wallet")
        if not to_address:
            logger.error("No destination address provided and no cold wallet in config")
            return
    
    # Calculate amount if not provided
    if amount is None:
        # Keep 0.01 SOL for gas
        amount = sol_balance - 0.01
    
    logger.info(f"Testing SOL withdrawal")
    logger.info(f"Current balance: {sol_balance:.8f} SOL")
    logger.info(f"Withdrawal amount: {amount:.8f} SOL")
    logger.info(f"Destination: {to_address}")
    
    # Confirm with user
    confirm = input(f"Are you sure you want to withdraw {amount:.8f} SOL to {to_address}? (y/n): ")
    if confirm.lower() != 'y':
        logger.info("Withdrawal cancelled")
        return
    
    # Execute withdrawal
    result = trader.transfer_sol(trader.keypair, to_address, amount)
    
    if result and result.get("success"):
        logger.info(f"Withdrawal successful!")
        logger.info(f"Transaction ID: {result.get('txid')}")
        
        # Send notification
        send_telegram_message(
            f"✅ Test Withdrawal Successful\n"
            f"Amount: {amount:.8f} SOL\n"
            f"Destination: {to_address}"
        )
    else:
        logger.error(f"Withdrawal failed: {result.get('error') if result else 'Unknown error'}")
    
    return result

def test_full_cycle(token_mint=None, buy_amount=0.01):
    """Test a full trading cycle: buy, monitor, sell, withdraw"""
    trader = get_real_trader()
    
    if not token_mint:
        # Default to BONK if no token provided
        token_mint = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # BONK
    
    # Get token info
    token_info = trader.get_token_metadata(token_mint)
    symbol = token_info.get("symbol", "Unknown")
    
    logger.info(f"Testing full cycle for {symbol} ({token_mint})")
    logger.info(f"Using amount: {buy_amount} SOL")
    
    # Confirm with user
    confirm = input(f"Are you sure you want to run a full trade cycle for {symbol}? (y/n): ")
    if confirm.lower() != 'y':
        logger.info("Test cancelled")
        return
    
    # Execute buy
    logger.info("Step 1: Buying token")
    buy_result = trader.buy_token(token_mint, buy_amount)
    
    if not buy_result or not buy_result.get("success"):
        logger.error(f"Buy failed: {buy_result.get('error') if buy_result else 'Unknown error'}")
        return
    
    logger.info(f"Buy successful!")
    logger.info(f"Tokens received: {buy_result.get('token_amount'):.8f} {symbol}")
    
    # Get initial price
    initial_price = buy_result.get("price") or trader.get_token_price(token_mint)
    
    # Monitor for a brief period
    logger.info("Step 2: Monitoring position for 30 seconds")
    for i in range(3):
        # Get current price
        current_price = trader.get_token_price(token_mint)
        
        # Calculate profit percentage
        profit_percent = ((current_price - initial_price) / initial_price) * 100
        
        logger.info(f"Current price: ${current_price:.8f}, Profit: {profit_percent:.2f}%")
        
        # Wait
        time.sleep(10)
    
    # Sell token
    logger.info("Step 3: Selling token")
    sell_result = trader.sell_token(token_mint)
    
    if not sell_result or not sell_result.get("success"):
        logger.error(f"Sell failed: {sell_result.get('error') if sell_result else 'Unknown error'}")
        return
    
    logger.info(f"Sell successful!")
    logger.info(f"Tokens sold: {sell_result.get('token_amount'):.8f} {symbol}")
    logger.info(f"SOL received: {sell_result.get('sol_received'):.8f} SOL")
    
    # Calculate profit/loss
    sol_received = sell_result.get("sol_received", 0)
    profit_sol = sol_received - buy_amount
    profit_percent = (profit_sol / buy_amount) * 100
    
    logger.info(f"Profit/Loss: {profit_sol:.8f} SOL ({profit_percent:.2f}%)")
    
    # Send notification
    send_telegram_message(
        f"✅ Full Test Cycle Completed\n"
        f"Token: {symbol}\n"
        f"SOL spent: {buy_amount:.8f}\n"
        f"SOL received: {sol_received:.8f}\n"
        f"Profit/Loss: {profit_sol:.8f} SOL ({profit_percent:.2f}%)"
    )
    
    return {
        "token": symbol,
        "buy": buy_result,
        "sell": sell_result,
        "profit_sol": profit_sol,
        "profit_percent": profit_percent
    }

def check_birdeye_key():
    """Check if Birdeye API key is configured"""
    try:
        birdeye_api_key = config.get("api_keys", {}).get("birdeye_api_key", "")
        
        if not birdeye_api_key:
            # Try the older format in config
            birdeye_api_key = "cc8ff825-27de-4804-9f6e-5bbb5a40fc3a"  # Use known key
            logger.warning("⚠️ No Birdeye API key found in config.api_keys, trying known key")
        
        # Verify it looks like a valid API key (basic check)
        if len(birdeye_api_key) < 10 or not any(c.isalpha() for c in birdeye_api_key):
            logger.warning("⚠️ Birdeye API key appears invalid. Using mock data for tests.")
            return False
        
        logger.info(f"Birdeye API key configured: {birdeye_api_key[:5]}...{birdeye_api_key[-5:]}")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Error checking Birdeye API key: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Test real trading functionality")
    parser.add_argument('--test', choices=['balance', 'price', 'pools', 'buy', 'sell', 'withdraw', 'cycle', 'all'], 
                        default='all', help='Test to run')
    parser.add_argument('--token', help='Token mint address for buy/sell tests')
    parser.add_argument('--amount', type=float, default=0.01, help='Amount of SOL to use for buy/withdraw tests')
    parser.add_argument('--to', help='Destination address for withdraw test')
    parser.add_argument('--mock', action='store_true', help='Force mock mode even if SDK is available')
    
    args = parser.parse_args()
    
    try:
        # If mock mode is requested, set the global variable
        if args.mock:
            # This is a bit of a hack to modify the imported module
            import solana_real_trader
            solana_real_trader.MOCK_MODE = True
            logger.info("Forced MOCK MODE enabled by command line flag")
        
        # Check for Birdeye API key
        check_birdeye_key()
        
        # Initialize real trading
        logger.info("Initializing trading...")
        trader = get_real_trader()
        
        # Check if we're in mock mode
        import solana_real_trader
        if solana_real_trader.MOCK_MODE:
            logger.info("===== RUNNING IN MOCK MODE - NO REAL TRANSACTIONS WILL BE EXECUTED =====")
        else:
            logger.info("===== RUNNING WITH REAL SOLANA INTEGRATION =====")
            
        logger.info(f"Live mode is {'ENABLED' if config.get('api_keys', {}).get('live_mode', False) else 'DISABLED'}")
        
        # Run tests
        if args.test == 'balance' or args.test == 'all':
            logger.info("=== Testing Balance ===")
            test_balance()
            print()
            
        if args.test == 'price' or args.test == 'all':
            logger.info("=== Testing Price Fetching ===")
            test_price()
            print()
            
        if args.test == 'pools' or args.test == 'all':
            logger.info("=== Testing New Pools ===")
            test_new_pools()
            print()
            
        if args.test == 'buy':
            logger.info("=== Testing Buy ===")
            test_buy(args.token, args.amount)
            print()
            
        if args.test == 'sell':
            logger.info("=== Testing Sell ===")
            test_sell(args.token)
            print()
            
        if args.test == 'withdraw':
            logger.info("=== Testing Withdraw ===")
            test_withdraw(args.amount, args.to)
            print()
            
        if args.test == 'cycle':
            logger.info("=== Testing Full Cycle ===")
            test_full_cycle(args.token, args.amount)
            print()
            
        logger.info("Tests completed!")
        
    except Exception as e:
        logger.error(f"Error running tests: {e}", exc_info=True)
        send_telegram_message(f"❌ Error in real trading tests: {str(e)}")

if __name__ == "__main__":
    main()
