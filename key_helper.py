def encrypt_config():
    from Crypto.Cipher import AES

    raw_key = os.environ.get("CONFIG_ENCRYPTION_KEY")
    if not raw_key:
        raise EnvironmentError("❌ CONFIG_ENCRYPTION_KEY is not set in the environment.")
    
    # Fix: Treat raw_key as a hex-encoded string, not base64
    ENCRYPTION_KEY = bytes.fromhex(raw_key)

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
