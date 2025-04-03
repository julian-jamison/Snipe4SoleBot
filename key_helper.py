import json
import os
import argparse
import binascii
from solders.keypair import Keypair

CONFIG_PATH = "config.json"

def generate_keypair():
    kp = Keypair()
    signer_key_hex = kp.to_bytes().hex()
    pubkey = str(kp.pubkey())

    print("🔐 Public Key:", pubkey)
    print("🔑 signer_private_key (hex):", signer_key_hex)

    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
    else:
        config = {}

    config.setdefault("solana_wallets", {})
    config["solana_wallets"]["signer_private_key"] = signer_key_hex

    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    print(f"✅ signer_private_key saved to {CONFIG_PATH}")

def validate_key(hex_key):
    try:
        key_bytes = bytes.fromhex(hex_key)
        length = len(key_bytes)

        if length not in [32, 64]:
            print(f"❌ Invalid key length: {length} bytes. Must be 32 or 64 bytes.")
            return

        if length == 64:
            kp = Keypair.from_bytes(key_bytes)
        else:  # 32-byte seed
            kp = Keypair.from_seed(key_bytes)

        print("✅ Key is valid.")
        print("🔐 Public Key:", kp.pubkey())

    except binascii.Error:
        print("❌ Provided key is not valid hex.")
    except Exception as e:
        print(f"❌ Key validation failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate or validate a Solana signer key.")
    parser.add_argument("--generate", action="store_true", help="Generate a new signer key and save to config.json")
    parser.add_argument("--validate", type=str, help="Validate a hex private key string.")

    args = parser.parse_args()

    if args.generate:
        generate_keypair()
    elif args.validate:
        validate_key(args.validate)
    else:
        parser.print_help()
