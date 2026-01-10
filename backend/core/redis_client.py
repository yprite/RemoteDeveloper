"""
Redis Client Module - Handles Redis connection and queue operations.
"""
import json
import logging
from typing import Optional, Dict, Any

import redis

logger = logging.getLogger(__name__)

# Global Redis client
_redis_client: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    """Get the global Redis client instance."""
    global _redis_client
    return _redis_client


def init_redis(host: str = 'localhost', port: int = 6379, db: int = 0) -> Optional[redis.Redis]:
    """
    Initialize Redis connection.
    
    Returns:
        Redis client if connection successful, None otherwise
    """
    global _redis_client
    try:
        _redis_client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        _redis_client.ping()
        logger.info("[REDIS] Connected successfully")
        return _redis_client
    except Exception as e:
        logger.error(f"[REDIS] Connection failed: {e}")
        _redis_client = None
        return None


def push_event(queue_name: str, event: Dict[str, Any]) -> bool:
    """
    Push an event to a Redis queue.
    
    Args:
        queue_name: Name of the queue (e.g., "queue:REQUIREMENT")
        event: Event data as dictionary
        
    Returns:
        True if successful, False otherwise
    """
    from core.logging_config import add_log
    
    r = get_redis()
    if r:
        r.rpush(queue_name, json.dumps(event))
        add_log("SYSTEM", f"Pushed event to {queue_name}", "info")
        return True
    else:
        add_log("SYSTEM", "Redis not available", "failed")
        return False


def pop_event(queue_name: str) -> Optional[Dict[str, Any]]:
    """
    Pop an event from a Redis queue.
    
    Args:
        queue_name: Name of the queue
        
    Returns:
        Event as dictionary if available, None otherwise
    """
    r = get_redis()
    if r:
        item = r.lpop(queue_name)
        if item:
            return json.loads(item)
    return None
