```python
"""mempool_monitor.py

High‑level responsibilities
--------------------------
1. Poll the Solana mempool (via Helius `searchTransactions`) for programs that
   create liquidity pools on‑chain.
2. Detect the *first* time we see a tx signature that looks like a new pool
   initialization (heuristic: instruction type contains the word "initialize").
3. Persist seen signatures so we never act twice on the same event.
4. Notify the caller and Telegram when we spot something worth sniping, safely
to avoid threading/asyncio conflicts.

Environment variables
---------------------
- HELIUS_API_KEY            – your Helius key (preferred)
- SOLANA_MEMPOOL_URL        – full custom endpoint. If *not* supplied we build
                              `https://mainnet.helius-rpc.com/?api-key=<key>`.
- DEX_PROGRAM_IDS           – comma‑separated list of AMM program IDs. If unset
                              we fall back to Raydium, Orca, Pump.fun.
- MEMPOOL_POLL_LIMIT        – how many txs per request (default 5).
- MEMPOOL_POLL_TIMEOUT      – HTTP timeout seconds (default 5).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

import requests
from requests.adapters import HTTPAdapter, Retry

from telegram_notifications import safe_send_telegram_message

# ─── logging setup ─────────────────────────────────────────────────────────
LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# ─── Helius / RPC endpoint detection ─────────────────────────────────────────
_HELIUS_KEY = os.getenv("HELIUS_API_KEY")
_DEFAULT_URL = (
    f"https://mainnet.helius-rpc.com/?api-key={_HELIUS_KEY}" if _HELIUS_KEY else None
)
SOLANA_MEMPOOL_URL = os.getenv("SOLANA_MEMPOOL_URL", _DEFAULT_URL)
if not SOLANA_MEMPOOL_URL:
    raise RuntimeError(
        "❌  Set HELIUS_API_KEY or SOLANA_MEMPOOL_URL in the environment."
    )

# ─── AMM program IDs (Raydium, Orca, Pump.fun default) ────────────────────
DEFAULT_PROGRAMS = (
    "rvHXrsyTrcRhTbkTJchfU3T9iU21WLCGMDu9zT4TuDw,"  # Raydium
    "nExF8aV2KXMo8bJpu9A4gQ2T2xnKxB9EdKmXKj7iCsN,"  # Orca
    "8Y8n1xfkoEvXxBAaLw3mcQgw3m1ahdt9YrcmWZz5w5EZ"   # Pump.fun
)
DEX_PROGRAM_IDS: List[str] = [
    pid.strip()
    for pid in os.getenv("DEX_PROGRAM_IDS", ",".join(DEFAULT_PROGRAMS)).split(",")
    if pid.strip()
]

# ─── request tuning ────────────────────────────────────────────────────────
POLL_LIMIT: int = int(os.getenv("MEMPOOL_POLL_LIMIT", 5))
HTTP_TIMEOUT: int = int(os.getenv("MEMPOOL_POLL_TIMEOUT", 5))

# ─── persistence for seen signatures ───────────────────────────────────────
SEEN_SIGNATURES_FILE = Path(os.getenv("SEEN_SIGNATURES_FILE", "seen_signatures.json"))
_MAX_SIGS = 10_000
if SEEN_SIGNATURES_FILE.exists():
    _SEEN_SIGS = set(json.loads(SEEN_SIGNATURES_FILE.read_text()))
else:
    _SEEN_SIGS = set()


def _persist_seen() -> None:
    """Write signature cache to disk (rotate when too large)."""
    if len(_SEEN_SIGS) > _MAX_SIGS:
        trimmed = list(_SEEN_SIGS)[-(_MAX_SIGS // 2):]
        _SEEN_SIGS.clear()
        _SEEN_SIGS.update(trimmed)
    SEEN_SIGNATURES_FILE.write_text(json.dumps(list(_SEEN_SIGS)))

# ─── resilient HTTP session ───────────────────────────────────────────────

def _session() -> requests.Session:
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    s = requests.Session()
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

SESSION = _session()

# ─── Telegram notify helper (thread‑safe) ─────────────────────────────────

def _notify(message: str) -> None:
    """
    Thread-safe wrapper to schedule our async Telegram send.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # schedule onto running loop
        asyncio.run_coroutine_threadsafe(
            safe_send_telegram_message(message), loop
        )
    else:
        # no loop or not running: run standalone
        asyncio.run(safe_send_telegram_message(message))

# ─── Core mempool scan ────────────────────────────────────────────────────

def _fetch_transactions(program_id: str) -> List[Dict[str, Any]]:
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
    resp = SESSION.post(
        SOLANA_MEMPOOL_URL,
        json=payload,
        timeout=HTTP_TIMEOUT,
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()
    return resp.json().get("result", [])


def _is_pool_init(tx: Dict[str, Any]) -> bool:
    for ix in tx.get("instructions", []):
        if "initialize" in ix.get("parsedInstructionType", "").lower():
            return True
    return False


def check_mempool() -> Optional[str]:
    """Return the mint of a new pool, else None."""
    for prog in DEX_PROGRAM_IDS:
        try:
            txs = _fetch_transactions(prog)
        except requests.RequestException as exc:
            LOGGER.warning("Helius request failed for %s: %s", prog, exc)
            _notify(f"⚠️ Helius request failed for {prog}: {exc}")
            continue

        for tx in txs:
            sig = tx.get("signature")
            if not sig or sig in _SEEN_SIGS:
                continue
            _SEEN_SIGS.add(sig)

            if not _is_pool_init(tx):
                continue

            _persist_seen()
            token_mint = (
                tx.get("description", {})
                .get("tokenTransfers", [{}])[0]
                .get("mint", "Unknown")
            )
            LOGGER.info("🚀 Pool init detected: %s via %s", token_mint, prog)
            _notify(
                f"🚀 Mempool: New liquidity pool detected for token {token_mint}"
            )
            return token_mint

    _persist_seen()
    return None


def get_new_liquidity_pools() -> Optional[str]:
    return check_mempool()

if __name__ == "__main__":
    LOGGER.info("Standalone mempool monitor – press Ctrl‑C to stop.")
    while True:
        mint = check_mempool()
        if mint:
            LOGGER.info("🔥 Found pool init for %s", mint)
        time.sleep(10)
```
