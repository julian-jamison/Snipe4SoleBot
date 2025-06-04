#!/usr/bin/env python3
"""Debug balance checking issues"""

import requests
import json
from solana_real_trader import SolanaRealTrader

def check_balance_multiple_ways():
    """Test balance checking using different methods"""
    
    print("🔍 Testing balance checking methods...")
    
    # Initialize trader
    trader = SolanaRealTrader()
    wallet_address = str(trader.keypair.pubkey())
    rpc_url = trader.rpc_url
    
    print(f"Wallet: {wallet_address}")
    print(f"RPC URL: {rpc_url}")
    print("-" * 50)
    
    # Method 1: Direct RPC call
    print("Method 1: Direct RPC call")
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [wallet_address]
        }
        
        response = requests.post(rpc_url, json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.ok:
            data = response.json()
            print(f"Response: {data}")
            
            if 'result' in data:
                lamports = data['result']['value']
                sol_balance = lamports / 1e9
                print(f"✅ Direct RPC: {sol_balance:.6f} SOL ({lamports} lamports)")
            else:
                print(f"❌ No result in response: {data}")
        else:
            print(f"❌ HTTP error: {response.text}")
    except Exception as e:
        print(f"❌ Direct RPC error: {str(e)}")
    
    print("-" * 50)
    
    # Method 2: Solana client
    print("Method 2: Solana Python client")
    try:
        response = trader.client.get_balance(trader.keypair.pubkey())
        print(f"Client response type: {type(response)}")
        print(f"Client response: {response}")
        
        if hasattr(response, 'value'):
            lamports = response.value
            sol_balance = lamports / 1e9
            print(f"✅ Python client: {sol_balance:.6f} SOL ({lamports} lamports)")
        else:
            print("❌ No 'value' attribute in response")
            print(f"Available attributes: {dir(response)}")
    except Exception as e:
        print(f"❌ Python client error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
    
    print("-" * 50)
    
    # Method 3: Jupiter swapper
    print("Method 3: Jupiter swapper")
    try:
        if trader.jupiter_swapper:
            balance = trader.jupiter_swapper.get_wallet_balance_sol()
            print(f"✅ Jupiter swapper: {balance:.6f} SOL")
        else:
            print("❌ Jupiter swapper not initialized")
    except Exception as e:
        print(f"❌ Jupiter swapper error: {str(e)}")
    
    print("-" * 50)
    
    # Method 4: Command line verification
    print("Method 4: Run this command manually:")
    print(f"solana balance {wallet_address}")

if __name__ == "__main__":
    check_balance_multiple_ways()
