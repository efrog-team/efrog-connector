from redis import Redis
from config import config, cache_config

cache: Redis = Redis(**cache_config)

for key, value in config.items():
    if key.startswith('CACHE_SET_') and cache.get(key[10:].lower()) is None:
        cache.set(key[10:].lower(), str(value))