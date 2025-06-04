from decrypt_config import decrypt_config_file
from encrypt_config import encrypt_config
import json

# Decrypt the config
config = decrypt_config_file()

# Show current key
print("OLD BirdEye key:", config['api_keys'].get('birdeye_api_key', 'NOT FOUND'))

# Update to the correct key
config['api_keys']['birdeye_api_key'] = '5e7294e4808a4e79ed4392a4510fd72'

# Show new key
print("NEW BirdEye key:", config['api_keys']['birdeye_api_key'])

# Re-encrypt and save
encrypt_config()
print("✅ Config updated and encrypted!")
