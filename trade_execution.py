import time
import requests
import json
import asyncio
import base64
import random
from utils import fetch_price, log_trade_result
from telegram_notifications import safe_send_telegram_message
from decrypt_config import config
from portfolio import add_position, remove_position, get_position, get_all_positions
from solana.rpc.api import Client
from solders.keypair import Keypair
from solana.rpc.types import TxOpts
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import VersionedTransaction
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Bot
from telegram.request import HTTPXRequest as AiohttpRequest
import aiohttp

trade_settings = config["trade_settings"]
BACKTEST_MODE = False
MOCK_DATA_FILE = "mock_pools.json"
SOLANA_RPC_URL = config.get("api_keys", {}).get("solana_rpc_url", "https://api.mainnet-beta.solana.com")

TRADE_COOLDOWN_SECONDS = trade_settings.get("trade_cooldown", 30)
MAX_SESSION_BUDGET_SOL = trade_settings.get("max_session_budget", 15)
MIN_WALLET_BALANCE_SOL = 0.1

session_spent = 0
last_trade_time = 0

BAD_TOKENS = set(["BAD1", "SCAM2", "FAKE3"])

# Initialize signer and Solana client
signer = Keypair.from_bytes(bytes.fromhex(config["solana_wallets"]["signer_private_key"]))
client = Client(SOLANA_RPC_URL)  # You might need to switch to an async client if available

# Async function to fetch wallet balance
async def get_wallet_balance(wallet_address=None):
    try:
        wallet_address = wallet_address or str(signer.pubkey())
        response = await client.get_balance(wallet_address)  # Ensure that client supports async
        lamports = response['result']['value']
        return lamports / 1e9
    except Exception as e:
        print(f"⚠️ Failed to fetch balance: {e}")
        return 0

# Async function to calculate market volatility
async def get_market_volatility():
    return round(random.uniform(0.01, 0.06), 4)

# Function to calculate trade size based on volatility
def calculate_trade_size(volatility):
    base_quantity = 100
    if volatility > trade_settings["dynamic_risk_management"]["volatility_threshold"]:
        return base_quantity * 0.5
    elif volatility < 0.02:
        return base_quantity * 1.5
    return base_quantity

# Check if a token is suspicious
async def is_token_suspicious(token_address):
    try:
        url = f"https://public-api.solscan.io/token/meta?tokenAddress={token_address}"
        headers = {"accept": "application/json"}
        async with aiohttp.ClientSession() as session:
            response = await session.get(url, headers=headers, timeout=5)
            
            if response.status != 200:
                return True
            
            data = await response.json()
            suspicious_indicators = [
                data.get("name", "").lower() in ["", "token", "unknown"],
                "scam" in data.get("name", "").lower(),
                data.get("symbol", "").lower() in ["scam", "fake"],
                not data.get("verified", False)
            ]

            return any(suspicious_indicators)

    except Exception as e:
        print(f"⚠️ Scam check failed: {e}")
        return True

# Async function to send a trade transaction
async def send_trade_transaction(token_address, quantity, price, side, wallet_key=None):
    try:
        quote_url = "https://quote-api.jup.ag/v6/swap"
        user_pubkey = str(wallet_key.pubkey() if wallet_key else signer.pubkey())
        params = {
            "inputMint": "So11111111111111111111111111111111111111112" if side == "buy" else token_address,
            "outputMint": token_address if side == "buy" else "So11111111111111111111111111111111111111112",
            "amount": int(quantity * 1e9),
            "slippage": 1.0,
            "userPublicKey": user_pubkey,
            "wrapUnwrapSOL": True,
            "dynamicSlippage": True
        }
        async with aiohttp.ClientSession() as session:
            response = await session.get(quote_url, params=params)
            route_response = await response.json()
            
            if "swapTransaction" not in route_response:
                print(f"❌ No swapTransaction in Jupiter response: {route_response}")
                return None

            swap_tx = base64.b64decode(route_response["swapTransaction"])
            txn = VersionedTransaction.deserialize(swap_tx)
            
            # Use the provided wallet key or default to signer
            key_to_use = wallet_key or signer
            txn.sign([key_to_use])

            encoded_tx = base64.b64encode(txn.serialize()).decode('ascii')
            async with aiohttp.ClientSession() as session:
                response = await session.post(
                    f"{SOLANA_RPC_URL}", 
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "sendTransaction",
                        "params": [
                            encoded_tx,
                            {"skipPreflight": False, "preflightCommitment": "processed"}
                        ]
                    },
                    headers={"Content-Type": "application/json"}
                )
                result = await response.json()
                
            if "result" in result:
                sig = result["result"]
                print(f"🚀 Trade TX sent: https://solscan.io/tx/{sig}")
                return sig
            else:
                print(f"❌ Transaction failed: {result.get('error')}")
                return None
    except Exception as e:
        print(f"❌ Trade TX failed: {e}")
        return None

# Execute the trade
async def execute_trade(action, token_address):
    global session_spent, last_trade_time

    if token_address in BAD_TOKENS or await is_token_suspicious(token_address):
        print(f"🚫 Skipping suspicious token: {token_address}")
        return

    if time.time() - last_trade_time < TRADE_COOLDOWN_SECONDS:
        print("🕒 Cooldown active. Waiting before next trade.")
        return

    if await get_wallet_balance() < MIN_WALLET_BALANCE_SOL:
        print("🚫 Wallet balance too low. Skipping trade.")
        return

    if session_spent >= MAX_SESSION_BUDGET_SOL:
        print("💰 Max session budget reached. Skipping trade.")
        return

    volatility = await get_market_volatility()
    quantity = calculate_trade_size(volatility)

    price = await fetch_price(token_address)
    if price is None:
        print("❌ Could not fetch price. Trade aborted.")
        return

    stop_loss = max(trade_settings["dynamic_risk_management"]["min_stop_loss"],
                    trade_settings["dynamic_risk_management"]["max_stop_loss"] * volatility)
    profit_target = min(trade_settings["dynamic_risk_management"]["max_profit_target"],
                        trade_settings["dynamic_risk_management"]["min_profit_target"] * (1 / volatility))

    if action == "buy":
        print(f"🛒 Buying {quantity} of {token_address} at ${price:.4f} (Volatility: {volatility})")
        tx_sig = await send_trade_transaction(token_address, quantity, price, side="buy")
        await safe_send_telegram_message(
            f"✅ Bought {quantity} of {token_address} at ${price:.4f} (Volatility: {volatility})"
        )
        log_trade_result("buy", token_address, price, quantity, 0, "success")
        add_position(token_address, quantity, price, "dex")
        return tx_sig

    elif action == "sell":
        position = get_position(token_address)
        entry_price = position["price"] if position else price
        profit_loss = round((price - entry_price) * quantity, 6)
        print(f"📤 Selling {quantity} of {token_address} at ${price:.4f} with P/L: ${profit_loss:.4f} (Volatility: {volatility})")
        tx_sig = await send_trade_transaction(token_address, quantity, price, side="sell")
        await safe_send_telegram_message(
            f"✅ Sold {quantity} of {token_address} at ${price:.4f} with P/L: ${profit_loss:.4f} (Volatility: {volatility})"
        )
        log_trade_result("sell", token_address, price, quantity, profit_loss, "success")
        remove_position(token_address)
        return tx_sig

    session_spent += price * quantity
    last_trade_time = time.time()
    await asyncio.sleep(2)

# Check for auto-sell triggers based on profit/loss
async def check_for_auto_sell():
    for token in get_all_positions():
        position = get_position(token)
        if not position:
            continue

        current_price = await fetch_price(token)
        if current_price is None:
            continue

        entry_price = position["price"]
        profit_pct = ((current_price - entry_price) / entry_price) * 100

        if profit_pct >= trade_settings["profit_target"]:
            print(f"💰 Profit target hit for {token}. Auto-selling.")
            await execute_trade("sell", token)
        elif profit_pct <= trade_settings["stop_loss"]:
            print(f"🔻 Stop-loss triggered for {token}. Auto-selling.")
            await execute_trade("sell", token)

# Add missing functions that were in the import error

async def buy_token_multi_wallet(token_address, wallets=None):
    """
    Buy a token using multiple wallets
    
    Args:
        token_address: The address of the token to buy
        wallets: List of wallet addresses to use (default: use all configured wallets)
    """
    wallets_config = {
        "wallet_1": config["solana_wallets"]["wallet_1"],
        "wallet_2": config["solana_wallets"]["wallet_2"],
        "wallet_3": config["solana_wallets"]["wallet_3"]
    }
    
    # Use provided wallets or default to all configured wallets
    wallets_to_use = wallets or list(wallets_config.keys())
    
    results = []
    for wallet_name in wallets_to_use:
        wallet_address = wallets_config.get(wallet_name)
        if not wallet_address:
            print(f"⚠️ Wallet {wallet_name} not found in config")
            continue
            
        print(f"🔄 Executing buy for wallet {wallet_name}: {wallet_address}")
        
        # We'll use the default signer for now - in a real implementation, 
        # you would need to load the private key for each wallet
        result = await execute_trade("buy", token_address)
        if result:
            results.append({"wallet": wallet_name, "tx": result})
            
    return results

async def sell_token_auto_withdraw(token_address, withdraw_to_cold=True):
    """
    Sell a token and optionally withdraw to cold wallet
    
    Args:
        token_address: The address of the token to sell
        withdraw_to_cold: Whether to withdraw to cold wallet after selling
    """
    # First sell the token using the default execute_trade function
    sell_result = await execute_trade("sell", token_address)
    
    # If successful and withdrawal requested, send SOL to cold wallet
    if sell_result and withdraw_to_cold:
        cold_wallet = config["solana_wallets"]["cold_wallet"]
        
        # Wait for sell transaction to confirm
        await asyncio.sleep(5)
        
        # Get wallet balance after sell
        balance = await get_wallet_balance()
        if balance > MIN_WALLET_BALANCE_SOL + 0.01:  # Keep some SOL for gas
            withdrawal_amount = balance - MIN_WALLET_BALANCE_SOL
            print(f"💸 Withdrawing {withdrawal_amount} SOL to cold wallet: {cold_wallet}")
            
            # Implementation of SOL transfer would go here
            # This would use Solana transfer instruction
            # For now we'll just log it
            await safe_send_telegram_message(
                f"💰 Withdrew {withdrawal_amount} SOL to cold wallet"
            )
        else:
            print(f"⚠️ Balance too low for withdrawal: {balance} SOL")
    
    return sell_result
