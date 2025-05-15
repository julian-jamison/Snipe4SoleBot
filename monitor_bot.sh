#!/bin/bash

# Health monitoring script for Snipe4SoleBot
HEARTBEAT_FILE="/root/Snipe4SoleBot/bot_heartbeat.json"
MAX_AGE_SECONDS=600  # 10 minutes
SERVICE_NAME="snipebot"

check_heartbeat() {
    if [ ! -f "$HEARTBEAT_FILE" ]; then
        echo "⚠️ Heartbeat file not found"
        return 1
    fi
    
    # Get last heartbeat timestamp
    LAST_HEARTBEAT=$(cat "$HEARTBEAT_FILE" | grep -oP '"timestamp":\s*\K[0-9.]+')
    CURRENT_TIME=$(date +%s)
    
    # Calculate age
    AGE=$((CURRENT_TIME - ${LAST_HEARTBEAT%.*}))
    
    if [ $AGE -gt $MAX_AGE_SECONDS ]; then
        echo "❌ Heartbeat is stale (${AGE}s old)"
        return 1
    fi
    
    echo "✅ Heartbeat is healthy (${AGE}s old)"
    return 0
}

restart_service() {
    echo "🔄 Restarting $SERVICE_NAME service..."
    sudo systemctl restart $SERVICE_NAME
}

# Main check
if ! check_heartbeat; then
    echo "⚠️ Bot appears unhealthy, attempting restart..."
    restart_service
fi

# Check memory usage
MEMORY_MB=$(cat "$HEARTBEAT_FILE" | grep -oP '"memory_mb":\s*\K[0-9.]+')
if (( $(echo "$MEMORY_MB > 800" | bc -l) )); then
    echo "⚠️ High memory usage: ${MEMORY_MB}MB"
    restart_service
fi
