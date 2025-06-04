#!/usr/bin/env python3
"""
🚀 AUTOMATED TRADING SETUP SCRIPT
==================================
Quick setup for your proven Solana trading bot
"""

import os
import json
from datetime import datetime

def create_config_file():
    """Create trading configuration file"""
    config = {
        "wallet_address": "5NY7AetzYAiNFu78mzcUcVKWWmSC2XFADyhUZFBQgVrL",
        "first_successful_trade": "2ud7ixEqVGd1G8qbgfkVYebjDVejBPkCzrWBKeqrCFnxU6NQPW7rdScebe4VKmtMbDX3xW74d9Fk8xvTUcyKEHBV",
        "trading_strategies": {
            "conservative": {
                "dca_interval_minutes": 120,
                "dca_amount_sol": 0.001,
                "max_trade_amount_sol": 0.005,
                "daily_loss_limit_sol": 0.01,
                "active_tokens": ["USDC"]
            },
            "balanced": {
                "dca_interval_minutes": 60,
                "dca_amount_sol": 0.002,
                "max_trade_amount_sol": 0.01,
                "daily_loss_limit_sol": 0.02,
                "active_tokens": ["USDC", "BONK"]
            },
            "aggressive": {
                "dca_interval_minutes": 30,
                "dca_amount_sol": 0.005,
                "max_trade_amount_sol": 0.02,
                "daily_loss_limit_sol": 0.05,
                "active_tokens": ["USDC", "BONK", "RAY"]
            }
        },
        "created": datetime.now().isoformat()
    }
    
    with open('trading_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ Configuration file created: trading_config.json")

def create_log_files():
    """Create initial log files"""
    
    # Create trading log
    with open('trading_bot.log', 'w') as f:
        f.write(f"# Solana Trading Bot Log - Started {datetime.now()}\n")
    
    # Create trades JSON log
    with open('trades.json', 'w') as f:
        # Add the first successful trade
        first_trade = {
            "timestamp": "2025-05-29T14:32:00",
            "strategy": "Manual Test",
            "trade": "0.001 SOL → USDC",
            "signature": "2ud7ixEqVGd1G8qbgfkVYebjDVejBPkCzrWBKeqrCFnxU6NQPW7rdScebe4VKmtMbDX3xW74d9Fk8xvTUcyKEHBV",
            "status": "SUCCESS"
        }
        f.write(json.dumps(first_trade) + '\n')
    
    print("✅ Log files created: trading_bot.log, trades.json")

def check_dependencies():
    """Check if all required packages are installed"""
    required_packages = [
        'asyncio', 'aiohttp', 'requests', 'solders'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("Install with: pip install aiohttp requests solders")
        return False
    else:
        print("✅ All dependencies installed")
        return True

def main():
    print("🤖 AUTOMATED SOLANA TRADING BOT SETUP")
    print("=" * 50)
    print("✅ First trade successfully executed!")
    print("🔗 Transaction: 2ud7ixEqVGd1G8qbgfkVYebjDVejBPkCzrWBKeqrCFnxU6NQPW7rdScebe4VKmtMbDX3xW74d9Fk8xvTUcyKEHBV")
    print("💰 Result: 0.001 SOL → 0.173058 USDC")
    print("=" * 50)
    
    print("\n🔧 Setting up automated trading environment...")
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Please install missing dependencies first")
        return
    
    # Create config and log files
    create_config_file()
    create_log_files()
    
    print("\n🚀 SETUP COMPLETE!")
    print("=" * 30)
    print("📁 Files created:")
    print("  - trading_config.json (Bot configuration)")
    print("  - trading_bot.log (Activity log)")
    print("  - trades.json (Trade history)")
    print()
    print("🎯 Next steps:")
    print("  1. Run: python automated_trading_bot.py")
    print("  2. Choose your trading strategy")
    print("  3. Monitor with the dashboard")
    print()
    print("⚠️  Remember:")
    print("  - Start with small amounts")
    print("  - Monitor the first few trades")
    print("  - Bot uses proven trading method")
    print("=" * 30)
    
    # Quick balance check
    import requests
    balance_payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'getBalance',
        'params': ['5NY7AetzYAiNFu78mzcUcVKWWmSC2XFADyhUZFBQgVrL']
    }
    
    try:
        response = requests.post('https://api.mainnet-beta.solana.com', json=balance_payload, timeout=10)
        if response.ok:
            data = response.json()
            balance = data['result']['value'] / 1e9
            print(f"💰 Current balance: {balance:.6f} SOL")
            
            if balance > 0.01:
                print("✅ Sufficient balance for automated trading")
            else:
                print("⚠️  Low balance - consider adding more SOL")
        else:
            print("❌ Could not check balance")
    except:
        print("❌ Network error checking balance")

if __name__ == "__main__":
    main()
