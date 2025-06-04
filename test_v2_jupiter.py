#!/usr/bin/env python3
"""Test v2 Jupiter trading with better transaction handling"""

import asyncio
from solana_real_trader import SolanaRealTrader
from solana.rpc.api import Client

async def test_v2_jupiter_trade():
    """Test v2 Jupiter trading method"""
    
    print("🔴 Testing v2 Jupiter trade...")
    
    # Initialize trader with working RPC
    trader = SolanaRealTrader()
    trader.rpc_url = 'https://api.mainnet-beta.solana.com'
    trader.client = Client(trader.rpc_url)
    
    # Reinitialize Jupiter
    from jupiter_integration import JupiterSwapper
    trader.jupiter_swapper = JupiterSwapper(trader.client, trader.keypair)
    
    # Check balance
    initial_balance = trader.get_wallet_balance()
    print(f"💰 Starting balance: {initial_balance:.6f} SOL")
    
    if initial_balance < 0.005:
        print("❌ Insufficient balance for trade")
        return False
    
    try:
        # Test v2 method
        print("🔴 Executing v2 Jupiter buy...")
        
        signature = await trader.jupiter_swapper.buy_token_with_sol_v2(
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            0.001,  # 0.001 SOL
            100     # 1% slippage
        )
        
        if signature:
            print(f"✅ v2 TRADE SUCCESSFUL!")
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
            print("❌ v2 Jupiter trade failed")
            return False
            
    except Exception as e:
        print(f"❌ v2 trade error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    print("🔍 Testing v2 Jupiter integration...")
    
    confirm = input("This will spend ~$0.17 of real money with v2 method. Continue? (yes/no): ")
    if confirm.lower() == 'yes':
        success = asyncio.run(test_v2_jupiter_trade())
        if success:
            print("\n🎉 V2 REAL TRADING IS WORKING!")
        else:
            print("\n❌ v2 trading test failed")
    else:
        print("Test cancelled")

if __name__ == "__main__":
    main()
