class ResponseFormatter:
    """Formatter for API responses."""

    def format_market_response(self, market_data, signals, realtime_data, coin_id):
        # Ensure index alignment by reindexing signals to match historical data
        base_index = market_data.df.index
        formatted_signals = {
            k: v.reindex(base_index).dropna().to_dict() for k, v in signals.items()
        }
        return {
            'coin_id': coin_id,
            'historical_data': market_data.df.reset_index().to_dict(orient='records'),
            'signals': formatted_signals,
            'realtime': realtime_data
        }
