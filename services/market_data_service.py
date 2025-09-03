import os
import requests

class MarketDataService:
    def __init__(self, config, cache_service):
        self.config = config
        self.cache_service = cache_service
        self.api_keys = {
            'coinpaprika': os.getenv('COINPAPRIKA_API_KEY'),
            'cryptocompare': os.getenv('CRYPTOCOMPARE_API_KEY'),
            'coinmarketcap': os.getenv('COINMARKETCAP_API_KEY'),
        }
        # Only add providers that either don't need keys, or have keys present
        self.providers = [
            self._get_coingecko,
            self._get_coincap,
            self._get_coinlore,
        ]
        if self.api_keys['coinpaprika']:
            self.providers.append(self._get_coinpaprika)
        if self.api_keys['cryptocompare']:
            self.providers.append(self._get_cryptocompare)
        if self.api_keys['coinmarketcap']:
            self.providers.append(self._get_coinmarketcap)

    # ... rest of your provider API code ...
