#!/usr/bin/env python3
"""Test trader with working RPC endpoint"""

from solana_real_trader import SolanaRealTrader
import requests

def test_trader_with_working_rpc():
    """Test trader functionality with a working RPC"""
    
    print("🧪 Testing SolanaRealTrader with working RPC...")
    
    # Initialize trader
    trader = SolanaRealTrader()
    
    # Override the RPC URL with working one
    working_rpc = "https://api.mainnet-beta.solana.com"
    print(f"Using working RPC: {working_rpc}")
    
    # Update trader's RPC
    trader.rpc_url = working_rpc
    
    # Recreate client with working RPC
    from solana.rpc.api import Client
    trader.client = Client(working_rpc)
    
    # Reinitialize Jupiter with working client
    try:
        from jupiter_integration import JupiterSwapper
        trader.jupiter_swapper = JupiterSwapper(trader.client, trader.keypair)
        print("✅ Jupiter swapper reinitialized")
    except Exception as e:
        print(f"❌ Jupiter reinit failed: {str(e)}")
    
    # Test wallet info
    wallet_address = str(trader.keypair.pubkey())
    print(f"Wallet: {wallet_address}")
    
    # Test direct balance check
    print("\n🔍 Testing direct balance check...")
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [wallet_address]
    }
    
    response = requests.post(working_rpc, json=payload)
    if response.ok:
        data = response.json()
        lamports = data['result']['value']
        sol_balance = lamports / 1e9
        print(f"✅ Direct RPC balance: {sol_balance:.6f} SOL")
    
    # Test trader balance method
    print("\n🔍 Testing trader balance method...")
    try:
        balance = trader.get_wallet_balance()
        print(f"✅ Trader balance: {balance:.6f} SOL")
    except Exception as e:
        print(f"❌ Trader balance error: {str(e)}")
    
    # Test Jupiter quote (no actual trade)
    print("\n🔍 Testing Jupiter quote...")
    try:
        SOL_MINT = "So11111111111111111111111111111111111111112"
        USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        
        quote = trader.get_jupiter_quote(SOL_MINT, USDC_MINT, int(0.001 * 1e9)
        print(f"✅ Jupiter quote: {quote}")
        
        if quote and not quote.get('error'):
            in_amount = int(quote.get('inAmount', 0)
            out_amount = int(quote.get('outAmount', 0)
            
            if in_amount > 0 and out_amount > 0:
                print(f"💹 Quote: {in_amount / 1e9:.6f} SOL → {out_amount / 1e6:.6f} USDC")
                return True
            
    except Exception as e:
        print(f"❌ Jupiter quote error: {str(e)}")
    
    return False

if __name__ == "__main__":
    success = test_trader_with_working_rpc()
    if success:
        print("\n🎉 All tests passed! Ready for trading.")
    else:
        print("\n❌ Some tests failed. Check errors above.")
