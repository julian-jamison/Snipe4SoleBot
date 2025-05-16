🚀 Enhanced Solana Trading Bot
A multi-strategy trading system for the Solana blockchain, featuring enhanced pool detection, cross-DEX arbitrage, market making, and trend following.
Show Image
Show Image
Show Image
🚀 Features

Enhanced Pool Detection: Lower liquidity threshold and 24-hour pool monitoring
Cross-DEX Arbitrage: Profit from price differences across Raydium, Orca, and Meteora
Market Making: Passive income from providing liquidity with wide spreads
Trend Following: Technical analysis for established tokens with trailing stops
Telegram Integration: Full control and monitoring via Telegram notifications
Multi-wallet Support: Trade using multiple wallets for risk diversification
Risk Management: Dynamic position sizing and automated stop-losses

📋 Prerequisites

Python 3.7+
Solana wallet(s) with SOL
Helius API key
Telegram Bot token

🔧 Installation

Clone the repository:

bashgit clone https://github.com/yourusername/enhanced-solana-bot.git
cd enhanced-solana-bot

Create and activate a virtual environment:

bashpython -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

Install dependencies:

bashpip install -r requirements.txt

Create your configuration:

bashcp config.example.json config.json
# Edit config.json with your settings

Encrypt your configuration:

bashexport CONFIG_ENCRYPTION_KEY="your_encryption_key_here"
python encrypt_config.py
⚙️ Configuration
Edit your config.json file with the following settings:
json{
  "solana_wallets": {
    "wallet_1": "YOUR_WALLET_ADDRESS_1",
    "wallet_2": "YOUR_WALLET_ADDRESS_2",
    "wallet_3": "YOUR_WALLET_ADDRESS_3",
    "cold_wallet": "YOUR_COLD_STORAGE_WALLET",
    "signer_private_key": "YOUR_SIGNER_PRIVATE_KEY",
    "signer_public_key": "YOUR_SIGNER_PUBLIC_KEY"
  },
  "telegram": {
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "chat_id": "YOUR_TELEGRAM_CHAT_ID"
  },
  "trade_settings": {
    "min_liquidity": 500,
    "max_gas_fee": 0.002,
    "profit_target": 10,
    "stop_loss": -5,
    "trade_cooldown": 30,
    "dynamic_risk_management": {
      "enabled": true,
      "volatility_threshold": 0.03,
      "max_stop_loss": -10,
      "min_stop_loss": -2,
      "max_profit_target": 15,
      "min_profit_target": 5
    },
    "allowed_tokens": [
      "So11111111111111111111111111111111111111112",
      "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
      "Es9vMFrzaCERiE2dZVjW6M9T3cxLVRshzF5sgJnpPzM9"
    ]
  },
  "strategy_settings": {
    "sniper": {
      "enabled": true,
      "max_concurrent_positions": 3
    },
    "arbitrage": {
      "enabled": true,
      "min_price_difference_percent": 1.0
    },
    "market_making": {
      "enabled": true,
      "min_spread_percent": 1.0
    },
    "trend_following": {
      "enabled": true,
      "tokens_to_monitor": [
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "Es9vMFrzaCERiE2dZVjW6M9T3cxLVRshzF5sgJnpPzM9"
      ]
    }
  },
  "api_keys": {
    "live_mode": true,
    "solana_rpc_url": "https://rpc.mainnet.helius.xyz/?api-key=YOUR_HELIUS_API_KEY"
  }
}
🚀 Usage
Starting the Bot
bashpython bot.py
Running as a Service
To run the bot continuously, create a systemd service:
bashsudo nano /etc/systemd/system/enhanced-solana-bot.service
Add the following:
ini[Unit]
Description=Enhanced Solana Trading Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/path/to/enhanced-solana-bot
Environment="PATH=/path/to/enhanced-solana-bot/venv/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="CONFIG_ENCRYPTION_KEY=your_encryption_key_here"
ExecStart=/path/to/enhanced-solana-bot/venv/bin/python /path/to/enhanced-solana-bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
Enable and start the service:
bashsudo systemctl daemon-reload
sudo systemctl enable enhanced-solana-bot
sudo systemctl start enhanced-solana-bot
Telegram Commands

/start - Start all trading strategies
/stop - Stop all trading strategies
/status - View bot status and active positions
/strategy <name> <on/off> - Enable/disable specific strategy
/wallets - View wallet information
/health - View performance metrics and uptime

📊 Strategy Overview
1. 🎯 Sniper Strategy (Enhanced)

Targets new and recently created liquidity pools (last 24 hours)
Lower minimum liquidity threshold (500 SOL instead of 1000)
Automatic profit-taking and stop-loss management

2. 💱 Cross-DEX Arbitrage

Monitors major tokens (SOL, USDC, USDT) across DEXes
Executes trades to profit from price discrepancies
Configurable minimum price difference threshold

3. 📈 Market Making

Identifies pools with wider spreads for better profit margins
Places orders on both sides of the market
Automatically refreshes orders at configurable intervals

4. 📉 Trend Following

Technical analysis for established tokens
Uses SMA7, SMA25, and RSI for entry/exit signals
Trailing stop-loss for maximizing profits

🛡️ Security Best Practices

Use a dedicated server or VPS
Never share your private keys or config
Use a cold wallet for storing profits
Regularly rotate API keys
Enable 2FA on all related accounts
Only fund trading wallets with amounts you're willing to risk

⚡ Commands & Usage
CommandDescription/healthShows bot uptime, active strategies, and profit summary/strategy sniper onEnables the sniper strategy/strategy arbitrage onEnables the arbitrage strategy/strategy market_making onEnables the market making strategy/strategy trend_following onEnables the trend following strategy/pause allPauses all trading strategies/resume allResumes all trading strategies
🚀 Deploying to DigitalOcean (Step-by-Step)
1️⃣ Create a DigitalOcean Droplet

Sign up at DigitalOcean.
Click "Create" → Select "Droplets".
Choose Ubuntu 22.04 (Recommended) as the OS.
Select the Basic plan ($7/month or higher recommended).
Under Authentication, choose SSH Key (recommended) or Password.
Click "Create Droplet" and wait for deployment.

2️⃣ Connect to Your DigitalOcean Server

Open a terminal on your local machine.
Run the following command to connect (replace with your droplet's IP):

shssh root@your-droplet-ip
3️⃣ Install Required Dependencies
Run the following commands to set up the environment:
shsudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv git -y
4️⃣ Clone the Repository and Set Up

Clone the repository:

shgit clone https://github.com/yourusername/enhanced-solana-bot.git
cd enhanced-solana-bot

Create a virtual environment:

shpython3 -m venv venv
source venv/bin/activate

Install dependencies:

shpip install -r requirements.txt

Configure your settings:

shcp config.example.json config.json
nano config.json
# Edit with your settings

Encrypt your configuration:

shexport CONFIG_ENCRYPTION_KEY="your_encryption_key_here"
python encrypt_config.py
5️⃣ Set Up as a Service

Create a systemd service file:

shsudo nano /etc/systemd/system/enhanced-solana-bot.service

Add the following content (adjust paths):

ini[Unit]
Description=Enhanced Solana Trading Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/enhanced-solana-bot
Environment="PATH=/root/enhanced-solana-bot/venv/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="CONFIG_ENCRYPTION_KEY=your_encryption_key_here"
ExecStart=/root/enhanced-solana-bot/venv/bin/python /root/enhanced-solana-bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

Enable and start the service:

shsudo systemctl daemon-reload
sudo systemctl enable enhanced-solana-bot
sudo systemctl start enhanced-solana-bot

Check if the bot is running:

shsudo systemctl status enhanced-solana-bot
📝 License
This project is licensed under the MIT License - see the LICENSE file for details.
⚠️ Disclaimer
This bot is provided for educational and research purposes only. Trading cryptocurrencies involves significant risk. Use at your own risk. The developers are not responsible for any financial losses incurred while using this software.
🚀 Next Steps

 Deploy the bot to a VPS for 24/7 automated trading
 Add machine learning for pattern recognition and improved entries
 Implement portfolio rebalancing for token diversification
 Create a web dashboard for real-time monitoring


🤝 Support & Contributions
Contributions are welcome! Please feel free to submit a Pull Request.

Fork the repository
Create your feature branch (git checkout -b feature/amazing-feature)
Commit your changes (git commit -m 'Add some amazing feature')
Push to the branch (git push origin feature/amazing-feature)
Open a Pull Request
