"""mempool_monitor.py

High‑level responsibilities
--------------------------
1. Poll the Solana mempool (via Helius `searchTransactions`) for programs that
   create liquidity pools on‑chain.
2. Detect the *first* time we see a tx signature that looks like a new pool
   initialisation (heuristic: instruction type contains the word "initialize").
3. Persist seen signatures so we never act twice on the same event.
4. Notify the caller (and Telegram, via `send_telegram_message`) when we spot
   something worth sniping.

Environment variables
---------------------
- HELIUS_API_KEY            – your Helius key (preferred)
- SOLANA_MEMPOOL_URL        – full custom endpoint. If *not* supplied we build
                              `https://mainnet.helius-rpc.com/?api-key=<key>`.
- DEX_PROGRAM_IDS           – comma‑separated list of AMM program IDs. If unset
                              we fall back to Raydium, Orca, Pump.fun.
- MEMPOOL_POLL_LIMIT        – how many txs per request (default 5).
- MEMPOOL_POLL_TIMEOUT      – HTTP timeout seconds (default 5).

The module exposes **check_mempool()** and a thin alias
**get_new_liquidity_pools()** for backward compatibility with existing import
statements in `monitor_and_trade.py`.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import requests
from requests.adapters import HTTPAdapter, Retry

from telegram_notifications import send_telegram_message

LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(message)s",
)

###############################################################################
# Configuration
###############################################################################

# --- Helius / RPC endpoint ---------------------------------------------------
DEFAULT_HELIUS_URL = "https://mainnet.helius-rpc.com/?api-key={key}"
_HELIUS_KEY = os.getenv("HELIUS_API_KEY")
SOLANA_MEMPOOL_URL = os.getenv(
    "SOLANA_MEMPOOL_URL",
    DEFAULT_HELIUS_URL.format(key=_HELIUS_KEY) if _HELIUS_KEY else None,
)
if not SOLANA_MEMPOOL_URL:
    raise RuntimeError(
        "❌  Set either SOLANA_MEMPOOL_URL or HELIUS_API_KEY in the environment"
    )

# --- Target AMM programs -----------------------------------------------------
DEX_PROGRAM_IDS: list[str] = (
    os.getenv(
        "DEX_PROGRAM_IDS",
        "rvHXrsyTrcRhTbkTJchfU3T9iU21WLCGMDu9zT4TuDw,"
        "nExF8aV2KXMo8bJpu9A4gQ2T2xnKxB9EdKmXKj7iCsN,"
        "8Y8n1xfkoEvXxBAaLw3mcQgw3m1ahdt9YrcmWZz5w5EZ",
    )
    .replace("\n", "")
    .split(",")
)
DEX_PROGRAM_IDS = [pid.strip() for pid in DEX_PROGRAM_IDS if pid.strip()]

# --- Request tuning ----------------------------------------------------------
POLL_LIMIT: int = int(os.getenv("MEMPOOL_POLL_LIMIT", 5))
HTTP_TIMEOUT: int = int(os.getenv("MEMPOOL_POLL_TIMEOUT", 5))

# --- Persistence -------------------------------------------------------------
SEEN_SIGNATURES_FILE = Path(os.getenv("SEEN_SIGNATURES_FILE", "seen_signatures.json"))
_MAX_SIGNATURES = 10_000  # rotate file after this many sigs to avoid bloat

if SEEN_SIGNATURES_FILE.exists():
    with SEEN_SIGNATURES_FILE.open() as fp:
        _SEEN_SIGNATURES: set[str] = set(json.load(fp))
else:
    _SEEN_SIGNATURES = set()


###############################################################################
# Helper utilities
###############################################################################

def _persist_seen_signatures() -> None:
    """Write signature cache to disk (truncating to the most recent N)."""
    if len(_SEEN_SIGNATURES) > _MAX_SIGNATURES:
        # Keep only the newest N (simple strategy: slice after sort by insertion)
        _trimmed = list(_SEEN_SIGNATURES)[-(_MAX_SIGNATURES // 2) :]
        _SEEN_SIGNATURES.clear()
        _SEEN_SIGNATURES.update(_trimmed)
    SEEN_SIGNATURES_FILE.write_text(json.dumps(list(_SEEN_SIGNATURES)))


def _http_session() -> requests.Session:
    """Return a requests session with sane retry/backoff."""
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


SESSION = _http_session()

###############################################################################
# Core logic
###############################################################################

def _fetch_recent_transactions(program_id: str) -> list[dict]:
    """Query Helius `searchTransactions` for a single program."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "searchTransactions",
        "params": {
            "query": f"accountKeys:{program_id}",
            "limit": POLL_LIMIT,
            "sort": "desc",
        },
    }

    response = SESSION.post(
        SOLANA_MEMPOOL_URL, json=payload, timeout=HTTP_TIMEOUT, headers={"Content-Type": "application/json"}
    )
    response.raise_for_status()
    return response.json().get("result", [])


def _looks_like_pool_initialisation(tx: dict) -> bool:
    """Heuristic: any instruction whose `parsedInstructionType` contains 'initialize'."""
    for ix in tx.get("instructions", []):
        if "initialize" in ix.get("parsedInstructionType", "").lower():
            return True
    return False


def check_mempool() -> Optional[str]:
    """Scan all configured AMM programs once.

    Returns
    -------
    str | None
        The **token mint address** of the first brand‑new liquidity pool we
        detect, else `None`.
    """
    LOGGER.debug("Scanning mempool via Helius…")

    for program_id in DEX_PROGRAM_IDS:
        try:
            transactions = _fetch_recent_transactions(program_id)
        except requests.RequestException as exc:
            LOGGER.warning("Helius request failed for %s: %s", program_id, exc)
            send_telegram_message(f"⚠️ Helius request failed for {program_id}: {exc}")
            continue

        for tx in transactions:
            sig = tx.get("signature")
            if not sig or sig in _SEEN_SIGNATURES:
                continue

            if _looks_like_pool_initialisation(tx):
                _SEEN_SIGNATURES.add(sig)
                _persist_seen_signatures()

                token_mint = (
                    tx.get("description", {})
                    .get("tokenTransfers", [{}])[0]
                    .get("mint", "Unknown")
                )
                LOGGER.info("🚀 Potential new pool: %s via %s", token_mint, program_id)
                send_telegram_message(
                    f"🚀 Mempool: New liquidity pool detected for token {token_mint}"
                )
                return token_mint

            # Mark signature as seen even if it wasn't an init to avoid re‑processing
            _SEEN_SIGNATURES.add(sig)

    _persist_seen_signatures()
    return None


# ---------------------------------------------------------------------------
# Backward‑compatibility alias
# ---------------------------------------------------------------------------

def get_new_liquidity_pools() -> Optional[str]:
    """Alias kept for legacy import paths (monitor_and_trade.py)."""
    return check_mempool()


###############################################################################
# Optional manual testing loop
###############################################################################

if __name__ == "__main__":
    LOGGER.info("Starting mempool monitor in standalone mode…")
    while True:
        pool = check_mempool()
        if pool:
            LOGGER.info("🔥 Found new liquidity pool: %s", pool)
        time.sleep(10)
