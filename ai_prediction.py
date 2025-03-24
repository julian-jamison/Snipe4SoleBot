import numpy as np
from tensorflow.keras.models import load_model
from utils import fetch_price

model = load_model("lstm_model.h5")

FEATURE_WINDOW = 10  # Number of time steps to consider for predictions


def calculate_rsi(prices, period=14):
    """Calculates the Relative Strength Index (RSI) based on price history."""
    if len(prices) < period:
        return None
    
    gains = [max(prices[i] - prices[i - 1], 0) for i in range(1, len(prices))]
    losses = [max(prices[i - 1] - prices[i], 0) for i in range(1, len(prices))]
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0:
        return 100  # RSI max
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_macd(prices, short_window=12, long_window=26, signal_window=9):
    """Calculates the Moving Average Convergence Divergence (MACD) indicator."""
    if len(prices) < long_window:
        return None, None
    
    short_ema = np.mean(prices[-short_window:])
    long_ema = np.mean(prices[-long_window:])
    macd = short_ema - long_ema
    signal = np.mean(prices[-signal_window:])
    return macd, signal


def calculate_moving_averages(prices, short_window=10, long_window=50):
    """Calculates short-term and long-term moving averages."""
    if len(prices) < long_window:
        return None, None
    
    short_ma = np.mean(prices[-short_window:])
    long_ma = np.mean(prices[-long_window:])
    return short_ma, long_ma


def get_market_features(token_address):
    """Fetches historical market data and computes indicators for AI predictions."""
    prices = []
    for _ in range(FEATURE_WINDOW):
        price = fetch_price(token_address)
        if price is None:
            return None
        prices.append(price)
    
    rsi = calculate_rsi(prices)
    macd, signal = calculate_macd(prices)
    short_ma, long_ma = calculate_moving_averages(prices)
    
    features = np.array(prices + [
        rsi if rsi is not None else 50, 
        macd if macd is not None else 0, 
        signal if signal is not None else 0, 
        short_ma if short_ma is not None else prices[-1], 
        long_ma if long_ma is not None else prices[-1]
    ]).reshape(1, FEATURE_WINDOW + 4)
    
    return features


def predict_market_trend(token_address):
    """Uses AI (LSTM model) to predict whether to buy, sell, or hold based on real market data."""
    market_data = get_market_features(token_address)
    if market_data is None:
        print("⚠️ Not enough market data available for prediction.")
        return "hold", 0.5
    
    prediction = model.predict(market_data)[0][0]

    if prediction > 0.6:
        return "buy", prediction
    elif prediction < 0.4:
        return "sell", prediction
    else:
        return "hold", prediction

