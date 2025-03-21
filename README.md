# 🚀 AI Crypto Trading Bot

## 📌 **Project Overview**
This project is an AI-powered crypto trading bot that automatically detects market opportunities, tracks whale transactions, and executes trades on decentralized exchanges (DEXs). It also includes automated Telegram notifications and encryption for sensitive configuration files.

---

## ✅ **Setup Instructions**

### **1️⃣ Upload Project to Replit**
1. Create a **new Python Repl** on [Replit](https://replit.com/).
2. Upload all project files.

### **2️⃣ Install Required Dependencies**
Run the following command in the Replit **terminal**:
```sh
pip install pycryptodome python-telegram-bot requests
```

### **3️⃣ Encrypt Your Configuration**
1. Run the encryption script to create `config.enc`:
```sh
python encrypt_config.py
```
2. Delete the original `config.json` file to secure sensitive data:
```sh
rm config.json
```

### **4️⃣ Start the Trading Bot**
Run the following command to start the bot:
```sh
python bot.py
```

---

## 🔒 **Security & Best Practices**
- **NEVER share `config.enc` or `CONFIG_ENCRYPTION_KEY`.**
- **Ensure `.gitignore` includes sensitive files** to prevent accidental exposure.
- **Use a VPS (like DigitalOcean) for 24/7 uptime instead of running on Replit.**

---

## 🛠 **Available Features**
✔ **AI-Based Trading Strategy** – Dynamic trade execution based on market conditions.  
✔ **Whale Transaction Tracking** – Auto-buy/sell based on whale activity.  
✔ **Gas Fee Optimization** – Avoids high transaction fees by delaying execution.  
✔ **Automated Telegram Alerts** – Get real-time notifications for trades, profits, and system status.  
✔ **Encrypted Configuration** – Protects wallet addresses and API keys.  
✔ **Manual Commands via Telegram** – `/pause`, `/resume`, `/health`, `/strategy`.

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
