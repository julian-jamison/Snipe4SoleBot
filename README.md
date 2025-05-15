# 🚀 AI Crypto Trading Bot

# Snipe4SolBot

A high-performance automated trading bot for the Solana blockchain, designed to identify and capitalize on new liquidity pool opportunities.

![Solana](https://img.shields.io/badge/Solana-362783?style=for-the-badge&logo=solana&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)

## 🚀 Features

- **Real-time Liquidity Pool Monitoring**: Detects new pools across major Solana DEXs (Raydium, Orca, Meteora)
- **Automated Trading**: Configurable buy/sell strategies with dynamic parameters
- **Telegram Integration**: Control and monitor trades directly from Telegram
- **Multi-wallet Support**: Rotate between multiple wallets for trading
- **Profit Management**: Automated profit taking and stop-loss execution
- **Health Monitoring**: Self-healing capabilities with automatic restarts
- **Whale Tracking**: Monitor large wallet movements to inform trading decisions

## 📋 Prerequisites

- Python 3.8+
- Solana wallet(s) with SOL
- Helius API key
- Telegram Bot token

## 🔧 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Snipe4SoleBot.git
cd Snipe4SoleBot
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
    "min_liquidity": 1000,
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
      "Es9vMFrzaCERiE2dZVjW6M9T3cxLVRshzF5sgJnpPzM9"
    ]
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
sudo nano /etc/systemd/system/snipebot.service
```

Add the following:

```ini
[Unit]
Description=Snipe4SoleBot Solana Trading Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/path/to/Snipe4SoleBot
Environment="PATH=/path/to/Snipe4SoleBot/venv/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="CONFIG_ENCRYPTION_KEY=your_encryption_key_here"
ExecStart=/path/to/Snipe4SoleBot/venv/bin/python /path/to/Snipe4SoleBot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable snipebot
sudo systemctl start snipebot
```

### Telegram Commands

- `/start` - Start the bot
- `/stop` - Stop the bot
- `/restart` - Restart the bot
- `/status` - View bot status
- `/wallets` - View wallet information
- `/pause` - Pause trading
- `/resume` - Resume trading
- `/debug` - View debug information

## 📊 Monitoring

Check the bot's logs:

```bash
tail -f bot_debug.log
```

With systemd:

```bash
sudo journalctl -u snipebot -f
```

## 🛡️ Security Best Practices

1. Use a dedicated server or VPS
2. Never share your private keys or config
3. Use a cold wallet for storing profits
4. Regularly rotate API keys
5. Enable 2FA on all related accounts
6. Only fund trading wallets with amounts you're willing to risk

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This bot is provided for educational and research purposes only. Trading cryptocurrencies involves significant risk. Use at your own risk. The developers are not responsible for any financial losses incurred while using this software.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## ⚡ **Commands & Usage**
| Command | Description |
|---------|-------------|
| `/health` | Shows bot uptime, total trades, and profit summary. |
| `/pause` | Pauses trading without stopping the bot. |
| `/resume` | Resumes trading if paused. |
| `/strategy <mode>` | Switches between `aggressive`, `balanced`, and `conservative` modes. |

---

## 🚀 **Deploying to DigitalOcean (Step-by-Step)**

### **1️⃣ Create a DigitalOcean Droplet**
1. Sign up at [DigitalOcean](https://www.digitalocean.com/).
2. Click **"Create"** → Select **"Droplets"**.
3. Choose **Ubuntu 22.04 (Recommended)** as the OS.
4. Select the **cheapest plan ($5/month or higher)**.
5. Under **Authentication**, choose **SSH Key** (recommended) or **Password**.
6. Click **"Create Droplet"** and wait for deployment.

### **2️⃣ Connect to Your DigitalOcean Server**
1. Open a terminal on Replit (or use an SSH client like PuTTY if on Windows).
2. Run the following command to connect (replace with your droplet’s IP):
```sh
ssh root@your-droplet-ip
```

### **3️⃣ Install Required Dependencies on DigitalOcean**
Run the following commands to set up the environment:
```sh
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip -y
pip install pycryptodome python-telegram-bot requests
```

### **4️⃣ Clone Your GitHub Repository to the Server**
1. Navigate to your home directory:
```sh
cd ~
```
2. Clone your GitHub repository (replace with your repo URL):
```sh
git clone https://github.com/yourusername/trading-bot.git
```
3. Move into the project directory:
```sh
cd trading-bot
```

### **5️⃣ Set Up and Encrypt Configurations**
1. Run the encryption script to secure `config.json`:
```sh
python encrypt_config.py
```
2. Delete the original `config.json` for security:
```sh
rm config.json
```

### **6️⃣ Start the Trading Bot**
Run the bot in the background so it continues running after logout:
```sh
nohup python3 bot.py > bot.log 2>&1 &
```
To check logs:
```sh
tail -f bot.log
```

### **7️⃣ Set Up Auto-Restart Using systemd (Optional but Recommended)**
1. Create a systemd service file:
```sh
sudo nano /etc/systemd/system/tradingbot.service
```
2. Add the following content:
```ini
[Unit]
Description=AI Crypto Trading Bot
After=network.target

[Service]
User=root
WorkingDirectory=/root/trading-bot
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/tradingbot.log
StandardError=append:/var/log/tradingbot.log

[Install]
WantedBy=multi-user.target
```
3. Save and exit (`CTRL + X`, then `Y`, then `Enter`).
4. Reload systemd and enable the service:
```sh
sudo systemctl daemon-reload
sudo systemctl enable tradingbot
sudo systemctl start tradingbot
```
5. Check if the bot is running:
```sh
sudo systemctl status tradingbot
```

✅ **Now, your bot will restart automatically if it crashes or if the server reboots.**

---

## 🚀 **Next Steps**
- [ ] Deploy the bot to a VPS for **24/7 automated trading**.
- [ ] Implement **AI dip buying** to enter trades at oversold conditions.
- [ ] Monitor **performance in Telegram using `/health` reports**.

---

## 🤝 **Support & Contributions**
If you have any issues or suggestions, feel free to submit a **GitHub issue** or reach out via Telegram!

📌 **Would you like to add an automated backup system to save `config.enc` to the cloud (Google Drive or AWS S3)?** 🚀
