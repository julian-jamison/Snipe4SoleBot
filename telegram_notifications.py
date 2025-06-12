"""
Telegram notification module for the trading bot.
This module handles sending notifications via Telegram.
"""
import logging
import requests
import asyncio
from decrypt_config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegram_notifications")

# FIXED: Corrected function definition syntax
async def send_telegram_message_async(message, disable_notification=False):
    """
    Send a message via Telegram asynchronously
    
    Args:
        message (str): Message to send
        disable_notification (bool): Whether to disable notification sound
        
    Returns:
        bool: True if successful, False otherwise
    """
    return send_telegram_message(message, disable_notification)

def send_telegram_message(message, disable_notification=False):
    """
    Send a message via Telegram
    
    Args:
        message (str): Message to send
        disable_notification (bool): Whether to disable notification sound
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Get Telegram config
    telegram_config = config.get("telegram", {})
    bot_token = telegram_config.get("bot_token")
    chat_id = telegram_config.get("chat_id")
    
    # Check if Telegram is configured
    if not bot_token or not chat_id:
        logger.warning("Telegram not configured. Message not sent: " + message[:100] + "...")
        # Print to console instead
        print(f"📩 Telegram message: {message}")
        return False
    
    try:
        # API URL
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        # Parameters
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_notification": disable_notification
        }
        
        # Send request
        response = requests.post(url, data=data, timeout=10)
        
        # Check response
        if response.status_code == 200:
            logger.info(f"Telegram message sent: {message[:50]}...")
            print(f"📩 Telegram message sent: {message[:50]}...")
            return True
        else:
            logger.error(f"Failed to send Telegram message: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False

# Async wrapper for compatibility
async def safe_send_telegram_message(message, disable_notification=False):
    """
    Safe async wrapper for sending telegram messages
    
    Args:
        message (str): Message to send
        disable_notification (bool): Whether to disable notification sound
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        return send_telegram_message(message, disable_notification)
    except Exception as e:
        logger.error(f"Error in safe_send_telegram_message: {e}")
        return False

# For testing
if __name__ == "__main__":
    message = "🚀 This is a test message from the Solana trading bot!"
    success = send_telegram_message(message)
    print(f"Message sent: {success}")
