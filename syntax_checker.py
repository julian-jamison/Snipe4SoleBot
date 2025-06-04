#!/bin/bash

# This script checks all Python files for syntax errors

echo "Checking Python files for syntax errors..."

# Check core modules
for file in bot.py monitor_and_trade.py trade_execution.py telegram_command_handler.py decrypt_config.py config_manager.py whale_tracking.py telegram_notifications.py utils.py portfolio.py
do
    if [ -f "$file" ]; then
        echo "Checking $file..."
        python -m py_compile "$file"
        if [ $? -eq 0 ]; then
            echo "✅ $file: No syntax errors"
        else
            echo "❌ $file: Syntax errors found"
        fi
    else
        echo "⚠️ $file not found"
    fi
done

echo "Syntax check complete."
