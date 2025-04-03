from Crypto.Cipher import AES
import json
import base64
import os

raw_key = os.environ.get("CONFIG_ENCRYPTION_KEY")
if not raw_key:
    raise EnvironmentError("❌ CONFIG_ENCRYPTION_KEY is not set in the environment.")
ENCRYPTION_KEY = base64.urlsafe_b64decode(raw_key)

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

# ✅ Now it's safe to call the function:
config = decrypt_config()
