import json
import logging
import os
from decrypt_config import config

LOGGER = logging.getLogger(__name__)

def load_decrypted_config():
    """Load the decrypted configuration."""
    try:
        # The config is already loaded and decrypted in decrypt_config.py
        return config
    except Exception as e:
        LOGGER.error(f"Error loading decrypted config: {e}")
        # Return a default config to prevent crashes
        return {
            'solana_wallets': {},
            'telegram': {},
            'trade_settings': {},
            'api_keys': {}
        }

def get_config_value(key_path, default=None):
    """Get a config value using dot notation (e.g., 'api_keys.live_mode')."""
    config = load_decrypted_config()
    keys = key_path.split('.')
    value = config
    
    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default

def update_config_value(key_path, value):
    """Update a config value (note: this doesn't persist to file)."""
    config = load_decrypted_config()
    keys = key_path.split('.')
    current = config
    
    try:
        for key in keys[:-1]:
            current = current[key]
        current[keys[-1]] = value
        return True
    except (KeyError, TypeError):
        LOGGER.error(f"Failed to update config value: {key_path}")
        return False

def reload_config():
    """Reload the configuration from file."""
    # This would need to be implemented if you want to reload
    # the config during runtime
    pass

# Aliases for backward compatibility
get_config_setting = get_config_value
save_config_setting = update_config_value
