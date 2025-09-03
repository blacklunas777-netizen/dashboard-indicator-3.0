from cachetools import TTLCache

class CacheService:
    """Simple in-memory cache service with TTL."""
    
    def __init__(self, ttl: int = 300):
        self.cache = TTLCache(maxsize=100, ttl=ttl)
    
    def get(self, key):
        return self.cache.get(key)
    
    def set(self, key, value):
        self.cache[key] = value
    
    def clear_all(self):
        self.cache.clear()
    
    def health_check(self):
        return {"status": "healthy"}
