#!/bin/bash

echo "🔧 Fixing syntax errors in Python files..."

# Simple pattern fixes for missing closing parentheses
files_to_fix=(
    "ai_prediction.py:s/for i in range(1, len(prices)]/for i in range(1, len(prices))]/g"
    "automated_trading_bot.py:s/bytes.fromhex(private_key_hex)/bytes.fromhex(private_key_hex))/g"
    "check_key.py:s/birdeye_api_key', '')/birdeye_api_key', '')))/g"
    "debug_balance.py:s/trader.keypair.pubkey()/trader.keypair.pubkey())/g"
    "encrypt_config.py:s/plaintext.encode()/plaintext.encode())/g"
    "encrypt_eax_config.py:s/get(\"salt\")/get(\"salt\"))/g"
    "fix_config.py:s/'NOT FOUND'/'NOT FOUND'))/g"
    "get-pip.py:s/message_parts)/message_parts))/g"
    "key_helper.py:s/plaintext.encode()/plaintext.encode())/g"
    "real_trade.py:s/else wallets}'/else wallets})'/g"
    "solan_real_trader.py:s/profit_target\", 10)/profit_target\", 10))/g"
    "solana_real_trader.py:s/profit_target\", 10)/profit_target\", 10))/g"
    "telegram_command_handler.py:s/f.read().strip()/f.read().strip())/g"
    "telegram_control_bot.py:s/start_command)/start_command))/g"
    "test_v2_jupiter.py:s/test_v2_jupiter_trade()/test_v2_jupiter_trade())/g"
    "test_working_trader.py:s/trader.keypair.pubkey()/trader.keypair.pubkey())/g"
    "whale_tracking.py:s/asyncio.run(test()/asyncio.run(test())/g"
)

for item in "${files_to_fix[@]}"; do
    file="${item%%:*}"
    pattern="${item##*:}"
    if [ -f "$file" ]; then
        echo "Fixing $file..."
        sed -i "$pattern" "$file"
    fi
done

# Fix merge conflicts
for file in mempool_monitor.py telegram_commands.py; do
    if [ -f "$file" ]; then
        echo "Removing merge conflicts from $file..."
        sed -i '/^<<<<<<< HEAD$/d; /^=======$/d; /^>>>>>>> /d' "$file"
    fi
done

# Fix trading_bot_advanced.py parentheses issue
if [ -f "trading_bot_advanced.py" ]; then
    sed -i 's/entry_price) \* 100/entry_price) * 100/g' "trading_bot_advanced.py"
fi

echo "✅ Basic fixes completed!"
