import pandas as pd

class SignalService:
    """Service for calculating trading signals."""
    
    def __init__(self, config):
        self.config = config
    
    def health_check(self):
        return {"status": "healthy"}
    
    def calculate_signals(self, df: pd.DataFrame, signal_group: str = None):
        """
        Calculate standard signals without any special scaling.
        Formulas are standard implementations for RSI, MACD, etc.
        Group parameter is optional; here we calculate a basic set.
        """
        signals = {}
        
        # RSI (14 periods) - no scaling
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14, min_periods=14).mean()
        avg_loss = loss.rolling(window=14, min_periods=14).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        signals['rsi'] = rsi
        
        # MACD (12,26,9) - no scaling
        ema12 = df['close'].ewm(span=12, adjust=False, min_periods=12).mean()
        ema26 = df['close'].ewm(span=26, adjust=False, min_periods=26).mean()
        macd = ema12 - ema26
        signal_line = macd.ewm(span=9, adjust=False, min_periods=9).mean()
        histogram = macd - signal_line
        signals['macd'] = macd
        signals['signal_line'] = signal_line
        signals['histogram'] = histogram
        
        # Simple Moving Average (20 periods) - example for other groups
        sma20 = df['close'].rolling(window=20, min_periods=20).mean()
        signals['sma20'] = sma20
        
        # Bollinger Bands (20 periods, 2 std) - no scaling
        rolling_mean = df['close'].rolling(window=20, min_periods=20).mean()
        rolling_std = df['close'].rolling(window=20, min_periods=20).std()
        upper_band = rolling_mean + (rolling_std * 2)
        lower_band = rolling_mean - (rolling_std * 2)
        signals['upper_band'] = upper_band
        signals['lower_band'] = lower_band
        
        return signals
