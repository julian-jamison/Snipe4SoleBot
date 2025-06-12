# 🚀 Snipe4SoleBot - Advanced Solana Trading Bot

A comprehensive multi-strategy automated trading system for the Solana blockchain, featuring real-time pool detection, cross-DEX arbitrage, market making, and intelligent trend following.

![Solana](https://img.shields.io/badge/Solana-362783?style=for-the-badge&logo=solana&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.7+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)
![Status](https://img.shields.io/badge/Status-LIVE%20TRADING-success?style=for-the-badge)

## 🎯 Key Features

- **🎯 Sniper Strategy**: Detects and trades new liquidity pools within seconds
- **💱 Cross-DEX Arbitrage**: Profits from price differences across Raydium, Orca, and Meteora
- **📊 Market Making**: Provides liquidity with wide spreads for passive income
- **📈 Trend Following**: Technical analysis with SMA and RSI indicators
- **📱 Telegram Integration**: Full remote control and real-time notifications
- **🔒 Security**: Encrypted configuration and cold wallet integration
- **⚡ Live Trading**: Real Jupiter aggregator integration for optimal prices
- **🤖 Multi-Wallet**: Distribute trades across multiple wallets for better efficiency

## 🏆 Trading Performance

- ✅ **Live Trading Mode**: Executes real trades on Solana mainnet
- ✅ **Risk Management**: Dynamic stop-losses and profit targets
- ✅ **Auto-Withdrawal**: Profits automatically sent to cold storage
- ✅ **24/7 Operation**: Continuous monitoring and trading
- ✅ **Helius RPC**: Premium Solana node for reliable connections

## 📋 Prerequisites

- **Python 3.7+**
- **Solana wallet** with trading capital in SOL
- **Helius API key** (for reliable RPC access)
- **Telegram Bot token** (for notifications and control)
- **Linux VPS** (recommended for 24/7 operation)

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/julian-jamison/Snipe4SoleBot.git
cd Snipe4SoleBot
```

### 2. Setup Environment
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Settings
```bash
# Copy example config
cp config.example.json config.json

# Edit with your settings
nano config.json
```

### 4. Required Configuration
```json
{
  "solana_wallets": {
    "wallet_1": "YOUR_TRADING_WALLET_1",
    "wallet_2": "YOUR_TRADING_WALLET_2", 
    "wallet_3": "YOUR_TRADING_WALLET_3",
    "cold_wallet": "YOUR_COLD_STORAGE_WALLET",
    "private_key_hex": "YOUR_128_CHAR_HEX_PRIVATE_KEY",
    "public_key": "YOUR_PUBLIC_KEY"
  },
  "telegram": {
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "chat_id": "YOUR_TELEGRAM_CHAT_ID"
  },
  "trade_settings": {
    "min_liquidity": 1000,
    "profit_target": 10,
    "stop_loss": -5,
    "trade_cooldown": 30,
    "allowed_tokens": [
      "So11111111111111111111111111111111111111112",
      "Es9vMFrzaCERiE2dZVjW6M9T3cxLVRshzF5sgJnpPzM9"
    ]
  },
  "api_keys": {
    "live_mode": true,
    "solana_rpc_url": "https://rpc.mainnet.helius.xyz/?api-key=YOUR_HELIUS_KEY",
    "birdeye_api_key": "YOUR_BIRDEYE_API_KEY"
  }
}
```

### 5. Start Trading
```bash
# Start the bot
python bot.py

# Or run in background
nohup python bot.py > bot.log 2>&1 &
```

## 📱 Telegram Commands

Once your bot is running, use these commands in Telegram:

| Command | Description |
|---------|-------------|
| `/start` | Show available commands |
| `/status` | View bot status and active strategies |
| `/balance` | Check wallet balances |
| `/positions` | View open trading positions |
| `/strategy <name> <on/off>` | Enable/disable specific strategies |
| `/shutdown` | Safely stop the bot |

## 🎯 Trading Strategies

### 1. **Sniper Strategy** 🎯
- Monitors new liquidity pool creation in real-time
- Executes buy orders within seconds of pool launch
- Implements safety checks for honeypots and scam tokens
- Auto-sells at profit targets or stop-losses

### 2. **Cross-DEX Arbitrage** 💱
- Scans price differences across major Solana DEXes
- Executes profitable arbitrage trades automatically
- Minimum 1% profit threshold for execution
- Supports Raydium, Orca, and Meteora

### 3. **Market Making** 📊
- Identifies pools with wide bid-ask spreads
- Places orders on both sides for passive income
- Automatically refreshes orders every 60 seconds
- Targets minimum 1% spread for profitability

### 4. **Trend Following** 📈
- Technical analysis using SMA7, SMA25, and RSI
- Enters positions on confirmed bullish trends
- Implements trailing stops to maximize profits
- Monitors established tokens like USDC, USDT

## 🛡️ Security Features

- **🔐 Encrypted Configuration**: Sensitive data protected with AES encryption
- **💰 Cold Wallet Integration**: Profits auto-transferred to cold storage
- **🔒 Private Key Security**: Local storage only, never transmitted
- **🛡️ Scam Protection**: Multiple layers of token verification
- **⚠️ Risk Management**: Position limits and loss prevention

## 🚀 Deployment Options

### Option 1: Local Development
```bash
# Run locally for testing
python bot.py
```

### Option 2: DigitalOcean VPS (Recommended)
```bash
# 1. Create Ubuntu 22.04 droplet
# 2. Install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv git -y

# 3. Clone and setup
git clone https://github.com/julian-jamison/Snipe4SoleBot.git
cd Snipe4SoleBot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Configure and start
cp config.example.json config.json
# Edit config.json with your settings
python bot.py
```

### Option 3: Systemd Service (24/7 Operation)
```bash
# Create service file
sudo nano /etc/systemd/system/snipe4solebot.service

# Add configuration:
[Unit]
Description=Snipe4SoleBot Trading System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/Snipe4SoleBot
Environment="PATH=/root/Snipe4SoleBot/venv/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/root/Snipe4SoleBot/venv/bin/python /root/Snipe4SoleBot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable snipe4solebot
sudo systemctl start snipe4solebot
```

## 📊 Monitoring & Logs

```bash
# Check bot status
sudo systemctl status snipe4solebot

# View live logs
tail -f telegram_bot.log
tail -f monitor.log

# Check trading positions
cat portfolio.json

# Monitor system resources
htop
```

## ⚙️ Configuration Options

### Trading Parameters
- `min_liquidity`: Minimum pool liquidity (default: 1000 SOL)
- `profit_target`: Take profit percentage (default: 10%)
- `stop_loss`: Stop loss percentage (default: -5%)
- `trade_cooldown`: Seconds between trades (default: 30)

### Risk Management
- `max_concurrent_positions`: Maximum open positions per strategy
- `daily_loss_limit`: Maximum daily loss before stopping
- `dynamic_risk_management`: Adjust parameters based on volatility

### Strategy Toggles
```json
"strategy_settings": {
  "sniper": {"enabled": true, "max_concurrent_positions": 3},
  "arbitrage": {"enabled": true, "min_price_difference_percent": 1.0},
  "market_making": {"enabled": true, "min_spread_percent": 1.0},
  "trend_following": {"enabled": true}
}
```

## 🔧 Troubleshooting

### Common Issues
1. **Private Key Error**: Ensure your private key is exactly 128 hex characters
2. **RPC Connection**: Verify your Helius API key and URL
3. **Telegram Not Working**: Check bot token and chat ID
4. **No Trades Executing**: Review `allowed_tokens` and `min_liquidity` settings

### Support Commands
```bash
# Check syntax errors
python3 -m py_compile *.py

# Test configuration
python3 -c "from decrypt_config import config; print('Config loaded:', bool(config))"

# Verify dependencies
pip check
```

## 📈 Performance Metrics

The bot tracks and reports:
- **Total Trades Executed**
- **Win/Loss Ratio**
- **Total Profit/Loss in SOL**
- **Average Trade Duration**
- **Strategy Performance Breakdown**

## ⚠️ Disclaimer

**This trading bot is for educational and research purposes. Cryptocurrency trading involves substantial risk of loss. Use at your own risk.**

- Start with small amounts to test functionality
- Never invest more than you can afford to lose
- Monitor the bot regularly, especially during high volatility
- The developers are not responsible for any financial losses

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Solana Foundation** for the robust blockchain infrastructure
- **Jupiter Protocol** for aggregated DEX routing
- **Helius** for reliable RPC services
- **Python Telegram Bot** library for seamless integration

---

**🚀 Ready to start automated trading on Solana? Get your bot running in minutes!**

*Last Updated: June 2025*
