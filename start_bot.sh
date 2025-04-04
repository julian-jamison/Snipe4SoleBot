#!/bin/bash

cd /root/Snipe4SoleBot
source venv/bin/activate

# Echo Python just for debug
echo "Using Python: $(which python)"
echo "Using PIP: $(which pip)"
echo "Python packages: $(pip list)"

export CONFIG_ENCRYPTION_KEY="Snipe4$ole@Bot_2025_secure_key"

exec python bot.py
