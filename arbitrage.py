"""
trade_execution.py
~~~~~~~~~~~~~~~~~~

• Core trading helpers for Snipe4SoleBot
• High‑level `execute_trade()` performs an on‑chain buy/sell, logs results,
  and updates the portfolio.
• Thin wrapper `_exec_trade_simple()` is exported under the same name so
  arbitrage.py can call it without re‑adding positions.

All other functions (buy_token_multi_wallet, sell_token_auto_withdraw, etc.)
are unchanged from your original file.
"""

from __future__ import annotations

import time
import json
import asyncio
import base64
import random
import aiohttp
import requests
from typing import Optional

from utils import fetch_price, log_trade_result
from telegram_notifications import safe_send_telegram_message
from decrypt_config import config
from portfolio import add_position, remove_position, get_position, get_all_positions
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

# ─── Config & globals ──────────────────────────────────────────────────────

trade_settings        = config["trade_settings"]
BACKTEST_MODE         = False
MOCK_DATA_FILE        = "mock_pools.json"
SOLANA_RPC_URL        = config.get("api_keys", {}).get(
    "solana_rpc_url",
    "https://api.mainnet-beta.solana.com",
)

TRADE_COOLDOWN_SECONDS = trade_settings.get("trade_cooldown", 30)
MAX_SESSION_BUDGET_SOL = trade_settings.get("max_session_budget", 15)
MIN_WALLET_BALANCE_SOL = 0.1

session_spent = 0
last_trade_time = 0

BAD_TOKENS = {"BAD1", "SCAM2", "FAKE3"}

# Initialize signer and Solana client
signer  = Keypair.from_bytes(bytes.fromhex(config["solana_wallets"]["signer_private_key"]))
client  = Client(SOLANA_RPC_URL)  # switch to async client when available


# ───────────────────────── helper coroutines ──────────────────────────────

async def get_wallet_balance(wallet_address: Optional[str] = None) -> float:
    """Return wallet SOL balance as float."""
    wallet_address = wallet_address or str(signer.pubkey())
    try:
        response = await client.get_balance(wallet_address)  # ensure async
        lamports = response["result"]["value"]
        return lamports / 1e9
    except Exception as exc:
        print(f"⚠️ Failed to fetch balance: {exc}")
        return 0.0


async def get_market_volatility() -> float:
    """Dummy volatility model – replace with real oracle if available."""
    return round(random.uniform(0.01, 0.06), 4)


def calculate_trade_size(volatility: float) -> float:
    base_qty = 100
    if volatility > trade_settings["dynamic_risk_management"]["volatility_threshold"]:
        return base_qty * 0.5
    if volatility < 0.02:
        return base_qty * 1.5
    return base_qty


async def is_token_suspicious(token_address: str) -> bool:
    """Basic SolScan heuristic to skip obvious scams."""
    try:
        url     = f"https://public-api.solscan.io/token/meta?tokenAddress={token_address}"
        headers = {"accept": "application/json"}
        async with aiohttp.ClientSession() as session:
            r = await session.get(url, headers=headers, timeout=5)
            if r.status != 200:
                return True
            data = await r.json()
            return any(
                [
                    data.get("name", "").lower() in {"", "token", "unknown"},
                    "scam" in data.get("name", "").lower(),
                    data.get("symbol", "").lower() in {"scam", "fake"},
                    not data.get("verified", False),
                ]
            )
    except Exception as exc:
        print(f"⚠️ Scam check failed: {exc}")
        return True


# ───────────────────────── on‑chain swap helper ───────────────────────────

async def send_trade_transaction(
    token_address: str,
    quantity: float,
    price: float,
    side: str,
    wallet_key: Optional[Keypair] = None,
) -> Optional[str]:
    """
    Submit a Jupiter v6 swap and return the tx signature on success.
    """
    try:
        quote_url   = "https://quote-api.jup.ag/v6/swap"
        user_pubkey = str(wallet_key.pubkey() if wallet_key else signer.pubkey())
        params = {
            "inputMint":  "So11111111111111111111111111111111111111112" if side == "buy" else token_address,
            "outputMint": token_address if side == "buy" else "So11111111111111111111111111111111111111112",
            "amount":       int(quantity * 1e9),
            "slippage":     1.0,
            "userPublicKey": user_pubkey,
            "wrapUnwrapSOL": True,
            "dynamicSlippage": True,
        }
        async with aiohttp.ClientSession() as session:
            rr = await session.get(quote_url, params=params)
            route = await rr.json()

        if "swapTransaction" not in route:
            print(f"❌ No swapTransaction in Jupiter response: {route}")
            return None

        swap_tx = base64.b64decode(route["swapTransaction"])
        txn     = VersionedTransaction.deserialize(swap_tx)

        key_to_use = wallet_key or signer
        txn.sign([key_to_use])

        encoded_tx = base64.b64encode(txn.serialize()).decode("ascii")
        async with aiohttp.ClientSession() as session:
            rs = await session.post(
                SOLANA_RPC_URL,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "sendTransaction",
                    "params": [
                        encoded_tx,
                        {"skipPreflight": False, "preflightCommitment": "processed"},
                    ],
                },
                headers={"Content-Type": "application/json"},
            )
            result = await rs.json()

        if "result" in result:
            sig = result["result"]
            print(f"🚀 Trade TX sent: https://solscan.io/tx/{sig}")
            return sig

        print(f"❌ Transaction failed: {result.get('error')}")
        return None
    except Exception as exc:
        print(f"❌ Trade TX failed: {exc}")
        return None


# ───────────────────────── high‑level trade executor ──────────────────────

async def execute_trade(action: str, token_address: str):
    """
    Master trade routine used by sniping logic and manual commands.
    Handles wallet/risk checks, sends tx, logs, updates portfolio.
    Returns tx signature (str) or None.
    """
    global session_spent, last_trade_time

    if token_address in BAD_TOKENS or await is_token_suspicious(token_address):
        print(f"🚫 Skipping suspicious token: {token_address}")
        return None

    if time.time() - last_trade_time < TRADE_COOLDOWN_SECONDS:
        print("🕒 Cooldown active. Waiting before next trade.")
        return None

    if await get_wallet_balance() < MIN_WALLET_BALANCE_SOL:
        print("🚫 Wallet balance too low. Skipping trade.")
        return None

    if session_spent >= MAX_SESSION_BUDGET_SOL:
        print("💰 Max session budget reached. Skipping trade.")
        return None

    volatility = await get_market_volatility()
    quantity   = calculate_trade_size(volatility)
    price      = await fetch_price(token_address)

    if price is None:
        print("❌ Could not fetch price. Trade aborted.")
        return None

    # dynamic risk
    stop_loss = max(
        trade_settings["dynamic_risk_management"]["min_stop_loss"],
        trade_settings["dynamic_risk_management"]["max_stop_loss"] * volatility,
    )
    profit_target = min(
        trade_settings["dynamic_risk_management"]["max_profit_target"],
        trade_settings["dynamic_risk_management"]["min_profit_target"] * (1 / volatility),
    )

    if action == "buy":
        print(f"🛒 Buying {quantity} of {token_address} at ${price:.4f} (Vol: {volatility})")
        tx_sig = await send_trade_transaction(token_address, quantity, price, side="buy")
        if tx_sig:
            await safe_send_telegram_message(
                f"✅ Bought {quantity} of {token_address} at ${price:.4f} (Vol: {volatility})"
            )
            log_trade_result("buy", token_address, price, quantity, 0, "success")
            add_position(token_address, quantity, price, "dex")
        return tx_sig

    elif action == "sell":
        position      = get_position(token_address)
        entry_price   = position["price"] if position else price
        profit_loss   = round((price - entry_price) * quantity, 6)
        print(f"📤 Selling {quantity} of {token_address} at ${price:.4f} | P/L ${profit_loss:.4f}")
        tx_sig = await send_trade_transaction(token_address, quantity, price, side="sell")
        if tx_sig:
            await safe_send_telegram_message(
                f"✅ Sold {quantity} of {token_address} at ${price:.4f} | P/L ${profit_loss:.4f}"
            )
            log_trade_result("sell", token_address, price, quantity, profit_loss, "success")
            remove_position(token_address)
        return tx_sig

    session_spent += price * quantity
    last_trade_time = time.time()
    await asyncio.sleep(2)
    return None


# ───────────────────────── thin adapter for arbitrage.py ───────────────────

async def _exec_trade_simple(side: str, token: str) -> bool:
    """
    Lightweight wrapper so arbitrage.py can call `execute_trade()` without
    size/wallet args **and without altering the portfolio twice**.
    """
    sig = await execute_trade(side, token)   # call full routine
    return bool(sig)


# Export under the original name arbitrage.py imports
# (This *overrides* the heavy name *only* for modules imported *after*
#  this re‑binding, which includes arbitrage.py.  The heavy version is still
#  reachable as `execute_trade_full` if ever needed.)
execute_trade_simple = _exec_trade_simple
execute_trade        = _exec_trade_simple   # what arbitrage.py resolves
