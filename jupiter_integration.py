import asyncio
import aiohttp
import base64
import json
import time
import logging
from typing import Dict, Optional, Any
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solders.transaction import VersionedTransaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jupiter_integration")

# Jupiter API endpoints
JUPITER_QUOTE_API = "https://quote-api.jup.ag/v6/quote"
JUPITER_SWAP_API = "https://quote-api.jup.ag/v6/swap"

# Solana token addresses
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_MINT = "Es9vMFrzaCERiE2dZVjW6M9T3cxLVRshzF5sgJnpPzM9"

class JupiterSwapper:
    """Jupiter DEX integration for Solana token swaps"""
    
    def __init__(self, rpc_client: Client, keypair: Keypair):
        self.client = rpc_client
        self.keypair = keypair
        self.wallet_address = str(keypair.pubkey())
        
    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50
    ) -> Optional[Dict[str, Any]]:
        """
        Get a quote from Jupiter for token swap
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address  
            amount: Amount in smallest unit (lamports/token units)
            slippage_bps: Slippage in basis points (50 = 0.5%)
            
        Returns:
            Quote data or None if failed
        """
        try:
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount),
                "slippageBps": str(slippage_bps),
                "onlyDirectRoutes": "false",
                "asLegacyTransaction": "false"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(JUPITER_QUOTE_API, params=params) as response:
                    if response.status == 200:
                        quote_data = await response.json()
                        logger.info(f"✅ Got Jupiter quote: {amount} → {quote_data.get('outAmount', 0)}")
                        return quote_data
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Jupiter quote failed ({response.status}): {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Jupiter quote error: {str(e)}")
            return None
    
    async def execute_swap(
        self,
        quote_data: Dict[str, Any],
        priority_fee_lamports: int = 1000
    ) -> Optional[str]:
        """
        Execute a swap using Jupiter
        
        Args:
            quote_data: Quote data from get_quote()
            priority_fee_lamports: Priority fee in lamports
            
        Returns:
            Transaction signature or None if failed
        """
        try:
            swap_request = {
                "quoteResponse": quote_data,
                "userPublicKey": self.wallet_address,
                "wrapAndUnwrapSol": True,
                "useSharedAccounts": True,
                "feeAccount": None,
                "computeUnitPriceMicroLamports": priority_fee_lamports,
                "asLegacyTransaction": False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    JUPITER_SWAP_API,
                    json=swap_request,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"❌ Jupiter swap request failed ({response.status}): {error_text}")
                        return None
                    
                    swap_response = await response.json()
                    
                    if "swapTransaction" not in swap_response:
                        logger.error(f"❌ No swapTransaction in response: {swap_response}")
                        return None
                    
                    # Deserialize and sign transaction
                    swap_transaction_buf = base64.b64decode(swap_response["swapTransaction"])
                    transaction = VersionedTransaction.from_bytes(swap_transaction_buf)
                    
                    # Sign transaction
                    transaction.sign([self.keypair])
                    
                    # Send transaction
                    signature = await self._send_transaction(transaction)
                    
                    if signature:
                        logger.info(f"✅ Swap executed! Signature: {signature}")
                        logger.info(f"🔗 View on Solscan: https://solscan.io/tx/{signature}")
                        return signature
                    else:
                        logger.error("❌ Failed to send swap transaction")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Jupiter swap execution error: {str(e)}")
            return None
    
    async def _send_transaction(self, transaction: VersionedTransaction) -> Optional[str]:
        """Send transaction to Solana network"""
        try:
            # Serialize transaction
            serialized_tx = base64.b64encode(transaction.serialize()).decode('ascii')
            
            # Send using RPC client
            response = self.client.send_transaction(
                transaction,
                TxOpts(skip_preflight=False, preflight_commitment="processed")
            )
            
            if hasattr(response, 'value'):
                signature = str(response.value)
                
                # Wait for confirmation
                await self._wait_for_confirmation(signature)
                return signature
            else:
                logger.error(f"❌ Transaction send failed: {response}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Transaction send error: {str(e)}")
            return None
    
    async def _wait_for_confirmation(self, signature: str, max_retries: int = 30):
        """Wait for transaction confirmation"""
        for i in range(max_retries):
            try:
                response = self.client.get_signature_statuses([signature])
                if response and response.value and response.value[0]:
                    status = response.value[0]
                    if status.confirmation_status:
                        logger.info(f"✅ Transaction confirmed: {signature}")
                        return True
                        
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.warning(f"⚠️ Confirmation check failed (attempt {i+1}): {str(e)}")
                await asyncio.sleep(2)
        
        logger.warning(f"⚠️ Transaction confirmation timeout: {signature}")
        return False
    
    async def buy_token_with_sol(
        self,
        token_mint: str,
        sol_amount: float,
        slippage_bps: int = 100
    ) -> Optional[str]:
        """
        Buy token with SOL
        
        Args:
            token_mint: Token mint address to buy
            sol_amount: Amount of SOL to spend
            slippage_bps: Slippage tolerance in basis points
            
        Returns:
            Transaction signature or None
        """
        try:
            # Convert SOL to lamports
            lamports = int(sol_amount * 1e9)
            
            logger.info(f"🛒 Buying {token_mint} with {sol_amount} SOL")
            
            # Get quote
            quote = await self.get_quote(SOL_MINT, token_mint, lamports, slippage_bps)
            if not quote:
                logger.error("❌ Failed to get quote for buy")
                return None
            
            # Execute swap
            signature = await self.execute_swap(quote)
            
            if signature:
                expected_tokens = int(quote.get("outAmount", 0))
                logger.info(f"✅ Buy successful! Expected tokens: {expected_tokens}")
                
            return signature
            
        except Exception as e:
            logger.error(f"❌ Buy token error: {str(e)}")
            return None
    
    async def sell_token_for_sol(
        self,
        token_mint: str,
        token_amount: int,
        slippage_bps: int = 100
    ) -> Optional[str]:
        """
        Sell token for SOL
        
        Args:
            token_mint: Token mint address to sell
            token_amount: Amount of tokens to sell (in token units)
            slippage_bps: Slippage tolerance in basis points
            
        Returns:
            Transaction signature or None
        """
        try:
            logger.info(f"📤 Selling {token_amount} units of {token_mint}")
            
            # Get quote
            quote = await self.get_quote(token_mint, SOL_MINT, token_amount, slippage_bps)
            if not quote:
                logger.error("❌ Failed to get quote for sell")
                return None
            
            # Execute swap
            signature = await self.execute_swap(quote)
            
            if signature:
                expected_sol = int(quote.get("outAmount", 0)) / 1e9
                logger.info(f"✅ Sell successful! Expected SOL: {expected_sol:.4f}")
                
            return signature
            
        except Exception as e:
            logger.error(f"❌ Sell token error: {str(e)}")
            return None
    
    def get_wallet_balance_sol(self) -> float:
        """Get SOL balance of wallet"""
        try:
            pubkey = self.keypair.pubkey()
            logger.info(f"Checking balance for: {str(pubkey)}")
            
            response = self.client.get_balance(pubkey)
            logger.info(f"Balance response: {response}")
            
            # Handle different response formats
            if hasattr(response, 'value'):
                lamports = response.value
                sol_balance = lamports / 1e9
                logger.info(f"✅ Balance: {lamports} lamports = {sol_balance:.6f} SOL")
                return sol_balance
            elif isinstance(response, dict) and 'result' in response:
                lamports = response['result']['value']
                sol_balance = lamports / 1e9
                logger.info(f"✅ Balance: {lamports} lamports = {sol_balance:.6f} SOL")
                return sol_balance
            else:
                logger.error(f"❌ Unexpected balance response format: {type(response)}")
                return 0.0
                
        except Exception as e:
            logger.error(f"❌ Balance check error: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return 0.0

# Convenience functions for easy integration
async def create_jupiter_swapper(rpc_url: str, keypair: Keypair) -> JupiterSwapper:
    """Create a Jupiter swapper instance"""
    client = Client(rpc_url)
    return JupiterSwapper(client, keypair)

# Testing function
async def test_jupiter_integration(rpc_url: str, keypair: Keypair):
    """Test Jupiter integration with small amounts"""
    logger.info("🧪 Testing Jupiter integration...")
    
    swapper = await create_jupiter_swapper(rpc_url, keypair)
    
    # Check balance
    balance = swapper.get_wallet_balance_sol()
    logger.info(f"💰 Wallet balance: {balance:.4f} SOL")
    
    if balance < 0.01:
        logger.error("❌ Insufficient balance for testing (need at least 0.01 SOL)")
        return False
    
    # Test small quote (0.001 SOL → USDC)
    quote = await swapper.get_quote(SOL_MINT, USDC_MINT, int(0.001 * 1e9), 100)
    
    if quote:
        expected_usdc = int(quote.get("outAmount", 0)) / 1e6  # USDC has 6 decimals
        logger.info(f"✅ Test quote successful: 0.001 SOL → {expected_usdc:.6f} USDC")
        return True
    else:
        logger.error("❌ Test quote failed")
        return False

if __name__ == "__main__":
    # This would be run for testing
    print("Jupiter Integration Module - Import this into your trading bot")
