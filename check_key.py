from decrypt_config import config
print("Current BirdEye key:", config['api_keys'].get('birdeye_api_key', 'NOT FOUND')
print("Key length:", len(str(config['api_keys'].get('birdeye_api_key', ''))))
