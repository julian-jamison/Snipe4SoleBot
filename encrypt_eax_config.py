#!/usr/bin/env python3
"""
Encrypt and decrypt configuration files using AES-EAX mode
"""
import os
import json
import base64
import getpass
import argparse
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def derive_key(password, salt=None):
    """
    Derive an encryption key from a password using PBKDF2
    
    Args:
        password (str): Password to derive key from
        salt (bytes, optional): Salt for key derivation. If None, generates a new random salt.
        
    Returns:
        tuple: (key, salt)
    """
    if salt is None:
        salt = os.urandom(16)
    
    # Convert password to bytes if it's a string
    if isinstance(password, str):
        password = password.encode('utf-8')
    
    # Create a PBKDF2HMAC instance
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 32 bytes = 256 bits
        salt=salt,
        iterations=100000,
    )
    
    # Derive the key
    key = kdf.derive(password)
    
    return key, salt

def encrypt_config(config_file, output_file=None, password=None):
    """
    Encrypt a configuration file
    
    Args:
        config_file (str): Path to configuration file
        output_file (str, optional): Path to output file. If None, adds '.encrypted' to config_file
        password (str, optional): Password for encryption. If None, prompts for password.
        
    Returns:
        str: Path to encrypted file
    """
    # Set default output file
    if output_file is None:
        output_file = f"{config_file}.encrypted"
    
    # Read the configuration file
    try:
        with open(config_file, 'r') as f:
            config_data = json.load(f)
    except Exception as e:
        print(f"Error reading configuration file: {e}")
        return None
    
    # Convert config to JSON string
    config_json = json.dumps(config_data)
    config_bytes = config_json.encode('utf-8')
    
    # Get password if not provided
    if password is None:
        password = getpass.getpass("Enter encryption password: ")
        password_confirm = getpass.getpass("Confirm encryption password: ")
        
        if password != password_confirm:
            print("Passwords do not match!")
            return None
    
    # Derive key and generate salt
    key, salt = derive_key(password)
    
    # Generate a random nonce
    nonce = os.urandom(12)
    
    # Create AESGCM cipher
    aesgcm = AESGCM(key)
    
    # Encrypt the data
    ciphertext = aesgcm.encrypt(nonce, config_bytes, None)
    
    # Create encrypted data structure
    encrypted_data = {
        "algorithm": "AES-GCM",
        "salt": base64.b64encode(salt).decode('utf-8'),
        "nonce": base64.b64encode(nonce).decode('utf-8'),
        "ciphertext": base64.b64encode(ciphertext).decode('utf-8')
    }
    
    # Write to output file
    with open(output_file, 'w') as f:
        json.dump(encrypted_data, f, indent=2)
    
    print(f"Configuration encrypted and saved to {output_file}")
    return output_file

def decrypt_config(encrypted_file, output_file=None, password=None):
    """
    Decrypt a configuration file
    
    Args:
        encrypted_file (str): Path to encrypted file
        output_file (str, optional): Path to output file. If None, adds '.decrypted' to encrypted_file
        password (str, optional): Password for decryption. If None, prompts for password.
        
    Returns:
        dict: Decrypted configuration
    """
    # Set default output file
    if output_file is None:
        output_file = f"{encrypted_file}.decrypted"
    
    # Read the encrypted file
    try:
        with open(encrypted_file, 'r') as f:
            encrypted_data = json.load(f)
    except Exception as e:
        print(f"Error reading encrypted file: {e}")
        return None
    
    # Get algorithm and encrypted data
    algorithm = encrypted_data.get("algorithm")
    if algorithm != "AES-GCM":
        print(f"Unsupported encryption algorithm: {algorithm}")
        return None
    
    # Decode salt, nonce, and ciphertext
    salt = base64.b64decode(encrypted_data.get("salt"))
    nonce = base64.b64decode(encrypted_data.get("nonce"))
    ciphertext = base64.b64decode(encrypted_data.get("ciphertext"))
    
    # Get password if not provided
    if password is None:
        password = getpass.getpass("Enter decryption password: ")
    
    # Derive key
    key, _ = derive_key(password, salt)
    
    # Create AESGCM cipher
    aesgcm = AESGCM(key)
    
    try:
        # Decrypt the data
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        
        # Parse JSON
        config_data = json.loads(decrypted_bytes.decode('utf-8'))
        
        # Write to output file if specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            print(f"Configuration decrypted and saved to {output_file}")
        
        return config_data
    
    except Exception as e:
        print(f"Error decrypting configuration: {e}")
        print("This could be due to an incorrect password or corrupted file.")
        return None

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Encrypt and decrypt configuration files")
    parser.add_argument('action', choices=['encrypt', 'decrypt'], help='Action to perform')
    parser.add_argument('file', help='File to encrypt or decrypt')
    parser.add_argument('--output', '-o', help='Output file path')
    
    args = parser.parse_args()
    
    if args.action == 'encrypt':
        encrypt_config(args.file, args.output)
    elif args.action == 'decrypt':
        decrypt_config(args.file, args.output)

if __name__ == "__main__":
    main()
