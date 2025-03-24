import json
import os

PORTFOLIO_FILE = "portfolio.json"

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return {}

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=4)

def add_position(token, quantity, price, dex):
    portfolio = load_portfolio()

    if token in portfolio:
        old = portfolio[token]
        total_quantity = old["quantity"] + quantity
        avg_price = ((old["price"] * old["quantity"]) + (price * quantity)) / total_quantity
        portfolio[token]["price"] = round(avg_price, 6)
        portfolio[token]["quantity"] = total_quantity
    else:
        portfolio[token] = {
            "quantity": quantity,
            "price": round(price, 6),
            "dex": dex
        }

    save_portfolio(portfolio)

def remove_position(token):
    portfolio = load_portfolio()
    if token in portfolio:
        del portfolio[token]
        save_portfolio(portfolio)

def get_position(token):
    return load_portfolio().get(token)

def get_all_positions():
    return load_portfolio()
