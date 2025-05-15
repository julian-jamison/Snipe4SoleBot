import logging
import asyncio
import aiohttp
from typing import List, Dict, Optional, Any
from solana.rpc.async_api import AsyncClient
from config_manager import load_decrypted_config

LOGGER = logging.getLogger(__name__)

# Known whale wallets to track
WHALE_WALLETS = {
    "5JQ8Mhdp2wv3HWcfjq9Ts8kwzCAeBADFBDAgBznzRsDF": "Whale 1",
    "3P3rpDXSYDQHgPZ4cTpkdpEnGhQamWVssWVng8JnPNe8": "Whale 2",
    # Add more whale wallets as needed
}

class WhaleTracker:
    """Track large wallet transactions on Solana."""
    
    def __init__(self, rpc_url: str):
        self.rpc_url = rpc_url
        self.client = AsyncClient(rpc_url)
        
    async def get_recent_transactions(self, wallet_address: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent transactions for a specific wallet."""
        try:
            # Get recent transaction signatures
            response = await self.client.get_signatures_for_address(
                wallet_address,
                limit=limit
            )
            
            if response.get("result"):
                signatures = response["result"]
                transactions = []
                
                # Fetch full transaction details for each signature
                for sig_info in signatures:
                    signature = sig_info["signature"]
                    tx_response = await self.client.get_transaction(
                        signature,
                        encoding="jsonParsed"
                    )
                    
                    if tx_response.get("result"):
                        transactions.append(tx_response["result"])
                
                return transactions
            
        except Exception as e:
            LOGGER.error(f"Error fetching transactions for {wallet_address}: {e}")
            
        return []
    
    async def analyze_transaction(self, transaction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze a transaction for potential trading opportunities."""
        try:
            # Extract transaction details
            tx_info = transaction.get("transaction", {})
            message = tx_info.get("message", {})
            instructions = message.get("instructions", [])
            
            # Look for DEX interactions
            for instruction in instructions:
                program_id = instruction.get("programId")
                
                # Check if this is a known DEX program
                if program_id in ["675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",  # Raydium
                                "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",  # Orca
                                "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBymtzvT"]: # Meteora
                    
                    parsed = instruction.get("parsed", {})
                    if parsed.get("type") in ["swap", "swapExactTokensForTokens"]:
                        # Extract swap details
                        info = parsed.get("info", {})
                        return {
                            "type": "swap",
                            "program": program_id,
                            "token_in": info.get("tokenIn"),
                            "token_out": info.get("tokenOut"),
                            "amount_in": info.get("amountIn"),
                            "amount_out": info.get("amountOut"),
                            "timestamp": transaction.get("blockTime")
                        }
                        
        except Exception as e:
            LOGGER.error(f"Error analyzing transaction: {e}")
            
        return None
    
    async def monitor_whale_activity(self) -> List[Dict[str, Any]]:
        """Monitor all whale wallets for recent activity."""
        all_transactions = []
        
        for wallet_address, whale_name in WHALE_WALLETS.items():
            LOGGER.info(f"Checking {whale_name} ({wallet_address})")
            
            # Get recent transactions
            transactions = await self.get_recent_transactions(wallet_address)
            
            # Analyze each transaction
            for tx in transactions:
                analysis = await self.analyze_transaction(tx)
                if analysis:
                    analysis["whale"] = whale_name
                    analysis["wallet"] = wallet_address
                    all_transactions.append(analysis)
        
        await self.client.close()
        return all_transactions


# Global whale tracker instance
whale_tracker = None

def initialize_whale_tracker():
    """Initialize the whale tracker with RPC URL from config."""
    global whale_tracker
    config = load_decrypted_config()
    rpc_url = config.get('api_keys', {}).get('solana_rpc_url', '')
    whale_tracker = WhaleTracker(rpc_url)

def get_whale_transactions():
    """Get recent whale transactions synchronously."""
    if not whale_tracker:
        initialize_whale_tracker()
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(whale_tracker.monitor_whale_activity())

async def get_whale_transactions_async():
    """Get recent whale transactions asynchronously."""
    if not whale_tracker:
        initialize_whale_tracker()
    
    return await whale_tracker.monitor_whale_activity()

def is_whale_wallet(address: str) -> bool:
    """Check if an address is a known whale wallet."""
    return address in WHALE_WALLETS
