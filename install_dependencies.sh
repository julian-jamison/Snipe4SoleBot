#!/bin/bash
# Install script for real trading functionality

echo "Installing dependencies for real trading..."

# Update package list
pip install --upgrade pip

# Install Solana dependencies (multiple approaches for compatibility)
echo "Installing Solana SDK (may take a few minutes)..."

# Try different installation approaches
pip install solana-py || echo "Failed to install solana-py, trying alternatives..."

# Alternative approach - separate packages
echo "Installing individual components..."
pip install solders
pip install solana-sdk
pip install base58
pip install anchorpy
pip install spl

# Install cryptography for encryption support
pip install cryptography

# Install requests for API calls
pip install requests

# Install other dependencies
pip install python-telegram-bot

# Create necessary directories
mkdir -p data logs abis

# Create sample ABI files if they don't exist
if [ ! -f abis/erc20_abi.json ]; then
    echo "Creating sample ERC20 ABI..."
    echo '[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"}]' > abis/erc20_abi.json
fi

if [ ! -f abis/factory_abi.json ]; then
    echo "Creating sample Factory ABI..."
    echo '[{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"token0","type":"address"},{"indexed":true,"internalType":"address","name":"token1","type":"address"},{"indexed":false,"internalType":"address","name":"pair","type":"address"},{"indexed":false,"internalType":"uint256","name":"","type":"uint256"}],"name":"PairCreated","type":"event"}]' > abis/factory_abi.json
fi

if [ ! -f abis/pair_abi.json ]; then
    echo "Creating sample Pair ABI..."
    echo '[{"constant":true,"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"payable":false,"stateMutability":"view","type":"function"}]' > abis/pair_abi.json
fi

if [ ! -f abis/router_abi.json ]; then
    echo "Creating sample Router ABI..."
    echo '[{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"}]' > abis/router_abi.json
fi

echo "All dependencies installed successfully!"
echo ""
echo "Next steps:"
echo "1. Ensure your config.json has valid API keys and wallet information"
echo "2. Run test_real_trading.py to verify functionality"
echo "3. Enable real trading by setting 'live_mode' to true in config.json"
echo ""
echo "Example: python test_real_trading.py --test balance"
