from Crypto.Cipher import AES
import json
import base64
import os

raw_key = os.environ.get("CONFIG_ENCRYPTION_KEY")
if not raw_key:
    raise EnvironmentError("❌ CONFIG_ENCRYPTION_KEY is not set in the environment.")
ENCRYPTION_KEY = base64.urlsafe_b64decode(raw_key)

with open("config.enc", "r") as f:
    encrypted_data = json.load(f)

key = base64.urlsafe_b64decode(os.environ["CONFIG_ENCRYPTION_KEY"])
cipher = AES.new(key, AES.MODE_EAX, nonce=base64.b64decode(encrypted_data["nonce"]))

decrypted = cipher.decrypt_and_verify(
    base64.b64decode(encrypted_data["ciphertext"]),
    base64.b64decode(encrypted_data["tag"])
)

print(decrypted.decode())  # ← this will show the exact broken JSON

# ✅ This line makes the config accessible in other scripts
config = decrypt_config()

# Optional log (can be removed in production)
# print("✅ Configuration Decrypted:", config)
