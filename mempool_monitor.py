# Import statements
import asyncio
import json
import logging
import os
import time
from typing import List, Dict, Optional, Any
import aiohttp
import base64
from solana.rpc.core import RPCException
from tenacity import retry, stop_after_attempt, wait_exponential
from config_manager import load_decrypted_config
from telegram_notifications import send_telegram_message_async

# Initialize logger first
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

def get_helius_api_key():
    """Extract Helius API key from the RPC URL."""
    config = load_decrypted_config()
    rpc_url = config.get('api_keys', {}).get('solana_rpc_url', '')
    
    # Extract API key from URL
    if 'api-key=' in rpc_url:
        api_key = rpc_url.split('api-key=')[-1]
        if '&' in api_key:
            api_key = api_key.split('&')[0]
        return api_key
    return None

def get_helius_rpc_url():
    """Get the Helius RPC URL from config."""
    config = load_decrypted_config()
    return config.get('api_keys', {}).get('solana_rpc_url', '')

# Get configuration
HELIUS_API_KEY = get_helius_api_key()
HELIUS_RPC_URL = get_helius_rpc_url()

# Log the RPC URL being used
LOGGER.info(f"Using Helius RPC endpoint: {HELIUS_RPC_URL}")

# Log the API key for debugging (only first few characters)
if HELIUS_API_KEY:
    LOGGER.info(f"Found Helius API key: {HELIUS_API_KEY[:5]}...{HELIUS_API_KEY[-4:]}")
else:
    LOGGER.warning("No Helius API key found in RPC URL")

# Helius WebSocket URL
HELIUS_WS_URL = f"wss://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# DEX programs to monitor
DEX_PROGRAMS = {
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "Raydium LP V4",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "Orca",
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBymtzvT": "Meteora"
}

LOGGER.info(f"Monitoring {len(DEX_PROGRAMS)} DEX programs: {list(DEX_PROGRAMS.keys()}")

SOLANA_NATIVE_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_MINT = "Es9vMFrzaCERiE2dZVjW6M9T3cxLVRshzF5sgJnpPzM9"

# Known honeypot tokens to avoid
HONEYPOT_TOKENS = {
    "7atgF8KQo4wJrD5ATGX7t1V2zVvykPJbFfNeVf1icFv1",  # Known scam token
    # Add more as discovered
}

# Token blacklist (e.g., known scams, honeypots)
TOKEN_BLACKLIST = {
    'ANvDJgYvf8nHyMYbKBBkL34gR5p8nfcZVB5JFGyELrQE',  # Example blacklisted token
    'D8cy77BBepLMngZx6ZukaTff5hCt1HrWyKk3Hnd9oitf',  # SafeMoon V2
    # Add more blacklisted tokens here
}

class MempoolMonitor:
    """WebSocket-based mempool monitor for Solana using Helius."""
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize the mempool monitor."""
        self.session = session
        self.latest_blockhash = None
        self.websocket = None
        self.is_connected = False
        
        # Initialize Helius connection
        LOGGER.info("Initializing mempool monitor...")
        if self._test_helius_connection():
            LOGGER.info("✅ Helius RPC connection test successful")
        else:
            LOGGER.error("❌ Failed to connect to Helius RPC")
    
    def _test_helius_connection(self) -> bool:
        """Test the Helius RPC connection."""
        try:
            import requests
            headers = {"Content-Type": "application/json"}
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getHealth"
            }
            
            response = requests.post(HELIUS_RPC_URL, headers=headers, json=payload, timeout=5)
            result = response.json()
            
            if result.get("result") == "ok":
                LOGGER.info("✅ Helius RPC connection test successful: %s", result.get("result")
                return True
            else:
                LOGGER.error("❌ Helius RPC health check failed: %s", result)
                return False
                
        except Exception as e:
            LOGGER.error("❌ Failed to test Helius connection: %s", str(e)
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    async def connect_websocket(self):
        """Connect to Helius WebSocket with retry logic."""
        try:
            self.websocket = await self.session.ws_connect(
                HELIUS_WS_URL,
                heartbeat=30,
                timeout=60
            )
            self.is_connected = True
            LOGGER.info("✅ Connected to Helius WebSocket")
            
            # Subscribe to all DEX programs
            await self._subscribe_to_programs()
            
        except Exception as e:
            self.is_connected = False
            LOGGER.error(f"❌ Failed to connect to WebSocket: {str(e)}")
            raise
    
    async def _subscribe_to_programs(self):
        """Subscribe to program accounts for all DEX programs."""
        for program_id, program_name in DEX_PROGRAMS.items():
            subscribe_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "programSubscribe",
                "params": [
                    program_id,
                    {
                        "encoding": "jsonParsed",
                        "commitment": "confirmed"
                    }
                ]
            }
            
            await self.websocket.send_json(subscribe_msg)
            LOGGER.info(f"📡 Subscribed to {program_name} ({program_id})")
    
    async def start_monitoring(self, callback):
        """Start monitoring the mempool via WebSocket."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            await self.connect_websocket()
            
            async for msg in self.websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        if "params" in data:
                            await self._process_transaction(data["params"], callback)
                    except json.JSONDecodeError:
                        LOGGER.error(f"Failed to decode message: {msg.data}")
                        
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    LOGGER.error(f'WebSocket error: {self.websocket.exception()}')
                    
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    LOGGER.warning("WebSocket connection closed")
                    break
                    
        except Exception as e:
            LOGGER.error(f"Error in WebSocket monitoring: {str(e)}")
        finally:
            if self.websocket and not self.websocket.closed:
                await self.websocket.close()
            self.is_connected = False
    
    async def _process_transaction(self, params: Dict[str, Any], callback):
        """Process a transaction from the WebSocket stream."""
        try:
            result = params.get("result", {})
            value = result.get("value", {})
            
            # Get transaction data
            slot = value.get("slot")
            signature = value.get("signature")
            
            # Get account updates
            account_data = value.get("account", {})
            parsed_data = account_data.get("data", {}).get("parsed", {})
            
            # Check if this is a liquidity pool creation
            if self._is_liquidity_pool_creation(parsed_data):
                pool_info = self._extract_pool_info(parsed_data, signature)
                if pool_info:
                    LOGGER.info(f"🎯 New liquidity pool detected: {pool_info}")
                    await callback(pool_info)
                    
        except Exception as e:
            LOGGER.error(f"Error processing transaction: {str(e)}")
    
    def _is_liquidity_pool_creation(self, parsed_data: Dict[str, Any]) -> bool:
        """Check if the transaction creates a new liquidity pool."""
        try:
            info = parsed_data.get("info", {})
            instruction_type = parsed_data.get("type", "")
            
            # Check for different DEX pool creation patterns
            if instruction_type in ["initializePool", "createPool", "initialize"]:
                return True
                
            # Check for token mints that might indicate a new pool
            if "mintA" in info and "mintB" in info:
                return True
                
            return False
            
        except Exception as e:
            LOGGER.error(f"Error checking pool creation: {str(e)}")
            return False
    
    def _extract_pool_info(self, parsed_data: Dict[str, Any], signature: str) -> Optional[Dict[str, Any]]:
        """Extract pool information from parsed transaction data."""
        try:
            info = parsed_data.get("info", {})
            
            # Extract token mints
            token_a = info.get("mintA", info.get("tokenMintA")
            token_b = info.get("mintB", info.get("tokenMintB")
            
            if not token_a or not token_b:
                return None
            
            # Extract pool address if available
            pool_address = info.get("poolAddress", info.get("account", signature)
            
            return {
                "pool_address": pool_address,
                "token_a": token_a,
                "token_b": token_b,
                "created_at": time.time(),
                "signature": signature
            }
            
        except Exception as e:
            LOGGER.error(f"Error extracting pool info: {str(e)}")
            return None
    
    async def get_pool_info_http(self, pool_address: str) -> Optional[Dict[str, Any]]:
        """Get pool information via HTTP RPC call."""
        try:
            headers = {"Content-Type": "application/json"}
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [
                    pool_address,
                    {
                        "encoding": "jsonParsed",
                        "commitment": "confirmed"
                    }
                ]
            }
            
            async with self.session.post(HELIUS_RPC_URL, headers=headers, json=payload) as response:
                result = await response.json()
                
                if "error" in result:
                    LOGGER.error(f"RPC error getting pool info: {result['error']}")
                    return None
                
                account_data = result.get("result", {}).get("value", {})
                if not account_data:
                    return None
                
                parsed_data = account_data.get("data", {}).get("parsed", {})
                return self._extract_pool_info(parsed_data, pool_address)
                
        except Exception as e:
            LOGGER.error(f"Error getting pool info via HTTP: {str(e)}")
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    async def _get_recent_blockhash(self):
        """Get recent blockhash with retry."""
        headers = {"Content-Type": "application/json"}
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getLatestBlockhash",
            "params": [{"commitment": "finalized"}]
        }
        
        async with self.session.post(HELIUS_RPC_URL, headers=headers, json=payload) as response:
            result = await response.json()
            if "error" in result:
                raise Exception(f"RPC Error: {result['error']}")
            
            blockhash_info = result.get("result", {}).get("value", {})
            return blockhash_info.get("blockhash")

# Legacy function for backward compatibility
def get_new_liquidity_pools():
    """Legacy function - now returns empty list as we use WebSocket monitoring."""
    return []

# Async function to check for new pools
async def check_new_pools_async():
    """Async function to check for new pools via WebSocket."""
    monitor = MempoolMonitor()
    pools = []
    
    async def pool_callback(pool_info):
        pools.append(pool_info)
    
    # Run for a short time to collect any new pools
    try:
        await asyncio.wait_for(
            monitor.start_monitoring(pool_callback),
            timeout=5.0
        )
    except asyncio.TimeoutError:
        pass
    
    return pools

# Synchronous wrapper for async function
def check_new_pools():
    """Check for new pools synchronously."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(check_new_pools_async()
import time
import requests

SOLANA_MEMPOOL_API = "https://api.solana.com/mempool"  # Placeholder, replace with a real API if available

def check_mempool():
    """Monitors the Solana mempool for early trade execution opportunities."""
    print("⏳ Scanning mempool for new liquidity pools...")

    try:
        response = requests.get(SOLANA_MEMPOOL_API)
        response.raise_for_status()
        mempool_data = response.json()

        for transaction in mempool_data.get("transactions", []):
            if transaction.get("type") == "liquidity_pool_creation":
                print(f"🚀 New liquidity pool detected: {transaction['token_address']}")
                return transaction["token_address"]
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error accessing mempool: {e}")

    return None  # No new pools detected

# Example call
if __name__ == "__main__":
    while True:
        pool = check_mempool()
        if pool:
            print(f"🔥 Liquidity Pool Found: {pool}")
        time.sleep(5)  # Check mempool every 5 seconds
