"""
Cryptocurrency Trading Signal Analysis Application
Refactored for better maintainability, error handling, and architecture.
Using CoinGecko API for market data.
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import logging
from datetime import datetime
import os
from collections import namedtuple
import pandas as pd
from pycoingecko import CoinGeckoAPI

from config import AppConfig
from services.market_data_service import MarketDataService
from services.signal_service import SignalService
from services.cache_service import CacheService
from utils.validators import InputValidator
from utils.exceptions import AppException, DataFetchError, ValidationError
from utils.response_formatter import ResponseFormatter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MarketDataService:
    """Service for fetching market data from CoinGecko API."""

    def __init__(self, config, cache_service):
        self.cg = CoinGeckoAPI(base_url="https://api.coingecko.com/api/v3")
        self.cache_service = cache_service
        self.config = config

    def health_check(self):
        return {"status": "healthy"}

    def get_supported_coins(self):
        cache_key = "supported_coins"
        cached = self.cache_service.get(cache_key)
        if cached:
            return cached
        coins = self.cg.get_coins_list()
        supported = [coin['id'] for coin in coins]
        self.cache_service.set(cache_key, supported)
        return supported

    def get_supported_exchanges(self):
        cache_key = "supported_exchanges"
        cached = self.cache_service.get(cache_key)
        if cached:
            return cached
        exchanges = self.cg.get_exchanges_list()
        supported = [ex['id'] for ex in exchanges]
        self.cache_service.set(cache_key, supported)
        return supported

    def get_realtime_data(self, coin_id):
        price_data = self.cg.get_price(coin_id, vs_currencies='usd', include_market_cap=True, include_24hr_vol=True, include_24hr_change=True)
        return {
            'price': price_data[coin_id]['usd'],
            'market_cap': price_data[coin_id].get('usd_market_cap'),
            'volume_24h': price_data[coin_id].get('usd_24h_vol'),
            'change_24h': price_data[coin_id].get('usd_24h_change')
        }

    def get_market_data(self, coin_id, days, exchange=None):
        cache_key = f"market_data_{coin_id}_{days}"
        cached = self.cache_service.get(cache_key)
        if cached:
            return cached

        raw_ohlc = self.cg.get_coin_ohlc_by_id(id=coin_id, vs_currency='usd', days=days)
        df_ohlc = pd.DataFrame(raw_ohlc, columns=["timestamp", "open", "high", "low", "close"])
        df_ohlc["timestamp"] = pd.to_datetime(df_ohlc["timestamp"], unit="ms", utc=True)
        df_ohlc.set_index("timestamp", inplace=True)

        raw_market = self.cg.get_coin_market_chart_by_id(id=coin_id, vs_currency='usd', days=days)
        df_volume = pd.DataFrame(raw_market['total_volumes'], columns=["timestamp", "volume"])
        df_volume["timestamp"] = pd.to_datetime(df_volume["timestamp"], unit="ms", utc=True)
        df_volume.set_index("timestamp", inplace=True)

        df_market_cap = pd.DataFrame(raw_market['market_caps'], columns=["timestamp", "market_cap"])
        df_market_cap["timestamp"] = pd.to_datetime(df_market_cap["timestamp"], unit="ms", utc=True)
        df_market_cap.set_index("timestamp", inplace=True)

        df = df_ohlc.join(df_volume, how='inner').join(df_market_cap, how='inner')

        if days <= 90:
            df = df.resample('D').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum',
                'market_cap': 'last'
            }).dropna()

        MarketData = namedtuple('MarketData', ['df'])
        market_data = MarketData(df=df)

        self.cache_service.set(cache_key, market_data)
        return market_data

    def get_volume_data(self, coin_id, days):
        raw_market = self.cg.get_coin_market_chart_by_id(id=coin_id, vs_currency='usd', days=days)
        volumes = raw_market['total_volumes']
        df_vol = pd.DataFrame(volumes, columns=["timestamp", "volume"])
        df_vol["timestamp"] = pd.to_datetime(df_vol["timestamp"], unit="ms", utc=True)
        df_vol.set_index("timestamp", inplace=True)
        if days <= 90:
            df_vol = df_vol.resample('D').sum().dropna()
        return df_vol.reset_index().to_dict(orient='records')

class CryptoTradingApp:
    """Main application class for crypto trading signal analysis."""

    def __init__(self, config=None):
        self.config = config or AppConfig()
        self.app = Flask(__name__, template_folder='templates')
        import secrets
        self.app.secret_key = os.environ.get("SESSION_SECRET") or secrets.token_urlsafe(32)
        if not os.environ.get("SESSION_SECRET"):
            logger.warning("Using auto-generated session secret - set SESSION_SECRET env var for production")
        CORS(self.app)

        # Initialize services
        self.cache_service = CacheService(ttl=self.config.CACHE_TTL)
        self.market_data_service = MarketDataService(self.config, self.cache_service)
        self.signal_service = SignalService(self.config)
        self.validator = InputValidator()
        self.response_formatter = ResponseFormatter()

        self._register_routes()
        self._register_error_handlers()
        logger.info("Crypto Trading Application initialized successfully")

    def _register_routes(self):
        """Register all application routes."""

        # Page routes
        self.app.route('/')(self.index)
        self.app.route('/group1')(self.group1)
        self.app.route('/group2')(self.group2)
        self.app.route('/group3')(self.group3)
        self.app.route('/group4')(self.group4)
        self.app.route('/macd-rsi')(self.macd_rsi)

        # API routes
        self.app.route('/api/data', methods=['GET'])(self.api_get_data)
        self.app.route('/api/coins', methods=['GET'])(self.api_get_coins)
        self.app.route('/api/exchanges', methods=['GET'])(self.api_get_exchanges)
        self.app.route('/api/chainlink-volume', methods=['GET'])(self.api_get_volume)
        self.app.route('/api/refresh', methods=['POST'])(self.api_refresh)
        self.app.route('/api/health', methods=['GET'])(self.api_health)

    def _register_error_handlers(self):
        """Register error handlers for the application."""

        @self.app.errorhandler(ValidationError)
        def handle_validation_error(e):
            logger.warning(f"Validation error: {str(e)}")
            return jsonify({
                "error": "Invalid input parameters",
                "message": str(e)
            }), 400

        @self.app.errorhandler(DataFetchError)
        def handle_data_fetch_error(e):
            logger.error(f"Data fetch error: {str(e)}")
            return jsonify({
                "error": "Failed to fetch market data",
                "message": str(e)
            }), 503

        @self.app.errorhandler(AppException)
        def handle_app_exception(e):
            logger.error(f"Application error: {str(e)}")
            return jsonify({
                "error": "Internal application error",
                "message": str(e)
            }), 500

        @self.app.errorhandler(Exception)
        def handle_generic_error(e):
            logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
            return jsonify({
                "error": "Internal server error",
                "message": "An unexpected error occurred"
            }), 500

    # Page routes
    def index(self):
        """Main dashboard page."""
        return render_template('index.html')

    def group1(self):
        """Core Mix indicators page."""
        return render_template('group1.html')

    def group2(self):
        """Volatility Gauges indicators page."""
        return render_template('group2.html')

    def group3(self):
        """Momentum & Trend indicators page."""
        return render_template('group3.html')

    def group4(self):
        """Range & Breakout indicators page."""
        return render_template('group4.html')

    def macd_rsi(self):
        """MACD & RSI buy/sell signals page."""
        return render_template('macd-rsi.html')

    # API routes
    def api_get_data(self):
        """API endpoint to fetch cryptocurrency data and signals."""
        try:
            # Validate and extract parameters
            params = self.validator.validate_data_request(request.args)

            # Fetch market data
            market_data = self.market_data_service.get_market_data(
                coin_id=params['coin_id'],
                days=params['days'],
                exchange=params['exchange']
            )

            # Calculate signals
            signals = self.signal_service.calculate_signals(
                market_data.df,
                signal_group=params['group']
            )

            # Get real-time data
            realtime_data = self.market_data_service.get_realtime_data(params['coin_id'])

            # Format response
            response_data = self.response_formatter.format_market_response(
                market_data=market_data,
                signals=signals,
                realtime_data=realtime_data,
                coin_id=params['coin_id']
            )

            logger.info(f"Successfully fetched data for {params['coin_id']}")
            return jsonify(response_data)

        except (ValidationError, DataFetchError, AppException):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in api_get_data: {str(e)}", exc_info=True)
            raise AppException(f"Failed to process data request: {str(e)}")

    def api_get_coins(self):
        """API endpoint to fetch list of supported cryptocurrencies."""
        try:
            coins = self.market_data_service.get_supported_coins()
            logger.info(f"Retrieved {len(coins)} supported coins")
            return jsonify(coins)
        except Exception as e:
            logger.error(f"Error fetching coins list: {str(e)}")
            raise AppException(f"Failed to fetch supported coins: {str(e)}")

    def api_get_exchanges(self):
        """API endpoint to fetch list of supported exchanges."""
        try:
            exchanges = self.market_data_service.get_supported_exchanges()
            return jsonify(exchanges)
        except Exception as e:
            logger.error(f"Error fetching exchanges: {str(e)}")
            raise AppException(f"Failed to fetch supported exchanges: {str(e)}")

    def api_get_volume(self):
        """API endpoint to fetch volume data."""
        try:
            days = self.validator.validate_integer_param(
                request.args.get('days', 20), 'days', 1, 365
            )
            volume_data = self.market_data_service.get_volume_data('chainlink', days)
            return jsonify(volume_data)
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error fetching volume data: {str(e)}")
            return jsonify({
                "error": str(e),
                "volume_data": []
            }), 200

    def api_refresh(self):
        """API endpoint to force refresh cached data."""
        try:
            self.cache_service.clear_all()
            logger.info("Cache cleared successfully")
            return jsonify({"message": "Cache cleared successfully"})
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            raise AppException(f"Failed to clear cache: {str(e)}")

    def api_health(self):
        """Health check endpoint."""
        try:
            health_status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "services": {
                    "cache": self.cache_service.health_check(),
                    "market_data": self.market_data_service.health_check(),
                    "signals": self.signal_service.health_check()
                }
            }
            all_healthy = all(
                service["status"] == "healthy"
                for service in health_status["services"].values()
            )
            if not all_healthy:
                health_status["status"] = "degraded"
                return jsonify(health_status), 503
            return jsonify(health_status)
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 503

    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Run the Flask application."""
        logger.info(f"Starting application on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

def create_app(config=None):
    """Application factory function."""
    app_instance = CryptoTradingApp(config)
    return app_instance.app

application = create_app()  # For gunicorn deployment

if __name__ == '__main__':
    config = AppConfig()
    crypto_app = CryptoTradingApp(config)
    crypto_app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG
    )
