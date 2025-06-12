import time, json, base64, logging, asyncio, threading, requests, base58
from datetime import datetime

MOCK_MODE = False
LIVE_MODE = False
try:
    from decrypt_config import config
except ImportError:
    config = {}

# Check live mode
if config and "api_keys" in config and config["api_keys"].get("live_mode"):
    LIVE_MODE = True

try:
    from solders.pubkey import Pubkey as PublicKey
    from solders.keypair import Keypair
    from solana.rpc.api import Client
    from solana.rpc.types import TxOpts
    from solana.transaction import Transaction
    from solders.system_program import ID as SYS_PROGRAM_ID
    COMMITMENT_CONFIRMED = "confirmed"
    logging.info("Using solders-based imports")
except ImportError as e:
    try:
        from solana.rpc.api import Client
        from solana.rpc.types import TxOpts
        try:
            from solana.rpc.commitment import Commitment
            COMMITMENT_CONFIRMED = Commitment.confirmed
        except (ImportError, AttributeError):
            from solana.rpc.commitment import Confirmed
            COMMITMENT_CONFIRMED = Confirmed
        from solana.transaction import Transaction
        from solana.keypair import Keypair
        from solana.publickey import PublicKey
        from solana.system_program import SYS_PROGRAM_ID
        logging.info("Using classic solana imports")
    except ImportError:
        if LIVE_MODE:
            logging.critical("CRITICAL: Solana SDK not available in LIVE MODE. Aborting.")
            raise SystemExit("Solana SDK required for live trading")
        MOCK_MODE = True
        logging.warning("Solana SDK missing – MOCK MODE enabled (dev/test only)")

try:
    from spl.token.constants import ASSOCIATED_TOKEN_PROGRAM_ID
    ATA_PROGRAM_ID = ASSOCIATED_TOKEN_PROGRAM_ID
except ImportError:
    ATA_PROGRAM_ID = PublicKey("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")

try:
    from telegram_notifications import send_telegram_message_async
except ImportError:
    async def send_telegram_message_async(msg): print(f"MOCK TELEGRAM: {msg}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sol_real_trader")

JUPITER_AGGREGATOR_PROGRAM_ID = "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB"
RAYDIUM_AMM_PROGRAM_ID      = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
ORCA_SWAP_PROGRAM_ID        = "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP"

class MockSolanaClient:
    def get_version(self): return {"result": {"solana-core": "mock"}}
    def get_balance(self, _): return {"result": {"value": 5_000_000_000}}
    def get_token_accounts_by_owner(self, *_): return {"result": {"value": []}}
    def get_token_account_balance(self, *_):
        return {"result": {"value": {"amount": "100000000", "decimals": 6, "uiAmount": 100}}}
    def confirm_transaction(self, _): return {"result": {"value": True}}
    def send_transaction(self, *_): return {"result": "MOCK_SIG"}
    def get_slot(self): return {"result": 123456789}

class SolanaRealTrader:
    def __init__(self):
        self.config = config
        self._enforce_mode()
        self.load_config()
        self.setup_connections()
        self.processed_pools = set()
        self.active_trades = set()
        self.running = True

    def _enforce_mode(self):
        if LIVE_MODE and MOCK_MODE:
            logger.critical("Tried to enter mock mode in live trading! Aborting.")
            raise SystemExit("Mock mode not allowed in live trading.")
        elif MOCK_MODE:
            logger.warning("MOCK mode enabled (test/dev only)")

    def load_config(self):
        t = self.config.get("trade_settings", {})
        self.wallets = self.config.get("solana_wallets", {})
        self.cold_wallet = self.wallets.get("cold_wallet")
        self.min_liquidity = float(t.get("min_liquidity", 1000)
        self.profit_target = float(t.get("profit_target", 10))
        self.stop_loss = float(t.get("stop_loss", -5)
        self.slippage_bps = int(t.get("slippage_bps", 100)
        # -- Key selection --
        self.keypair = self._load_private_key()

    def _load_private_key(self):
        pk_hex = self.wallets.get("private_key_hex") or self.wallets.get("private_key")
        if not pk_hex:
            logger.critical("No private key in config! Cannot run real trading.")
            raise SystemExit("No private key found in config.")
        pk_hex = pk_hex.strip().replace(" ", "")
        if pk_hex.startswith("[") and pk_hex.endswith("]"):
            pk_hex = pk_hex[1:-1].replace(",", "").replace(" ", "")
        # Defensive: must be exactly 64 hex chars (32 bytes)
        if len(pk_hex) != 64:
            logger.critical(f"Private key hex must be 64 characters (got {len(pk_hex)}): {pk_hex!r}")
            raise SystemExit("Private key not valid hex: must be 64 hex chars (32 bytes for Solana)")
        try:
            key_bytes = bytes.fromhex(pk_hex)
            if len(key_bytes) != 32:
                logger.critical(f"Decoded private key wrong length: {len(key_bytes)} (expected 32)")
                raise SystemExit("Private key must decode to 32 bytes for Solana keypair")
            logger.info("Private key: type=hex, length=64 (decoded 32 bytes)")
            kp = Keypair(key_bytes)
            logger.info("Private key loaded for live trading.")
            return kp
        except Exception as e:
            logger.critical(f"Failed to load keypair from private key: {e}")
            raise SystemExit("Failed to create Keypair from private key.")

    def setup_connections(self):
        if LIVE_MODE:
            rpc_url = self.config["api_keys"].get("solana_rpc_url")
            logger.info(f"Connecting to SOLANA RPC (REAL): {rpc_url}")
            self.client = Client(rpc_url)
            # Test connection
            try:
                version_info = self.client.get_version()
                logger.info(f"✅ Solana RPC connection OK: {version_info}")
            except Exception as e:
                logger.critical(f"Solana RPC failed: {e}")
                raise SystemExit("No RPC, cannot trade live.")
        else:
            self.client = MockSolanaClient()
            logger.info("Using mock Solana client.")

    def buy_token(self, mint, amount_sol, *args, **kwargs):
        if not LIVE_MODE:
            logger.info(f"MOCK BUY: {amount_sol} SOL of {mint[:8]}")
            return {"success": True, "tx_id": f"MOCK_TX_{int(time.time()}", "amount": amount_sol * 1000}
        logger.info(f"REAL BUY: {amount_sol} SOL of {mint[:8]}")
        # (TODO) Add real buy logic here
        return {"success": True, "tx_id": "TODO_REAL_TX", "amount": amount_sol * 1000}

    def sell_token(self, mint, amount, *args, **kwargs):
        if not LIVE_MODE:
            logger.info(f"MOCK SELL: {amount} {mint[:8]}")
            return {"success": True, "tx_id": f"MOCK_TX_{int(time.time()}", "amount_sol": amount / 1000}
        logger.info(f"REAL SELL: {amount} of {mint[:8]}")
        # (TODO) Add real sell logic here
        return {"success": True, "tx_id": "TODO_REAL_TX", "amount_sol": amount / 1000}

# Helper for integration
def get_real_trader():
    return SolanaRealTrader()

