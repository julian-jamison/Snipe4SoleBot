import time
from trade_execution import execute_trade
from mempool_monitor import check_mempool
from ai_prediction import predict_market_trend
from telegram_notifications import send_telegram_message_async
from health_check import send_health_update
from backup_config import backup_to_gdrive

def main():
    """Main trading bot loop."""
   await send_telegram_message_async("🚀 Snipe4SoleBot has started!")
    
    while True:
        print("🔍 Monitoring market and mempool...")
        trade_signal = check_mempool()
        
        if trade_signal:
            predicted_trend = predict_market_trend()
            if predicted_trend == "buy":
                execute_trade("buy")
            elif predicted_trend == "sell":
                execute_trade("sell")
        
        # Send a health update every hour
        send_health_update()
        
        # Backup encrypted config to Google Drive every 24 hours
        if time.time() % 86400 < 2:  # Check if a day has passed
            backup_to_gdrive()
           await send_telegram_message_async("🔄 Config backup completed!")
        
        time.sleep(2)

if __name__ == "__main__":
    main()
