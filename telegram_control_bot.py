#!/usr/bin/env python3
"""
Telegram Control Bot - Always running to control the main bot
"""
import asyncio
import subprocess
import os
import psutil
import time
import json
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from decrypt_config import config

TELEGRAM_BOT_TOKEN = config["telegram"]["bot_token"]
TELEGRAM_CHAT_ID = config["telegram"]["chat_id"]
SERVICE_NAME = "snipebot"
BOT_PATH = "/root/Snipe4SoleBot/bot.py"
VENV_PYTHON = "/root/Snipe4SoleBot/venv/bin/python"

def is_bot_running():
    """Check if the main bot is running."""
    # Check via systemd
    try:
        result = subprocess.run(["systemctl", "is-active", SERVICE_NAME], 
                              capture_output=True, text=True)
        if result.stdout.strip() == "active":
            return True
    except:
        pass
    
    # Check for Python process
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python' in proc.info['name'].lower():
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'bot.py' in cmdline and 'telegram_control' not in cmdline:
                    return True
        except:
            continue
    
    return False

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the main bot."""
    if is_bot_running():
        await update.message.reply_text("🤖 Bot is already running!")
        return
    
    await update.message.reply_text("🚀 Starting Snipe4SoleBot...")
    
    try:
        # Try systemd first
        result = subprocess.run(["sudo", "systemctl", "start", SERVICE_NAME], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            await update.message.reply_text("✅ Bot started successfully via systemd!")
        else:
            # Direct execution
            subprocess.Popen([VENV_PYTHON, BOT_PATH], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            await update.message.reply_text("✅ Bot started directly!")
        
        # Verify it's running
        await asyncio.sleep(3)
        if is_bot_running():
            await update.message.reply_text("🟢 Bot is now active and monitoring!")
        else:
            await update.message.reply_text("⚠️ Bot may not have started correctly. Check logs.")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to start: {str(e)}")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop the main bot."""
    if not is_bot_running():
        await update.message.reply_text("🤖 Bot is not running!")
        return
    
    await update.message.reply_text("🛑 Stopping Snipe4SoleBot...")
    
    try:
        # Try systemd first
        result = subprocess.run(["sudo", "systemctl", "stop", SERVICE_NAME], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            await update.message.reply_text("✅ Bot stopped via systemd!")
        else:
            # Kill process directly
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'python' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        if 'bot.py' in cmdline and 'telegram_control' not in cmdline:
                            proc.terminate()
                            await update.message.reply_text("✅ Bot process terminated!")
                            break
                except:
                    continue
        
        await asyncio.sleep(2)
        if not is_bot_running():
            await update.message.reply_text("🔴 Bot is now stopped.")
        else:
            await update.message.reply_text("⚠️ Bot may still be running. Check manually.")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to stop: {str(e)}")

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restart the main bot."""
    await update.message.reply_text("🔄 Restarting Snipe4SoleBot...")
    
    # Stop first
    await stop_command(update, context)
    await asyncio.sleep(3)
    
    # Then start
    await start_command(update, context)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check bot status."""
    bot_status = "🟢 Running" if is_bot_running() else "🔴 Stopped"
    
    msg = f"""🤖 *Snipe4SoleBot Control Panel*
    
Status: {bot_status}

*Available Commands:*
• /start - Start the trading bot
• /stop - Stop the trading bot  
• /restart - Restart the bot
• /status - Check current status
• /logs - View recent logs
"""
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent logs."""
    try:
        # Get last 10 lines of logs
        result = subprocess.run(["tail", "-n", "10", "/root/Snipe4SoleBot/bot_debug.log"], 
                              capture_output=True, text=True)
        
        if result.stdout:
            log_text = f"📋 *Recent Logs:*\n```\n{result.stdout}\n```"
            await update.message.reply_text(log_text, parse_mode='Markdown')
        else:
            await update.message.reply_text("📋 No recent logs found.")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to read logs: {str(e)}")

async def main():
    """Run the control bot."""
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stop", stop_command)
    app.add_handler(CommandHandler("restart", restart_command))
    app.add_handler(CommandHandler("status", status_command)
    app.add_handler(CommandHandler("logs", logs_command)
    
    print("🎮 Telegram Control Bot started. Use commands to control Snipe4SoleBot.")
    
    # Run the bot
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main()
