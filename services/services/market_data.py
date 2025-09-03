import requests
import time
import logging
from cachetools import TTLCache
from config import Config

# Initialize logger
logger = logging.getLogger("market_data")
logging.basicConfig(level=logging.INFO)

# Short-term cache for coin data
cache = TTLCache(maxsize=1000, ttl=Config.CACHE_TTL_SECONDS)

class MarketDataProvider:
    def __init__(self, name):
        self.name = name

    def fetch(self, symbol):
        raise NotImplementedError

    def report_success(self):
        return True

    def rate_limit_info(self):
        return {}

# Provider implementations

class CoinGeckoProvider(MarketDataProvider):
    def __init__(self):
        super().__init__('CoinGecko')

    def fetch(self, symbol):
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{symbol.lower()}"
            resp = requests.get(url, timeout=Config.PROVIDER_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            market_data = data.get('market_data', {})
            return {
                "price": market_data.get('current_price', {}).get('usd'),
                "market_cap": market_data.get('market_cap', {}).get('usd'),
                "volume_24h": market_data.get('total_volume', {}).get('usd'),
                "provider": self.name
            }
        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return None

class CoinCapProvider(MarketDataProvider):
    def __init__(self):
        super().__init__('CoinCap')

    def fetch(self, symbol):
        try:
            url = f"https://api.coincap.io/v2/assets/{symbol.lower()}"
            resp = requests.get(url, timeout=Config.PROVIDER_TIMEOUT)
            resp.raise_for_status()
            data = resp.json().get('data', {})
            return {
                "price": float(data.get('priceUsd', 0)),
                "market_cap": float(data.get('marketCapUsd', 0)),
                "volume_24h": float(data.get('volumeUsd24Hr', 0)),
                "provider": self.name
            }
        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return None

class CoinLoreProvider(MarketDataProvider):
    def __init__(self):
        super().__init__('CoinLore')

    def fetch(self, symbol):
        try:
            url = f"https://api.coinlore.net/api/ticker/?id={symbol}"
            resp = requests.get(url, timeout=Config.PROVIDER_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()[0] if resp.json() else {}
            return {
                "price": float(data.get('price_usd', 0)),
                "market_cap": float(data.get('market_cap_usd', 0)),
                "volume_24h": float(data.get('volume24', 0)),
                "provider": self.name
            }
        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return None

class CoinPaprikaProvider(MarketDataProvider):
    def __init__(self, api_key=None):
        super().__init__('CoinPaprika')
        self.api_key = api_key

    def fetch(self, symbol):
        try:
            url = f"https://api.coinpaprika.com/v1/tickers/{symbol.lower()}"
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            resp = requests.get(url, headers=headers, timeout=Config.PROVIDER_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            return {
                "price": float(data.get('price_usd', 0)),
                "market_cap": float(data.get('market_cap_usd', 0)),
                "volume_24h": float(data.get('volume_24h', 0)),
                "provider": self.name
            }
        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return None

class CryptoCompareProvider(MarketDataProvider):
    def __init__(self, api_key=None):
        super().__init__('CryptoCompare')
        self.api_key = api_key

    def fetch(self, symbol):
        try:
            url = f"https://min-api.cryptocompare.com/data/pricemultifull?fsyms={symbol.upper()}&tsyms=USD"
            headers = {}
            if self.api_key:
                headers['Authorization'] = f"Apikey {self.api_key}"
            resp = requests.get(url, headers=headers, timeout=Config.PROVIDER_TIMEOUT)
            resp.raise_for_status()
            data = resp.json().get('RAW', {}).get(symbol.upper(), {}).get('USD', {})
            return {
                "price": data.get('PRICE'),
                "market_cap": data.get('MKTCAP'),
                "volume_24h": data.get('VOLUME24HOUR'),
                "provider": self.name
            }
        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return None

class CoinMarketCapProvider(MarketDataProvider):
    def __init__(self, api_key=None):
        super().__init__('CoinMarketCap')
        self.api_key = api_key

    def fetch(self, symbol):
        try:
            url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
            params = {"symbol": symbol.upper()}
            headers = {}
            if self.api_key:
                headers['X-CMC_PRO_API_KEY'] = self.api_key
            resp = requests.get(url, headers=headers, params=params, timeout=Config.PROVIDER_TIMEOUT)
            resp.raise_for_status()
            data = resp.json().get('data', {}).get(symbol.upper(), {}).get('quote', {}).get('USD', {})
            return {
                "price": data.get('price'),
                "market_cap": data.get('market_cap'),
                "volume_24h": data.get('volume_24h'),
                "provider": self.name
            }
        except Exception as e:
            logger.error(f"{self.name} error: {e}")
            return None

# Provider registry
def get_provider_chain():
    return [
        CoinGeckoProvider(),
        CoinCapProvider(),
        CoinLoreProvider(),
        CoinPaprikaProvider(api_key=Config.COINPAPRIKA_API_KEY),
        CryptoCompareProvider(api_key=Config.CRYPTOCOMPARE_API_KEY),
        CoinMarketCapProvider(api_key=Config.COINMARKETCAP_API_KEY),
    ]

def get_market_data(symbol):
    cache_key = f"{symbol}:market_data"
    if cache_key in cache:
        cached = cache[cache_key]
        logger.info(f"Serving {symbol} from cache (provider: {cached['provider']})")
        return cached

    for provider in get_provider_chain():
        for attempt in range(Config.PROVIDER_RETRY_ATTEMPTS):
            try:
                result = provider.fetch(symbol)
                if result and result["price"] is not None:
                    cache[cache_key] = {
                        **result,
                        "timestamp": time.time()
                    }
                    logger.info(f"Fetched {symbol} from {provider.name}")
                    return cache[cache_key]
                else:
                    logger.info(f"No data from {provider.name}, trying next...")
            except Exception as e:
                logger.error(f"Provider {provider.name} attempt {attempt+1}: {e}")
                time.sleep(Config.PROVIDER_BACKOFF_FACTOR * (2 ** attempt))
    # All providers failed
    logger.error(f"All providers failed for {symbol}")
    return None
