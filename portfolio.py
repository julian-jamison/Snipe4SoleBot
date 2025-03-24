import json
import os
from datetime import datetime

PORTFOLIO_FILE = "portfolio.json"


def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return {}


def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=4)


def update_portfolio(token, action, price, quantity):
    portfolio = load_portfolio()
    token_data = portfolio.get(token, {"quantity": 0, "average_price": 0})

    if action == "buy":
        total_cost = token_data["quantity"] * token_data["average_price"] + quantity * price
        token_data["quantity"] += quantity
        token_data["average_price"] = total_cost / token_data["quantity"]

    elif action == "sell":
        token_data["quantity"] -= quantity
        if token_data["quantity"] <= 0:
            portfolio.pop(token, None)
        else:
            portfolio[token] = token_data

    else:
        portfolio[token] = token_data

    save_portfolio(portfolio)


def calculate_portfolio_value(price_lookup_func):
    portfolio = load_portfolio()
    total_value = 0

    for token, data in portfolio.items():
        price = price_lookup_func(token)
        if price:
            total_value += data["quantity"] * price

    return total_value


def get_token_quantity(token):
    portfolio = load_portfolio()
    return portfolio.get(token, {}).get("quantity", 0)


def get_token_average_price(token):
    portfolio = load_portfolio()
    return portfolio.get(token, {}).get("average_price", 0)
