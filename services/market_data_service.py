import requests
import statistics
from cachetools import TTLCache
import os

class MarketDataService:
    """Service for fetching market data from multiple APIs and aggregating consensus."""

    def __init__(self, config, cache_service):
        self.config = config
        self.cache_service = cache_service
        self.api_keys = {
            'coinpaprika': os.environ.get('COINPAPRIKA_API_KEY'),
            'cryptocompare': os.environ.get('CRYPTOCOMPARE_API_KEY'),
            'coinmarketcap': os.environ.get('COINMARKETCAP_API_KEY')
        }
        self.providers = [
            self._get_coingecko,
            self._get_coincap,
            self._get_coinlore,
            self._get_coinpaprika,
            self._get_cryptocompare,
            self._get_coinmarketcap
        ]

    def health_check(self):
        return {"status": "healthy"}

    def get_supported_coins(self):
        # Consensus not needed; just use CoinGecko for supported coins
        url = "https://api.coingecko.com/api/v3/coins/list"
        resp = requests.get(url)
        resp.raise_for_status()
        coins = resp.json()
        return [coin["id"] for coin in coins]

    def get_supported_exchanges(self):
        # Consensus not needed; just use CoinGecko for supported exchanges
        url = "https://api.coingecko.com/api/v3/exchanges/list"
        resp = requests.get(url)
        resp.raise_for_status()
        exchanges = resp.json()
        return [ex["id"] for ex in exchanges]

    def get_realtime_data(self, coin_id):
        cache_key = f"consensus_realtime_{coin_id}"
        cached = self.cache_service.get(cache_key)
        if cached:
            return cached

        price_list, market_cap_list, volume_list, change_list = [], [], [], []

        for provider in self.providers:
            try:
                data = provider(coin_id)
                if data:
                    price_list.append(data.get("price"))
                    market_cap_list.append(data.get("market_cap"))
                    volume_list.append(data.get("volume_24h"))
                    change_list.append(data.get("change_24h"))
            except Exception:
                continue

        def safe_median(lst):
            lst = [x for x in lst if x is not None]
            return statistics.median(lst) if lst else None

        consensus_data = {
            "price": safe_median(price_list),
            "market_cap": safe_median(market_cap_list),
            "volume_24h": safe_median(volume_list),
            "change_24h": safe_median(change_list)
        }
        self.cache_service.set(cache_key, consensus_data)
        return consensus_data

    # --- Individual API methods ---

    def _get_coingecko(self, coin_id):
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_market_cap=true&include_24hr_vol=true&include_24hr_change=true"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json().get(coin_id, {})
        return {
            "price": data.get("usd"),
            "market_cap": data.get("usd_market_cap"),
            "volume_24h": data.get("usd_24h_vol"),
            "change_24h": data.get("usd_24h_change")
        }

    def _get_coincap(self, coin_id):
        # CoinCap uses symbols (e.g. BTC), so fallback mapping for known coins
        symbol_map = {'bitcoin': 'btc', 'ethereum': 'eth', 'chainlink': 'link'}
        symbol = symbol_map.get(coin_id, coin_id)
        url = f"https://api.coincap.io/v2/assets/{symbol}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json().get("data", {})
        return {
            "price": float(data.get("priceUsd")) if data.get("priceUsd") else None,
            "market_cap": float(data.get("marketCapUsd")) if data.get("marketCapUsd") else None,
            "volume_24h": float(data.get("volumeUsd24Hr")) if data.get("volumeUsd24Hr") else None,
            "change_24h": float(data.get("changePercent24Hr")) if data.get("changePercent24Hr") else None
        }

    def _get_coinlore(self, coin_id):
        # CoinLore uses IDs; fallback for BTC, ETH, LINK
        id_map = {'bitcoin': '90', 'ethereum': '80', 'chainlink': '518'}
        coinlore_id = id_map.get(coin_id)
        if not coinlore_id:
            return None
        url = f"https://api.coinlore.net/api/ticker/?id={coinlore_id}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        result = resp.json()[0]
        return {
            "price": float(result.get("price_usd")) if result.get("price_usd") else None,
            "market_cap": float(result.get("market_cap_usd")) if result.get("market_cap_usd") else None,
            "volume_24h": float(result.get("volume24")) if result.get("volume24") else None,
            "change_24h": float(result.get("percent_change_24h")) if result.get("percent_change_24h") else None
        }

    def _get_coinpaprika(self, coin_id):
        # CoinPaprika uses symbols, e.g., btc-bitcoin
        symbol_map = {'bitcoin': 'btc-bitcoin', 'ethereum': 'eth-ethereum', 'chainlink': 'link-chainlink'}
        paprika_id = symbol_map.get(coin_id)
        if not paprika_id:
            return None
        url = f"https://api.coinpaprika.com/v1/tickers/{paprika_id}"
        headers = {}
        if self.api_keys['coinpaprika']:
            headers['Authorization'] = f"Bearer {self.api_keys['coinpaprika']}"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return {
            "price": data.get("quotes", {}).get("USD", {}).get("price"),
            "market_cap": data.get("quotes", {}).get("USD", {}).get("market_cap"),
            "volume_24h": data.get("quotes", {}).get("USD", {}).get("volume_24h"),
            "change_24h": data.get("quotes", {}).get("USD", {}).get("percent_change_24h")
        }

    def _get_cryptocompare(self, coin_id):
        # CryptoCompare uses symbols; fallback for BTC, ETH, LINK
        symbol_map = {'bitcoin': 'BTC', 'ethereum': 'ETH', 'chainlink': 'LINK'}
        symbol = symbol_map.get(coin_id)
        if not symbol or not self.api_keys['cryptocompare']:
            return None
        url = f"https://min-api.cryptocompare.com/data/pricemultifull?fsyms={symbol}&tsyms=USD"
        headers = {'authorization': f'Apikey {self.api_keys["cryptocompare"]}'}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json().get("RAW", {}).get(symbol, {}).get("USD", {})
        return {
            "price": data.get("PRICE"),
            "market_cap": data.get("MKTCAP"),
            "volume_24h": data.get("TOTALVOLUME24H"),
            "change_24h": data.get("CHANGEPCT24HOUR")
        }

    def _get_coinmarketcap(self, coin_id):
        # CoinMarketCap uses slugs for coin_id; fallback for BTC, ETH, LINK
        slug_map = {'bitcoin': 'bitcoin', 'ethereum': 'ethereum', 'chainlink': 'chainlink'}
        slug = slug_map.get(coin_id)
        if not slug or not self.api_keys['coinmarketcap']:
            return None
        url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?slug={slug}&convert=USD"
        headers = {'X-CMC_PRO_API_KEY': self.api_keys["coinmarketcap"]}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        data = next(iter(resp.json().get("data", {}).values()), None)
        if not data:
            return None
        quote = data.get("quote", {}).get("USD", {})
        return {
            "price": quote.get("price"),
            "market_cap": quote.get("market_cap"),
            "volume_24h": quote.get("volume_24h"),
            "change_24h": quote.get("percent_change_24h")
        }
