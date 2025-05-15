import json
import os
import time
import asyncio
import aiohttp
import threading
import subprocess
import psutil
from telegram.request import _httpxrequest as AiohttpRequest
from telegram import Update, Bot
from telegram.ext import ContextTypes
from telegram.ext import ApplicationBuilder, CommandHandler
from decrypt_config import config
from config_manager import load_decrypted_config

TELEGRAM_BOT_TOKEN = config["telegram"]["bot_token"]
TELEGRAM_CHAT_ID = config["telegram"]["chat_id"]

STATUS_FILE = "bot_status.json"
PORTFOLIO_FILE = "portfolio.json"
WALLETS_FILE = "wallets.json"
BOT_RUNNING_FLAG = "bot_running.flag"
SERVICE_NAME = "snipebot"  # For systemd service

# Track bot start time globally
BOT_START_TIME = time.time()

# Create the session inside the event loop
async def create_session():
    session = aiohttp.ClientSession()
    request = AiohttpRequest(session)
    bot = Bot(token=TELEGRAM_BOT_TOKEN, request=request)
    return bot, session

telegram_listener_started = False

def schedule_safe_telegram_message(message: str):
    def run_in_loop():
        try:
            asyncio.run(safe_send_telegram_message(message))
        except RuntimeError as e:
            print(f"⚠️ Loop error fallback: {e}")
    threading.Thread(target=run_in_loop).start()

async def safe_send_telegram_message(message: str):
    print(f"🔄 Attempting to send Telegram message: {message[:40]}...")
    try:
        bot, _ = await create_session()  # Create bot session here
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print(f"📩 Telegram message sent safely: {message}")
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")

def is_bot_running():
    """Check if the main bot is running."""
    # Check for the flag file
    if os.path.exists(BOT_RUNNING_FLAG):
        return True
    
    # Check for the process via systemd
    try:
        result = subprocess.run(["systemctl", "is-active", SERVICE_NAME], 
                              capture_output=True, text=True)
        return result.stdout.strip() == "active"
    except:
        pass
    
    # Check for Python process running bot.py
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python' in proc.info['name'].lower():
                cmdline = ' '.join(proc.info['cmdline'])
                if 'bot.py' in cmdline and proc.info['pid'] != os.getpid():
                    return True
        except:
            continue
    
    return False

async def start_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command to start the main bot."""
    if not update.effective_chat:
        return
    
    print(f"📩 Received /start from chat_id={update.effective_chat.id}")
    
    # Check if bot is already running
    if is_bot_running():
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="🤖 Bot is already running!"
        )
        return
    
    try:
        # Try to start via systemd first
        result = subprocess.run(["sudo", "systemctl", "start", SERVICE_NAME], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="✅ Bot started successfully via systemd!"
            )
        else:
            # Fallback to direct Python execution
            subprocess.Popen(["python", "/root/Snipe4SoleBot/bot.py"], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="✅ Bot started directly!"
            )
        
        # Wait a moment for the bot to start
        await asyncio.sleep(3)
        
        # Check if it's actually running
        if is_bot_running():
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="🚀 Snipe4SoleBot is now active and monitoring!"
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="⚠️ Bot started but verification failed. Check logs."
            )
            
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f"❌ Failed to start bot: {str(e)}"
        )

async def stop_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /stop command to stop the main bot."""
    if not update.effective_chat:
        return
    
    print(f"📩 Received /stop from chat_id={update.effective_chat.id}")
    
    if not is_bot_running():
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="🤖 Bot is not running!"
        )
        return
    
    try:
        # Try to stop via systemd first
        result = subprocess.run(["sudo", "systemctl", "stop", SERVICE_NAME], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="✅ Bot stopped successfully!"
            )
        else:
            # Fallback to killing the process
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'python' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline'])
                        if 'bot.py' in cmdline:
                            proc.terminate()
                            await context.bot.send_message(
                                chat_id=update.effective_chat.id, 
                                text="✅ Bot process terminated!"
                            )
                            break
                except:
                    continue
            
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f"❌ Failed to stop bot: {str(e)}"
        )

async def restart_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /restart command to restart the main bot."""
    if not update.effective_chat:
        return
    
    print(f"📩 Received /restart from chat_id={update.effective_chat.id}")
    
    try:
        # Try to restart via systemd
        result = subprocess.run(["sudo", "systemctl", "restart", SERVICE_NAME], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="✅ Bot restarted successfully!"
            )
        else:
            # Fallback: stop then start
            await stop_bot_command(update, context)
            await asyncio.sleep(2)
            await start_bot_command(update, context)
            
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f"❌ Failed to restart bot: {str(e)}"
        )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return

    print(f"📩 Received /status from chat_id={update.effective_chat.id}")

    try:
        # Load current config
        current_config = load_decrypted_config()
        
        # Check if bot is running
        bot_running = is_bot_running()
        bot_status = "🟢 Running" if bot_running else "🔴 Stopped"
        
        # Calculate uptime if bot is running
        uptime_text = "N/A"
        if bot_running and os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, "r") as f:
                    status_data = json.load(f)
                    start_time = status_data.get('start_time', 0)
                    if start_time:
                        uptime_seconds = time.time() - start_time
                        uptime_minutes = round(uptime_seconds / 60, 2)
                        uptime_text = f"{uptime_minutes} minutes"
            except:
                pass
        
        # Load status data if available
        trade_count = 0
        total_profit = 0.0
        
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, "r") as f:
                    status_data = json.load(f)
                    trade_count = status_data.get('trade_count', 0)
                    total_profit = status_data.get('profit', 0.0)
            except:
                pass
        
        # Create status message
        msg = f"""🤖 *Snipe4SoleBot Status*

📊 *Runtime Stats:*
• Status: {bot_status}
• Uptime: {uptime_text}
• Trades Executed: {trade_count}
• Total Profit/Loss: {total_profit:.4f} SOL

⚙️ *Configuration:*
• Live Mode: {'Enabled' if current_config.get('api_keys', {}).get('live_mode', False) else 'Disabled'}
• Min Liquidity: ${current_config.get('trade_settings', {}).get('min_liquidity', 0)}
• Profit Target: {current_config.get('trade_settings', {}).get('profit_target', 0)}%
• Stop Loss: {current_config.get('trade_settings', {}).get('stop_loss', 0)}%

🔍 *Available Commands:*
• /start - Start the bot
• /stop - Stop the bot
• /restart - Restart the bot
• /status - Bot status
• /wallets - View wallets
• /pause - Pause trading
• /resume - Resume trading
"""
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=msg,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        error_msg = f"❌ Error loading status: {str(e)}"
        print(error_msg)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_msg)

async def wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return

    print(f"📩 Received /wallets from chat_id={update.effective_chat.id}")

    try:
        # Load wallet addresses from config
        current_config = load_decrypted_config()
        wallet_addresses = current_config.get('solana_wallets', {})
        
        # Filter only trading wallets
        trading_wallets = {k: v for k, v in wallet_addresses.items() 
                          if k.startswith('wallet_') and not k.endswith('_key')}
        
        if not trading_wallets:
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text="⚠️ No trading wallets configured."
            )
            return
        
        # Create wallet overview message
        message = "👛 *Trading Wallet Overview:*\n\n"
        
        for wallet_name, wallet_address in trading_wallets.items():
            # Format wallet display
            short_address = f"{wallet_address[:4]}...{wallet_address[-4:]}"
            message += f"• {wallet_name}: `{short_address}`\n"
        
        # Add cold wallet info if available
        cold_wallet = wallet_addresses.get('cold_wallet')
        if cold_wallet:
            message += f"\n💰 *Cold Wallet:*\n• `{cold_wallet[:4]}...{cold_wallet[-4:]}`"
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=message,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        error_msg = f"❌ Failed to load wallets: {str(e)}"
        print(error_msg)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_msg)

async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📩 Received /pause from chat_id={update.effective_chat.id}")
    with open("pause_flag", "w") as f:
        f.write("1")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="⏸ Bot paused.")

async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📩 Received /resume from chat_id={update.effective_chat.id}")
    if os.path.exists("pause_flag"):
        os.remove("pause_flag")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="▶️ Bot resumed.")

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📩 Received /debug from chat_id={update.effective_chat.id}")
    
    # Send detailed debug information
    debug_info = """🔍 *Debug Information*
    
• Bot Version: 1.0.0
• Python Version: 3.x
• Telegram Connection: ✅ Active
• Config Loaded: ✅ Success
    
*Available Commands:*
• /start - Start the bot
• /stop - Stop the bot
• /restart - Restart the bot
• /status - Bot status
• /wallets - View wallets
• /pause - Pause trading
• /resume - Resume trading
• /debug - This message
"""
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=debug_info,
        parse_mode='Markdown'
    )

async def run_telegram_command_listener(token):
    global telegram_listener_started
    if telegram_listener_started:
        return

    telegram_listener_started = True
    print("✅ Starting Telegram command listener...")

    app = ApplicationBuilder().token(token).build()
    
    # Add all command handlers
    app.add_handler(CommandHandler("start", start_bot_command))
    app.add_handler(CommandHandler("stop", stop_bot_command))
    app.add_handler(CommandHandler("restart", restart_bot_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("wallets", wallets))
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(CommandHandler("debug", debug))
    
    await app.run_polling()
