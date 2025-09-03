import os

class Config:
    # API Keys from environment variables
    COINPAPRIKA_API_KEY = os.getenv('COINPAPRIKA_API_KEY')
    CRYPTOCOMPARE_API_KEY = os.getenv('CRYPTOCOMPARE_API_KEY')
    COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY')

    # Cache settings
    CACHE_TTL_SECONDS = int(os.getenv('CACHE_TTL_SECONDS', 60))

    # Timeout for external API calls
    PROVIDER_TIMEOUT = float(os.getenv('PROVIDER_TIMEOUT', 2.0))
    PROVIDER_RETRY_ATTEMPTS = int(os.getenv('PROVIDER_RETRY_ATTEMPTS', 2))
    PROVIDER_BACKOFF_FACTOR = float(os.getenv('PROVIDER_BACKOFF_FACTOR', 0.5))

    # Provider priority order
    PROVIDER_CHAIN = [
        'CoinGecko',
        'CoinCap',
        'CoinLore',
        'CoinPaprika',
        'CryptoCompare',
        'CoinMarketCap'
    ]
