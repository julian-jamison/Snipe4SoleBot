#!/usr/bin/env python3
"""
Generate a proper Solana keypair and save to file
"""
import json
import base58
from solana.keypair import Keypair

def generate_keypair():
    """Generate a new Solana keypair"""
    # Create a new random keypair
    keypair = Keypair()
    
    # Get the secret key (private key) as bytes
    secret_key_bytes = keypair.secret_key
    
    # Convert to hex string (64 bytes)
    private_key_hex = secret_key_bytes.hex()
    
    # Get the public key as base58 string
    public_key_base58 = str(keypair.public_key)
    
    # Return the keypair information
    return {
        "private_key_hex": private_key_hex,
        "public_key": public_key_base58,
        "secret_key_bytes_base58": base58.b58encode(secret_key_bytes).decode('ascii')
    }

def main():
    """Generate keypair and save to file"""
    # Generate the keypair
    keypair_info = generate_keypair()
    
    # Print the keypair information
    print("\nGenerated new Solana keypair:")
    print(f"Public Key (base58): {keypair_info['public_key']}")
    print(f"Private Key (hex, 64 bytes): {keypair_info['private_key_hex']}")
    print(f"Secret Key (base58): {keypair_info['secret_key_bytes_base58']}")
    
    # Save to file
    output_file = "proper_keypair.json"
    with open(output_file, "w") as f:
        json.dump(keypair_info, f, indent=2)
    
    print(f"\nKeypair saved to {output_file}")
    print("\nIMPORTANT: Keep your private key secure! Anyone with access to this key can control your wallet.")
    print("          Consider encrypting this file or storing the keys in a secure location.")

if __name__ == "__main__":
    main()
