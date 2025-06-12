"""
Enhanced configuration module for the Solana trading bot.
This module handles loading and decryption of sensitive configuration data,
with support for both key-based (Fernet) and password-based (AES-GCM) encryption.
"""
import os
import json
import base64
import getpass
import logging
from base64 import b64decode
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("decrypt_config")

# Configuration file paths
CONFIG_FILE = "config.json.encrypted"
ENCRYPTED_CONFIG_FILE = "config.encrypted"
KEY_FILE = "config.key"
PASSWORD_ENCRYPTED_FILE = "config.json.encrypted"

# Check which encryption method to use
USE_ENCRYPTED_CONFIG = os.path.exists(ENCRYPTED_CONFIG_FILE) and os.path.exists(KEY_FILE)
USE_PASSWORD_ENCRYPTION = os.path.exists(PASSWORD_ENCRYPTED_FILE)

# Environment variable for non-interactive mode
CONFIG_PASSWORD_ENV = "CONFIG_PASSWORD"

def derive_key(password, salt):
    """
    Derive an encryption key from a password using PBKDF2
    
    Args:
        password (str): Password to derive key from
        salt (bytes): Salt for key derivation
        
    Returns:
        bytes: Derived key
    """
    # Convert password to bytes if it's a string
    if isinstance(password, str):
        password = password.encode('utf-8')
    
    # Create a PBKDF2HMAC instance
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 32 bytes = 256 bits
        salt=salt,
        iterations=100000,
    )
    
    # Derive the key
    key = kdf.derive(password)
    
    return key

def decrypt_password_config(password=None):
    """
    Decrypt configuration file using password-based encryption
    
    Args:
        password (str, optional): Password for decryption. If None, prompts user or uses environment variable.
        
    Returns:
        dict: Decrypted configuration
    """
    try:
        # Read the encrypted file
        with open(PASSWORD_ENCRYPTED_FILE, 'r') as f:
            encrypted_data = json.load(f)
        
        # Get algorithm and encrypted data
        algorithm = encrypted_data.get("algorithm")
        if algorithm != "AES-GCM":
            logger.error(f"Unsupported encryption algorithm: {algorithm}")
            return None
        
        # Decode salt, nonce, and ciphertext
        salt = base64.b64decode(encrypted_data.get("salt"))
        nonce = base64.b64decode(encrypted_data.get("nonce"))
        ciphertext = base64.b64decode(encrypted_data.get("ciphertext"))
        
        # Get password
        if password is None:
            # Check for environment variable first
            if CONFIG_PASSWORD_ENV in os.environ:
                password = os.environ[CONFIG_PASSWORD_ENV]
                logger.info(f"Using password from environment variable {CONFIG_PASSWORD_ENV}")
            else:
                # Prompt user for password
                password = getpass.getpass("Enter configuration decryption password: ")
        
        # Derive key
        key = derive_key(password, salt)
        
        # Create AESGCM cipher
        aesgcm = AESGCM(key)
        
        # Decrypt the data
        try:
            decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
            
            # Parse JSON
            config_data = json.loads(decrypted_bytes.decode('utf-8'))
            
            logger.info("Successfully decrypted configuration using password")
            return config_data
            
        except Exception as e:
            logger.error(f"Failed to decrypt configuration: {e}")
            logger.error("This could be due to an incorrect password")
            return None
            
    except Exception as e:
        logger.error(f"Error reading encrypted file: {e}")
        return None

def decrypt_config_file():
    """Decrypt the encrypted config file using the key (Fernet method)."""
    try:
        # Read the key
        with open(KEY_FILE, "rb") as key_file:
            key = key_file.read()
        
        # Initialize the Fernet cipher
        cipher = Fernet(key)
        
        # Read the encrypted config
        with open(ENCRYPTED_CONFIG_FILE, "rb") as encrypted_file:
            encrypted_data = encrypted_file.read()
        
        # Decrypt the data
        decrypted_data = cipher.decrypt(encrypted_data)
        
        # Parse the JSON
        config_data = json.loads(decrypted_data.decode())
        
        logger.info("Successfully decrypted configuration using key file")
        return config_data
    
    except Exception as e:
        logger.error(f"Failed to decrypt configuration with key file: {e}")
        return None

def load_config(password=None):
    """
    Load the configuration from file.
    
    Args:
        password (str, optional): Password for decryption. If None, prompts user or uses environment variable.
        
    Returns:
        dict: Configuration data
    """
    config_data = None
    
    # Try password-based encryption first (most secure)
    if USE_PASSWORD_ENCRYPTION:
        config_data = decrypt_password_config(password)
        if config_data:
            return config_data
        logger.warning("Password-based decryption failed, trying alternatives")
    
    # Try key-based encryption next
    if USE_ENCRYPTED_CONFIG:
        config_data = decrypt_config_file()
        if config_data:
            return config_data
        logger.warning("Key-based decryption failed, trying alternatives")
    
    # Fall back to unencrypted config
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config_data = json.load(f)
            logger.info("Using unencrypted configuration file")
            return config_data
        else:
            logger.warning("Configuration file not found, using default config")
            return get_default_config()
    
    except FileNotFoundError:
        logger.warning("Configuration file not found, using default config")
        return get_default_config()
    except json.JSONDecodeError:
        logger.critical("Invalid JSON in configuration file")
        return get_default_config()
    except Exception as e:
        logger.critical(f"Error loading configuration: {e}")
        return get_default_config()

def get_default_config():
    """Return a minimal default configuration."""
    return {
        "telegram": {
            "bot_token": "",
            "chat_id": ""
        },
        "solana_wallets": {
            "signer_private_key": "",
            "wallet_1": "",
            "wallet_2": "",
            "wallet_3": "",
            "cold_wallet": ""
        },
        "api_keys": {
            "solana_rpc_url": "https://api.mainnet-beta.solana.com",
            "live_mode": False
        },
        "trade_settings": {
            "trade_cooldown": 30,
            "max_session_budget": 15,
            "allowed_tokens": [],
            "profit_target": 10,
            "stop_loss": -5,
            "dynamic_risk_management": {
                "volatility_threshold": 0.05,
                "min_stop_loss": -10,
                "max_stop_loss": -2,
                "min_profit_target": 5,
                "max_profit_target": 20
            }
        },
        "trend_following_tokens": [
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            "Es9vMFrzaCERiE2dZVjW6M9T3cxLVRshzF5sgJnpPzM9",  # USDT
            "So11111111111111111111111111111111111111112"    # SOL
        ]
    }

# Function to clean sensitive data from memory (for debugging/logging only)
def clean_sensitive_data(config_data):
    """Remove sensitive data from the configuration object for safe logging."""
    if not config_data or not isinstance(config_data, dict):
        return {}
    
    # Create a deep copy to avoid modifying the original
    import copy
    config_copy = copy.deepcopy(config_data)
    
    # Remove private keys
    if 'solana_wallets' in config_copy:
        wallets = config_copy['solana_wallets']
        if 'private_key_hex' in wallets:
            wallets['private_key_hex'] = '[REDACTED]'
        if 'signer_private_key' in wallets:
            wallets['signer_private_key'] = '[REDACTED]'
    
    # Remove API keys
    if 'api_keys' in config_copy:
        api_keys = config_copy['api_keys']
        if 'birdeye_api_key' in api_keys:
            api_keys['birdeye_api_key'] = '[REDACTED]'
    
    return config_copy

# Export the configuration - IMPORTANT: Use the original, not sanitized version
config = load_config()

# Create a separate safe version for debugging (but don't use this as the main config)
_safe_config_for_debugging = clean_sensitive_data(config.copy() if config else None)

# For testing
if __name__ == "__main__":
    print("Configuration loaded successfully!")
    if config:
        print(f"Telegram bot configured: {'Yes' if config.get('telegram', {}).get('bot_token') else 'No'}")
        print(f"Number of wallets: {len([k for k in config.get('solana_wallets', {}).keys() if k.startswith('wallet_')])}")
        print(f"Trading in live mode: {'Yes' if config.get('api_keys', {}).get('live_mode') else 'No'}")
        
        # Print safe version of config for debugging
        print("\nSafe configuration (sensitive data redacted):")
        print(json.dumps(_safe_config_for_debugging, indent=2))
    else:
        print("❌ Failed to load configuration")
