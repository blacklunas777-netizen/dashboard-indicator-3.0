"""
Cryptocurrency Trading Signal Analysis Application
Refactored for better maintainability, error handling, and architecture.
Using CoinGecko API and others for market data.
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import logging
from datetime import datetime
import os
import secrets

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

class CryptoTradingApp:
    """Main application class for crypto trading signal analysis."""

    def __init__(self, config=None):
        self.config = config or AppConfig()
        self.app = Flask(__name__, template_folder='templates')
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
        self.app.add_url_rule('/', view_func=self.index)
        self.app.add_url_rule('/group1', view_func=self.group1)
        self.app.add_url_rule('/group2', view_func=self.group2)
        self.app.add_url_rule('/group3', view_func=self.group3)
        self.app.add_url_rule('/group4', view_func=self.group4)
        self.app.add_url_rule('/macd-rsi', view_func=self.macd_rsi)

        self.app.add_url_rule('/api/data', view_func=self.api_get_data, methods=['GET'])
        self.app.add_url_rule('/api/coins', view_func=self.api_get_coins, methods=['GET'])
        self.app.add_url_rule('/api/exchanges', view_func=self.api_get_exchanges, methods=['GET'])
        self.app.add_url_rule('/api/chainlink-volume', view_func=self.api_get_volume, methods=['GET'])
        self.app.add_url_rule('/api/refresh', view_func=self.api_refresh, methods=['POST'])
        self.app.add_url_rule('/api/health', view_func=self.api_health, methods=['GET'])

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
        return render_template('index.html')
    def group1(self):
        return render_template('group1.html')
    def group2(self):
        return render_template('group2.html')
    def group3(self):
        return render_template('group3.html')
    def group4(self):
        return render_template('group4.html')
    def macd_rsi(self):
        return render_template('macd-rsi.html')

    # API routes
    def api_get_data(self):
        try:
            params = self.validator.validate_data_request(request.args)
            market_data = self.market_data_service.get_market_data(
                coin_id=params['coin_id'],
                days=params['days'],
                exchange=params.get('exchange')
            )
            signals = self.signal_service.calculate_signals(
                market_data.df,
                signal_group=params['group']
            )
            realtime_data = self.market_data_service.get_realtime_data(params['coin_id'])
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
        try:
            coins = self.market_data_service.get_supported_coins()
            logger.info(f"Retrieved {len(coins)} supported coins")
            return jsonify(coins)
        except Exception as e:
            logger.error(f"Error fetching coins list: {str(e)}")
            raise AppException(f"Failed to fetch supported coins: {str(e)}")

    def api_get_exchanges(self):
        try:
            exchanges = self.market_data_service.get_supported_exchanges()
            return jsonify(exchanges)
        except Exception as e:
            logger.error(f"Error fetching exchanges: {str(e)}")
            raise AppException(f"Failed to fetch supported exchanges: {str(e)}")

    def api_get_volume(self):
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
        try:
            self.cache_service.clear_all()
            logger.info("Cache cleared successfully")
            return jsonify({"message": "Cache cleared successfully"})
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            raise AppException(f"Failed to clear cache: {str(e)}")

    def api_health(self):
        try:
            health_status = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
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
                "timestamp": datetime.utcnow().isoformat()
            }), 503

    def run(self, host='0.0.0.0', port=5000, debug=False):
        logger.info(f"Starting application on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

def create_app(config=None):
    """Application factory function."""
    # Here you can check for API keys and log warnings if some are missing
    app_instance = CryptoTradingApp(config)
    return app_instance.app

# This is the entrypoint Gunicorn expects
application = create_app()

if __name__ == '__main__':
    config = AppConfig()
    crypto_app = CryptoTradingApp(config)
    crypto_app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG
    )
