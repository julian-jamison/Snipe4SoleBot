from Crypto.Cipher import AES
import json
import base64
import os

ENCRYPTION_KEY = os.getenv("CONFIG_ENCRYPTION_KEY").encode().ljust(32, b'\0')
CONFIG_FILE = "config.json"
ENCRYPTED_FILE = "config.enc"

def decrypt_config():
    """Decrypts config.enc and restores config.json."""
    if not os.path.exists(ENCRYPTED_FILE):
        print("❌ Encrypted config file not found. Aborting decryption.")
        return

    with open(ENCRYPTED_FILE, "r") as f:
        encrypted_data = json.load(f)

    cipher = AES.new(ENCRYPTION_KEY, AES.MODE_EAX, nonce=base64.b64decode(encrypted_data["nonce"]))
    decrypted_text = cipher.decrypt_and_verify(
        base64.b64decode(encrypted_data["ciphertext"]),
        base64.b64decode(encrypted_data["tag"])
    )

    with open(CONFIG_FILE, "w") as f:
        f.write(decrypted_text.decode())
    
    print("✅ Configuration file decrypted successfully.")

decrypt_config()