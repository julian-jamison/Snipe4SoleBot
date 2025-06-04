#!/bin/bash
# Simplified installation script for Solana trading dependencies

echo "Installing minimal required dependencies for testing..."

# Update pip
pip install --upgrade pip

# Install core requests library
pip install requests

# Try multiple approaches for Solana SDK installation
echo "Trying to install Solana SDK..."

# First, try the old library version which has better compatibility with some systems
pip install solana==0.28.0

# If above fails, try newer package
if [ $? -ne 0 ]; then
    echo "Failed to install older Solana version, trying newer package..."
    pip install solana-py
fi

# Install base58 for key encoding
pip install base58

# Create necessary directories
mkdir -p data logs abis

echo ""
echo "Installation complete!"
echo ""
echo "Now run the test again:"
echo "python test_real_trading.py --test price"
echo ""
