import redis
import logging


class RedisClient:
    _instance = None

    def __new__(cls, host="localhost", port=6379, db=0):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            try:
                cls._instance._client = redis.Redis(host=host, port=port, db=db)
                cls._instance._client.ping()
            except redis.ConnectionError as e:
                logging.error(f"Redis connection failed: {e}")
                cls._instance._client = None
        return cls._instance

    def get_client(self):
        return self._client
