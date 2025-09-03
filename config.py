import os

class AppConfig:
    """Application configuration loaded from environment variables."""

    def __init__(self):
        self.CACHE_TTL = int(os.environ.get('CACHE_TTL', 300))  # 5 minutes default
        self.HOST = os.environ.get('HOST', '0.0.0.0')
        self.PORT = int(os.environ.get('PORT', 5000))
        # Improved boolean parsing for DEBUG
        self.DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')
