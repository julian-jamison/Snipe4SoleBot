from Crypto.Cipher import AES
import json
import base64
import os

ENCRYPTION_KEY = os.getenv("CONFIG_ENCRYPTION_KEY").encode().ljust(32, b'\0')

def decrypt_config():
    """Decrypts config.enc and returns config data."""
    with open("config.enc", "r") as f:
        encrypted_data = json.load(f)

    cipher = AES.new(
        ENCRYPTION_KEY,
        AES.MODE_EAX,
        nonce=base64.b64decode(encrypted_data["nonce"])
    )
    decrypted_text = cipher.decrypt_and_verify(
        base64.b64decode(encrypted_data["ciphertext"]),
        base64.b64decode(encrypted_data["tag"])
    )
    return json.loads(decrypted_text.decode())

# ✅ This line makes the config accessible in other scripts
config = decrypt_config()

# Optional log (can be removed in production)
print("✅ Configuration Decrypted:", config)
