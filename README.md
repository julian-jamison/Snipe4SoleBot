# 🚀 Enhanced Solana Trading Bot

A multi-strategy trading system for the Solana blockchain, featuring enhanced pool detection, cross-DEX arbitrage, market making, and trend following.

![Solana](https://img.shields.io/badge/Solana-362783?style=for-the-badge&logo=solana&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)

## 🚀 Features

- **Enhanced Pool Detection**: Lower liquidity threshold and 24-hour pool monitoring
- **Cross-DEX Arbitrage**: Profit from price differences across Raydium, Orca, and Meteora
- **Market Making**: Passive income from providing liquidity with wide spreads
- **Trend Following**: Technical analysis for established tokens with trailing stops
- **Telegram Integration**: Full control and monitoring via Telegram notifications
- **Multi-wallet Support**: Trade using multiple wallets for risk diversification
- **Risk Management**: Dynamic position sizing and automated stop-losses

## 📋 Prerequisites

- Python 3.7+
- Solana wallet(s) with SOL
- Helius API key
- Telegram Bot token

## 🔧 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/enhanced-solana-bot.git
cd enhanced-solana-bot
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create your configuration:
```bash
cp config.example.json config.json
# Edit config.json with your settings
```

5. Encrypt your configuration:
```bash
export CONFIG_ENCRYPTION_KEY="your_encryption_key_here"
python encrypt_config.py
```

## ⚙️ Configuration

Edit your `config.json` file with the following settings:

```json
{
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
```

## 🚀 Usage

### Starting the Bot

```bash
python bot.py
```

### Running as a Service

To run the bot continuously, create a systemd service:

```bash
sudo nano /etc/systemd/system/enhanced-solana-bot.service
```

Add the following:

```ini
[Unit]
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
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable enhanced-solana-bot
sudo systemctl start enhanced-solana-bot
```

### Telegram Commands

- `/start` - Start all trading strategies
- `/stop` - Stop all trading strategies
- `/status` - View bot status and active positions
- `/strategy <name> <on/off>` - Enable/disable specific strategy
- `/wallets` - View wallet information
- `/health` - View performance metrics and uptime

## 📊 Strategy Overview

### 1. 🎯 Sniper Strategy (Enhanced)
- Targets new and recently created liquidity pools (last 24 hours)
- Lower minimum liquidity threshold (500 SOL instead of 1000)
- Automatic profit-taking and stop-loss management

### 2. 💱 Cross-DEX Arbitrage
- Monitors major tokens (SOL, USDC, USDT) across DEXes
- Executes trades to profit from price discrepancies
- Configurable minimum price difference threshold

### 3. 📈 Market Making
- Identifies pools with wider spreads for better profit margins
- Places orders on both sides of the market
- Automatically refreshes orders at configurable intervals

### 4. 📉 Trend Following
- Technical analysis for established tokens
- Uses SMA7, SMA25, and RSI for entry/exit signals
- Trailing stop-loss for maximizing profits

## 🛡️ Security Best Practices

1. Use a dedicated server or VPS
2. Never share your private keys or config
3. Use a cold wallet for storing profits
4. Regularly rotate API keys
5. Enable 2FA on all related accounts
6. Only fund trading wallets with amounts you're willing to risk

## ⚡ Commands & Usage

| Command | Description |
|---------|-------------|
| `/health` | Shows bot uptime, active strategies, and profit summary |
| `/strategy sniper on` | Enables the sniper strategy |
| `/strategy arbitrage on` | Enables the arbitrage strategy |
| `/strategy market_making on` | Enables the market making strategy |
| `/strategy trend_following on` | Enables the trend following strategy |
| `/pause all` | Pauses all trading strategies |
| `/resume all` | Resumes all trading strategies |

## 🚀 Deploying to DigitalOcean (Step-by-Step)

### **1️⃣ Create a DigitalOcean Droplet**
1. Sign up at [DigitalOcean](https://www.digitalocean.com/).
2. Click **"Create"** → Select **"Droplets"**.
3. Choose **Ubuntu 22.04 (Recommended)** as the OS.
4. Select the **Basic plan ($7/month or higher recommended)**.
5. Under **Authentication**, choose **SSH Key** (recommended) or **Password**.
6. Click **"Create Droplet"** and wait for deployment.

### **2️⃣ Connect to Your DigitalOcean Server**
1. Open a terminal on your local machine.
2. Run the following command to connect (replace with your droplet's IP):
```sh
ssh root@your-droplet-ip
```

### **3️⃣ Install Required Dependencies**
Run the following commands to set up the environment:
```sh
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv git -y
```

### **4️⃣ Clone the Repository and Set Up**
1. Clone the repository:
```sh
git clone https://github.com/yourusername/enhanced-solana-bot.git
cd enhanced-solana-bot
```

2. Create a virtual environment:
```sh
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```sh
pip install -r requirements.txt
```

4. Configure your settings:
```sh
cp config.example.json config.json
nano config.json
# Edit with your settings
```

5. Encrypt your configuration:
```sh
export CONFIG_ENCRYPTION_KEY="your_encryption_key_here"
python encrypt_config.py
```

### **5️⃣ Set Up as a Service**
1. Create a systemd service file:
```sh
sudo nano /etc/systemd/system/enhanced-solana-bot.service
```

2. Add the following content (adjust paths):
```ini
[Unit]
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
```

3. Enable and start the service:
```sh
sudo systemctl daemon-reload
sudo systemctl enable enhanced-solana-bot
sudo systemctl start enhanced-solana-bot
```

4. Check if the bot is running:
```sh
sudo systemctl status enhanced-solana-bot
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This bot is provided for educational and research purposes only. Trading cryptocurrencies involves significant risk. Use at your own risk. The developers are not responsible for any financial losses incurred while using this software.

## 🚀 Next Steps
- [ ] Deploy the bot to a VPS for **24/7 automated trading**
- [ ] Add machine learning for pattern recognition and improved entries
- [ ] Implement portfolio rebalancing for token diversification
- [ ] Create a web dashboard for real-time monitoring

---

## 🤝 Support & Contributions

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
