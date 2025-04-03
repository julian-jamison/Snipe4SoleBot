import json
import argparse
import base64
import os
from solders.keypair import Keypair

CONFIG_FILE = "config.json"
ENCRYPTED_FILE = "config.enc"

def generate_keypair():
    kp = Keypair()
    signer_key_hex = kp.as_bytes().hex()

    print(f"✅ Generated signer key:\n{signer_key_hex}")
    print(f"🔒 Updating {CONFIG_FILE} with signer_private_key...")

    if not os.path.exists(CONFIG_FILE):
        print(f"❌ {CONFIG_FILE} does not exist. Create it first.")
        return

    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

    config.setdefault("solana_wallets", {})["signer_private_key"] = signer_key_hex

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    print("🔐 Encrypting updated config.json...")
    encrypt_config()

def encrypt_config():
    from Crypto.Cipher import AES

    raw_key = os.environ.get("CONFIG_ENCRYPTION_KEY")
    if not raw_key:
        raise EnvironmentError("❌ CONFIG_ENCRYPTION_KEY is not set in the environment.")
    ENCRYPTION_KEY = base64.urlsafe_b64decode(raw_key)

    with open(CONFIG_FILE, "r") as f:
        plaintext = f.read()

    cipher = AES.new(ENCRYPTION_KEY, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode())

    encrypted_data = {
        "nonce": base64.b64encode(cipher.nonce).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "tag": base64.b64encode(tag).decode()
    }

    with open(ENCRYPTED_FILE, "w") as f:
        json.dump(encrypted_data, f)

    print("✅ Configuration file encrypted successfully.")
    os.remove(CONFIG_FILE)
    print("🛑 Unencrypted config.json has been deleted for security.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true", help="Generate a new Solana keypair and encrypt config")
    args = parser.parse_args()

    if args.generate:
        generate_keypair()
