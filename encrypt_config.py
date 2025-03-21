from Crypto.Cipher import AES
import json
import base64
import os

ENCRYPTION_KEY = os.getenv("CONFIG_ENCRYPTION_KEY").encode().ljust(32, b'\0')
CONFIG_FILE = "config.json"
ENCRYPTED_FILE = "config.enc"

def encrypt_config():
    """Encrypts config.json and saves as config.enc."""
    if not os.path.exists(CONFIG_FILE):
        print("❌ config.json not found. Aborting encryption.")
        return

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
    print("🛑 Unencrypted config.json has been deleted for security purposes.")

encrypt_config()
