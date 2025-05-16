🚀 Enhanced Solana Trading Bot
This trading bot has been upgraded with multiple trading strategies for the Solana blockchain. It now supports four distinct trading strategies that can be used individually or in combination.
📊 Strategy Overview
1. 🎯 Sniper Strategy (Enhanced)
The original pool-sniping strategy has been improved with:

Lower minimum liquidity threshold (500 SOL instead of 1000)
Support for recently created pools (within the last 24 hours), not just brand new ones
Automatic profit-taking and stop-loss management

2. 💱 Cross-DEX Arbitrage
A new arbitrage strategy that:

Monitors for price differences of major tokens (SOL, USDC, USDT) across different DEXes
Automatically executes trades to profit from price discrepancies
Focuses on DEX programs including Raydium, Orca, and Meteora

3. 📈 Market Making
A market making strategy that:

Identifies pools with wider spreads
Implements passive market making by placing orders on both sides
Automatically refreshes orders at configurable intervals

4. 📉 Trend Following
A technical analysis-based strategy that:

Implements trend following for more established tokens
Uses moving averages and RSI for entry/exit points
Features trailing stop-loss for risk management

⚙️ Configuration
All strategies can be configured in the STRATEGY_CONFIG dictionary in monitor_and_trade.py:
pythonSTRATEGY_CONFIG = {
    "sniper": {
        "enabled": True,
        "max_concurrent_positions": 3,
        "profit_target_percent": 10,
        "stop_loss_percent": -5,
        "check_interval_seconds": 2
    },
    "arbitrage": {
        "enabled": True,
        "min_price_difference_percent": 1.0,
        "max_concurrent_trades": 2,
        "check_interval_seconds": 30,
        "tokens_to_monitor": [SOLANA_NATIVE_MINT, USDC_MINT, USDT_MINT]
    },
    "market_making": {
        "enabled": True,
        "min_spread_percent": 1.0,
        "max_concurrent_pools": 2,
        "order_refresh_seconds": 60,
        "check_interval_seconds": 300
    },
    "trend_following": {
        "enabled": True,
        "timeframes": ["4h"],
        "max_concurrent_positions": 3,
        "position_size_percent": 10,  # Percent of available capital
        "check_interval_seconds": 3600,  # 1 hour
        "tokens_to_monitor": []  # Will be populated from config
    }
}
🖥️ Usage
Running All Strategies
To run all strategies simultaneously:
pythonfrom monitor_and_trade import start_all_strategies, stop_all_strategies

# Start all enabled strategies
strategy_threads = start_all_strategies()

# To stop all strategies
stop_all_strategies()
Running Individual Strategies
You can also run strategies individually by setting only the desired strategy to enabled:
python# In monitor_and_trade.py
STRATEGY_CONFIG = {
    "sniper": {"enabled": True, ...},
    "arbitrage": {"enabled": False, ...},
    "market_making": {"enabled": False, ...},
    "trend_following": {"enabled": False, ...}
}

# Then run
from monitor_and_trade import start_all_strategies
start_all_strategies()
Backward Compatibility
For backward compatibility with the original bot, you can use:
pythonfrom monitor_and_trade import start_sniper_thread
sniper_thread = start_sniper_thread()
📋 Requirements
The bot requires the following dependencies:

Python 3.7+
aiohttp
solana.py
python-telegram-bot

🔧 Configuration

Update your config.json with appropriate settings
For trend following, add tokens in the "trend_following_tokens" section of your config

💬 Telegram Notifications
All strategies send notifications to Telegram about:

New trading opportunities detected
Trade entries and exits
Profit/loss information
Strategy status updates

⚠️ Caution
Trading cryptocurrencies involves significant risk. This bot is for educational purposes and should be thoroughly tested before using with real funds. Always:

Start with small amounts
Test thoroughly in a development environment
Monitor the bot's activities regularly
Be prepared for potential losses

🔍 Expanded Pool Criteria
The mempool monitor now uses the following expanded criteria:

Minimum pool liquidity: 500 SOL (lowered from 1000)
Considers pools created within the last 24 hours
Improved filtering for scam/honeypot tokens

📊 Technical Indicators
For trend following, the bot uses:

Simple Moving Averages (7 and 25 period)
Relative Strength Index (14 period)
Bullish criteria: SMA7 > SMA25 and RSI > 50
Bearish criteria: SMA7 < SMA25 and RSI < 50

📁 Folder Structure

mempool_monitor.py: Enhanced pool monitoring with expanded criteria
trade_execution.py: Trade execution logic for all strategies
monitor_and_trade.py: Main monitoring loops for all strategies
utils.py: Utility functions used across the bot
telegram_notifications.py: Telegram notification functionality
config_manager.py: Configuration loading and management
