# Crypto Trading Signal Analysis

This is a Flask-based web application for analyzing cryptocurrency trading signals using data from the CoinGecko API and many more   
It provides API endpoints for fetching market data, calculating indicators (RSI, MACD, SMA, Bollinger Bands), and serving HTML pages for visualization with interactive charts.

## Features
- Fetches daily OHLCV data from CoinGecko.
- Calculates standard trading indicators without custom scaling.
- Supports caching for performance.
- API endpoints for data, coins, exchanges, volume, refresh, and health checks.
- Simple HTML templates for different indicator groups.
- Interactive charts powered by Chart.js for all indicator groups.
