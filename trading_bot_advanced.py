# trading_bot_advanced.py

import json
import os
from datetime import datetime
from utils import fetch_price, log_trade_result
from telegram_notifications import send_telegram_message
from decrypt_config import config

PORTFOLIO_FILE = "portfolio.json"
trade_settings = config["trade_settings"]

# 1. Portfolio Tracking

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return {}

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=4)

def update_portfolio_on_buy(token, quantity, price):
    portfolio = load_portfolio()
    portfolio[token] = {
        "quantity": quantity,
        "buy_price": price,
        "timestamp": datetime.now().isoformat()
    }
    save_portfolio(portfolio)

def update_portfolio_on_sell(token):
    portfolio = load_portfolio()
    if token in portfolio:
        del portfolio[token]
        save_portfolio(portfolio)

# 2. Auto-Sell Logic

def check_portfolio_for_sell_opportunities():
    portfolio = load_portfolio()
    for token, data in portfolio.items():
        current_price = fetch_price(token)
        if current_price is None:
            continue

        entry_price = data["buy_price"]
        profit_pct = ((current_price - entry_price) / entry_price) * 100

        if profit_pct >= trade_settings["profit_target"] or profit_pct <= trade_settings["stop_loss"]:
            quantity = data["quantity"]
            print(f"📤 Selling {token} due to {'profit' if profit_pct > 0 else 'loss'} ({profit_pct:.2f}%)")
            send_telegram_message(f"📤 Auto-sell triggered for {token} at ${current_price:.4f} ({profit_pct:.2f}%)")
            log_trade_result("sell", token, current_price, quantity, profit_pct, "success")
            update_portfolio_on_sell(token)

# 3. Backtest Mode (very basic version)

def run_backtest_simulation(historical_data):
    capital = 1000
    portfolio = {}

    for point in historical_data:
        token = point["token"]
        price = point["price"]
        action = point["action"]  # "buy" or "sell"

        if action == "buy" and capital >= price:
            qty = capital / price
            portfolio[token] = {"quantity": qty, "buy_price": price}
            capital = 0
            print(f"[BUY] {qty:.2f} {token} at ${price}")

        elif action == "sell" and token in portfolio:
            qty = portfolio[token]["quantity"]
            entry_price = portfolio[token]["buy_price"]
            capital = qty * price
            profit_pct = ((price - entry_price) / entry_price) * 100
            print(f"[SELL] {qty:.2f} {token} at ${price} | PnL: {profit_pct:.2f}%")
            del portfolio[token]

    print(f"\nFinal capital: ${capital:.2f}")
