#!/usr/bin/env python3
"""Fix to enable real trading instead of mock"""

from solana_real_trader import SolanaRealTrader
from solana.rpc.api import Client

def test_real_jupiter_trade():
    """Test actual Jupiter trade execution"""
    
    print("🔴 Testing REAL Jupiter trade...")
    
    # Initialize trader with working RPC
    trader = SolanaRealTrader()
    trader.rpc_url = 'https://api.mainnet-beta.solana.com'
    trader.client = Client(trader.rpc_url)
    
    # Reinitialize Jupiter
    from jupiter_integration import JupiterSwapper
    trader.jupiter_swapper = JupiterSwapper(trader.client, trader.keypair)
    
    # Check current balance
    initial_balance = trader.get_wallet_balance()
    print(f"💰 Starting balance: {initial_balance:.6f} SOL")
    
    if initial_balance < 0.005:
        print("❌ Insufficient balance for real trade test")
        return False
    
    # Test direct Jupiter buy (bypassing trader's buy_token method)
    print("🔴 Executing REAL Jupiter buy...")
    
    try:
        import asyncio
        
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Execute real Jupiter swap: 0.001 SOL -> USDC
        signature = loop.run_until_complete(
            trader.jupiter_swapper.buy_token_with_sol(
                "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                0.001,  # 0.001 SOL
                100     # 1% slippage
            )
        )
        
        if signature:
            print(f"✅ REAL TRADE SUCCESSFUL!")
            print(f"🔗 Transaction: https://solscan.io/tx/{signature}")
            
            # Wait and check balance
            import time
            time.sleep(5)
            
            final_balance = trader.get_wallet_balance()
            spent = initial_balance - final_balance
            print(f"💰 Final balance: {final_balance:.6f} SOL")
            print(f"💸 SOL spent: {spent:.6f} SOL")
            
            return True
        else:
            print("❌ Jupiter trade failed - no signature returned")
            return False
            
    except Exception as e:
        print(f"❌ Real trade error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def check_mock_mode_status():
    """Check if trader is in mock mode"""
    from solana_real_trader import MOCK_MODE
    print(f"MOCK_MODE status: {MOCK_MODE}")
    
    trader = SolanaRealTrader()
    print(f"Jupiter swapper exists: {trader.jupiter_swapper is not None}")
    
    # Check if trade methods are working
    if hasattr(trader, 'buy_token'):
        print("✅ buy_token method exists")
    else:
        print("❌ buy_token method missing")

if __name__ == "__main__":
    print("🔍 Checking trader status...")
    check_mock_mode_status()
    
    print("\n" + "="*50)
    print("🔴 Testing REAL trade...")
    
    confirm = input("This will spend ~$0.17 of real money. Continue? (yes/no): ")
    if confirm.lower() == 'yes':
        success = test_real_jupiter_trade()
        if success:
            print("\n🎉 REAL TRADING IS WORKING!")
        else:
            print("\n❌ Real trading test failed")
    else:
        print("Test cancelled")
