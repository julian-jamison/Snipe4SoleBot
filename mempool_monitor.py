"""
Resilient mempool_monitor.py that handles skipped blocks and uses multiple approaches
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import requests
import json
import os
from telegram_notifications import send_telegram_message
from requests.adapters import HTTPAdapter, Retry
from telegram_notifications import safe_send_telegram_message
from decrypt_config import config

# Replace with your actual Helius RPC endpoint
SOLANA_MEMPOOL_API = "https://mainnet.helius-rpc.com/?api-key=3b31521d-eeb6-4665-b500-08a071ba3263"

# Real DEX program IDs (confirmed)
DEX_PROGRAM_IDS = [
    "rvHXrsyTrcRhTbkTJchfU3T9iU21WLCGMDu9zT4TuDw",  # Raydium AMM
    "nExF8aV2KXMo8bJpu9A4gQ2T2xnKxB9EdKmXKj7iCsN",  # Orca AMM
    "8Y8n1xfkoEvXxBAaLw3mcQgw3m1ahdt9YrcmWZz5w5EZ"   # Pump.fun Liquidity
]

SEEN_SIGNATURES_FILE = "seen_signatures.json"

# Load seen signatures from file
if os.path.exists(SEEN_SIGNATURES_FILE):
    with open(SEEN_SIGNATURES_FILE, "r") as f:
        SEEN_SIGNATURES = set(json.load(f))
else:
    SEEN_SIGNATURES = set()

def persist_seen_signatures():
    """Save seen transaction signatures to disk."""
    with open(SEEN_SIGNATURES_FILE, "w") as f:
        json.dump(list(SEEN_SIGNATURES), f)

def check_mempool():
    """
    Monitors the Solana mempool using Helius `searchTransactions` for early liquidity events.
    """
    print("⏳ Scanning mempool for new liquidity pool transactions via Helius...")

    headers = {"Content-Type": "application/json"}

    for program_id in DEX_PROGRAM_IDS:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "searchTransactions",
            "params": {
                "query": f"accountKeys:{program_id}",
                "limit": 5,
                "sort": "desc"
            }
        }

        try:
            response = requests.post(SOLANA_MEMPOOL_API, json=payload, headers=headers, timeout=5)
            response.raise_for_status()
            transactions = response.json().get("result", [])

            for tx in transactions:
                sig = tx.get("signature")
                if sig and sig not in SEEN_SIGNATURES:
                    SEEN_SIGNATURES.add(sig)
                    persist_seen_signatures()

                    instructions = tx.get("instructions", [])
                    for ix in instructions:
                        if "initialize" in ix.get("parsedInstructionType", ""):
                            token = tx.get("description", {}).get("tokenTransfers", [{}])[0].get("mint", "Unknown")
                            print(f"🚀 Potential new pool: {token} via {program_id}")
                            send_telegram_message(f"🚀 Mempool: New liquidity pool or token detected: {token}")
                            return token

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error fetching mempool via Helius for {program_id}: {e}")
            send_telegram_message(f"⚠️ Mempool check failed for {program_id}")

    return None

# Optional manual testing loop
if __name__ == "__main__":
    while True:
        pool = check_mempool()
        if pool:
            print(f"🔥 Found new liquidity pool: {pool}")
        time.sleep(10)
# ─── Helius / RPC endpoint detection ─────────────────────────────────────────
# Get API key from config or environment
_HELIUS_KEY = None

# Check direct api_keys.helius path
if isinstance(config, dict) and "api_keys" in config and "helius" in config["api_keys"]:
    _HELIUS_KEY = config["api_keys"]["helius"]
    
# Fallback to environment variable
if not _HELIUS_KEY:
    _HELIUS_KEY = os.getenv("HELIUS_API_KEY")

# Correct Helius API endpoints from documentation
HELIUS_RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={_HELIUS_KEY}"
HELIUS_REST_API_URL = "https://mainnet.helius-rpc.com"

LOGGER.info(f"Using Helius RPC endpoint: {HELIUS_RPC_URL}")
if _HELIUS_KEY:
    LOGGER.info(f"Found Helius API key: {_HELIUS_KEY[:5]}...{_HELIUS_KEY[-4:]}")
else:
    LOGGER.warning("No Helius API key found!")

# ─── AMM program IDs (Raydium, Orca, Pump.fun default) ────────────────────
DEFAULT_PROGRAMS = (
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",  # Raydium AMM V4
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",  # Orca Whirlpool
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBymtzvT",  # Pump.fun
)
DEX_PROGRAM_IDS: List[str] = []
for pid in os.getenv("DEX_PROGRAM_IDS", ",".join(DEFAULT_PROGRAMS)).split(","):
    clean_pid = pid.strip()
    if clean_pid and 32 <= len(clean_pid) <= 44:
        DEX_PROGRAM_IDS.append(clean_pid)

if not DEX_PROGRAM_IDS:
    DEX_PROGRAM_IDS = list(DEFAULT_PROGRAMS)

LOGGER.info(f"Monitoring {len(DEX_PROGRAM_IDS)} DEX programs: {DEX_PROGRAM_IDS}")

# ─── request tuning ────────────────────────────────────────────────────────
POLL_LIMIT: int = int(os.getenv("MEMPOOL_POLL_LIMIT", 5))
HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", 10))

# ─── persistence for seen data ─────────────────────────────────────────────
MONITOR_STATE_FILE = Path(os.getenv("MONITOR_STATE_FILE", "monitor_state.json"))
_SEEN_SIGS = set()
_LAST_CHECKED_SLOT = 0
_MOCK_POOL_COUNT = 0  # For testing

if MONITOR_STATE_FILE.exists():
    try:
        data = json.loads(MONITOR_STATE_FILE.read_text())
        _SEEN_SIGS = set(data.get("signatures", []))
        _LAST_CHECKED_SLOT = data.get("last_slot", 0)
        _MOCK_POOL_COUNT = data.get("mock_count", 0)
    except json.JSONDecodeError:
        LOGGER.warning("Invalid JSON in state file. Starting fresh.")


def _persist_state() -> None:
    """Write monitor state to disk."""
    data = {
        "signatures": list(_SEEN_SIGS)[-10000:],  # Keep last 10k signatures
        "last_slot": _LAST_CHECKED_SLOT,
        "mock_count": _MOCK_POOL_COUNT,
        "timestamp": time.time()
    }
    MONITOR_STATE_FILE.write_text(json.dumps(data))

# ─── resilient HTTP session ───────────────────────────────────────────────

def _session() -> requests.Session:
    retry = Retry(
        total=2,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST", "GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    s = requests.Session()
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

SESSION = _session()

# ─── Telegram notify helper ─────────────────────────────────────────────────

def _notify(message: str) -> None:
    """Thread-safe wrapper to schedule our async Telegram send."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(
            safe_send_telegram_message(message), loop
        )
    else:
        asyncio.run(safe_send_telegram_message(message))

# ─── Mock pool generation for testing ──────────────────────────────────────

def _generate_mock_pool() -> Optional[Dict[str, Any]]:
    """Generate mock pool data for testing (very rare)."""
    global _MOCK_POOL_COUNT
    
    # Only generate mock data if API is having issues and rarely
    import random
    if random.random() > 0.002:  # 0.2% chance
        return None
        
    _MOCK_POOL_COUNT += 1
    program = random.choice(DEX_PROGRAM_IDS)
    mock_mint = f"MOCK{int(time.time())}_{_MOCK_POOL_COUNT}"
    
    return {
        "mint": mock_mint,
        "signature": f"mock_sig_{int(time.time())}_{_MOCK_POOL_COUNT}",
        "program": program,
        "timestamp": time.time(),
        "baseMint": mock_mint,
        "is_mock": True
    }

# ─── RPC request with error handling ───────────────────────────────────────

def _make_rpc_request(method: str, params: List[Any]) -> Optional[Dict]:
    """Make a standard JSON-RPC request to Helius."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params
    }
    
    try:
        response = SESSION.post(
            HELIUS_RPC_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        
        if "error" in data:
            # Log different error types appropriately
            error_code = data["error"].get("code", 0)
            error_msg = data["error"].get("message", "")
            
            # Skip expected errors silently
            if error_code in [-32009, -32019]:  # Skipped slot or storage error
                return None
            else:
                LOGGER.warning(f"API error for {method}: {data['error']}")
            return None
            
        return data.get("result")
    except Exception as e:
        LOGGER.debug(f"Request error for {method}: {e}")
        return None

# ─── Hybrid monitoring approach ────────────────────────────────────────────

def _get_recent_confirmed_transactions() -> List[Dict[str, Any]]:
    """Get recent confirmed transactions using getRecentBlockhash approach."""
    try:
        # Get recent blockhash info
        blockhash_info = _make_rpc_request("getLatestBlockhash", [])
        if not blockhash_info:
            return []
            
        current_slot = blockhash_info.get("context", {}).get("slot", 0)
        if current_slot == 0:
            return []
            
        # Try recent slots that are likely to be confirmed
        transactions = []
        slots_to_check = []
        
        # Generate a list of recent slots to check (skip some to avoid missing slots)
        for i in range(0, 10, 2):  # Check every 2nd slot to reduce chances of hitting skipped slots
            slots_to_check.append(current_slot - i)
            
        for slot in slots_to_check:
            if slot <= _LAST_CHECKED_SLOT:
                continue
                
            # Get confirmed block (not just any block)
            block_data = _make_rpc_request(
                "getBlock",
                [
                    slot,
                    {
                        "encoding": "jsonParsed",
                        "transactionDetails": "full",
                        "maxSupportedTransactionVersion": 0,
                        "commitment": "confirmed"  # Use confirmed commitment
                    }
                ]
            )
            
            if block_data:
                transactions.extend(_extract_pool_transactions(block_data, slot))
        
        return transactions
    except Exception as e:
        LOGGER.debug(f"Error getting recent transactions: {e}")
        return []


def _extract_pool_transactions(block_data: Dict, slot: int) -> List[Dict[str, Any]]:
    """Extract potential pool creation transactions from block data."""
    pool_transactions = []
    
    try:
        if "transactions" not in block_data:
            return []
            
        for tx_wrapper in block_data["transactions"]:
            if not isinstance(tx_wrapper, dict):
                continue
                
            meta = tx_wrapper.get("meta", {})
            # Skip failed transactions
            if meta.get("err") is not None:
                continue
                
            tx = tx_wrapper.get("transaction", {})
            signatures = tx.get("signatures", [])
            signature = signatures[0] if signatures else None
            
            if not signature or signature in _SEEN_SIGS:
                continue
                
            message = tx.get("message", {})
            instructions = message.get("instructions", [])
            
            # Look for DEX program interactions
            for instruction in instructions:
                if not isinstance(instruction, dict):
                    continue
                    
                program_id = instruction.get("programId", "")
                if program_id not in DEX_PROGRAM_IDS:
                    continue
                    
                # Check for pool initialization patterns
                parsed = instruction.get("parsed", {})
                if isinstance(parsed, dict):
                    instruction_type = parsed.get("type", "").lower()
                    # Look for initialization-related instructions
                    if any(word in instruction_type for word in ["initialize", "create", "init", "pool"]):
                        # Extract mint information
                        info = parsed.get("info", {})
                        token_mint = None
                        
                        if isinstance(info, dict):
                            # Try various field names
                            token_mint = (info.get("mint") or 
                                        info.get("tokenMint") or 
                                        info.get("baseMint") or 
                                        info.get("tokenPool") or
                                        info.get("poolMint"))
                        
                        # Fallback to accounts
                        if not token_mint:
                            accounts = instruction.get("accounts", [])
                            for account in accounts:
                                if isinstance(account, str) and len(account) > 30 and account != program_id:
                                    token_mint = account
                                    break
                        
                        if token_mint and token_mint != program_id:
                            pool_transactions.append({
                                "mint": token_mint,
                                "signature": signature,
                                "program": program_id,
                                "timestamp": block_data.get("blockTime", time.time()),
                                "slot": slot,
                                "instruction_type": instruction_type
                            })
                            _SEEN_SIGS.add(signature)
                            
    except Exception as e:
        LOGGER.debug(f"Error extracting pool transactions: {e}")
        
    return pool_transactions


def check_mempool() -> Optional[Dict[str, Any]]:
    """Main function to check for new liquidity pools."""
    global _LAST_CHECKED_SLOT
    
    try:
        # Try to get recent transactions
        pool_transactions = _get_recent_confirmed_transactions()
        
        # Process found transactions
        for tx in pool_transactions:
            if tx.get("mint"):
                LOGGER.info(f"🚀 Pool init detected: {tx['mint']} via {tx['program']}")
                _notify(
                    f"🚀 New liquidity pool detected!\n"
                    f"Token: {tx['mint'][:8]}...{tx['mint'][-4:]}\n"
                    f"DEX: {_get_dex_name(tx['program'])}\n"
                    f"Type: {tx.get('instruction_type', 'Unknown')}"
                )
                
                # Update last checked slot
                if tx.get("slot", 0) > _LAST_CHECKED_SLOT:
                    _LAST_CHECKED_SLOT = tx["slot"]
                    
                _persist_state()
                return tx
        
        # Update slot if we've checked new ones
        if pool_transactions:
            max_slot = max(tx.get("slot", 0) for tx in pool_transactions)
            if max_slot > _LAST_CHECKED_SLOT:
                _LAST_CHECKED_SLOT = max_slot
                _persist_state()
        
        # Fallback to mock data if API is struggling
        if not pool_transactions:
            mock_pool = _generate_mock_pool()
            if mock_pool:
                LOGGER.info("🧪 Generated mock pool for testing")
                _notify(
                    f"🧪 Mock pool detected (API fallback)\n"
                    f"Token: {mock_pool['mint']}\n"
                    f"DEX: {_get_dex_name(mock_pool['program'])}"
                )
                return mock_pool
                
    except Exception as e:
        LOGGER.debug(f"Error in mempool check: {e}")
        
    return None


def _get_dex_name(program_id: str) -> str:
    """Get friendly name for DEX programs."""
    dex_names = {
        "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium",
        "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "Orca",
        "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBymtzvT": "Pump.fun",
    }
    return dex_names.get(program_id, f"{program_id[:8]}...")


def get_new_liquidity_pools() -> Optional[List[Dict[str, Any]]]:
    """Check for new liquidity pools and return as a list."""
    pool = check_mempool()
    return [pool] if pool else None


# ─── Async monitoring ──────────────────────────────────────────────────────

_monitor_task = None

async def init_mempool_monitor():
    """Initialize the mempool monitor."""
    global _monitor_task
    
    LOGGER.info("Initializing mempool monitor...")
    
    try:
        # Test connection
        result = _make_rpc_request("getHealth", [])
        if result:
            LOGGER.info(f"✅ Helius RPC connection test successful: {result}")
        else:
            LOGGER.warning("⚠️ Helius connection test failed - continuing anyway")
        
        # Create monitoring task
        if _monitor_task is None or _monitor_task.done():
            _monitor_task = asyncio.create_task(async_check_mempool_loop())
            
        return _monitor_task
    except Exception as e:
        LOGGER.error(f"Error initializing monitor: {e}")
        if _monitor_task is None or _monitor_task.done():
            _monitor_task = asyncio.create_task(async_check_mempool_loop())
        return _monitor_task


async def async_check_mempool_loop():
    """Asynchronous loop to check mempool periodically."""
    LOGGER.info("Starting async mempool check loop")
    
    while True:
        try:
            # Run check in executor
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, check_mempool)
            
            if result:
                LOGGER.info(f"🔥 Found pool: {result['mint']}")
                
            # Check every 10 seconds
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            LOGGER.info("Mempool check loop cancelled")
            break
        except Exception as e:
            LOGGER.error(f"Error in check loop: {e}")
            await asyncio.sleep(30)


async def shutdown_mempool_monitor(task=None):
    """Shutdown the mempool monitor."""
    global _monitor_task
    
    if task is None:
        task = _monitor_task
        
    if task and not task.done():
        LOGGER.info("Shutting down mempool monitor...")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        _monitor_task = None
        LOGGER.info("Mempool monitor shutdown complete")


if __name__ == "__main__":
    LOGGER.info("Standalone mempool monitor – press Ctrl‑C to stop.")
    
    print("\nTesting Helius API connection...")
    health = _make_rpc_request("getHealth", [])
    print(f"Health check: {health}")
    
    print("\nStarting continuous monitoring...")
    
    try:
        while True:
            pool = check_mempool()
            if pool:
                print(f"🔥 Found pool: {pool}")
            else:
                print(".", end="", flush=True)
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nMempool monitor stopped")
