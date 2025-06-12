#!/bin/bash

cd /root/Snipe4SoleBot
source venv/bin/activate

# Always require explicit LIVE confirmation
export S4S_CONFIRM_LIVE=YES

# Echo Python just for debug
echo "Using Python: $(which python)"
echo "Using PIP: $(which pip)"
echo "Python packages: $(pip list)"

export CONFIG_ENCRYPTION_KEY="Snipe4$ole@Bot_2025_secure_key"
export S4S_CONFIRM_LIVE=YES

exec python bot.py
