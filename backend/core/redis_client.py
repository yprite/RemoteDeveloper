"""
Redis Client Module - Handles Redis connection and queue operations with schema validation.
"""
import json
import logging
from typing import Optional, Dict, Any, Union

import redis
from pydantic import ValidationError

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


def push_event(queue_name: str, event: Union[Dict[str, Any], "AgentEvent"]) -> bool:
    """
    Push an event to a Redis queue with schema validation.
    
    Args:
        queue_name: Name of the queue (e.g., "queue:REQUIREMENT")
        event: Event data as dictionary or AgentEvent model
        
    Returns:
        True if successful, False otherwise
    """
    from core.logging_config import add_log
    from core.schemas import AgentEvent
    
    r = get_redis()
    if not r:
        add_log("SYSTEM", "Redis not available", "failed")
        return False
    
    try:
        # Validate and convert to dict if needed
        if isinstance(event, dict):
            # Validate against schema
            validated = AgentEvent.from_dict(event)
            event_data = validated.to_dict()
        else:
            event_data = event.to_dict()
        
        r.rpush(queue_name, json.dumps(event_data))
        add_log("SYSTEM", f"Pushed event to {queue_name}", "info")
        return True
        
    except ValidationError as e:
        add_log("SYSTEM", f"Schema validation failed: {str(e)[:100]}", "failed")
        logger.error(f"Event validation failed: {e}")
        # Still push but log the error (for backward compatibility)
        r.rpush(queue_name, json.dumps(event if isinstance(event, dict) else event.to_dict()))
        return True
    except Exception as e:
        add_log("SYSTEM", f"Push failed: {str(e)[:50]}", "failed")
        logger.error(f"Push event failed: {e}")
        return False


def pop_event(queue_name: str, validate: bool = True) -> Optional[Dict[str, Any]]:
    """
    Pop an event from a Redis queue with optional schema validation.
    
    Args:
        queue_name: Name of the queue
        validate: Whether to validate against AgentEvent schema
        
    Returns:
        Event as dictionary if available, None otherwise
    """
    from core.schemas import AgentEvent
    
    r = get_redis()
    if not r:
        return None
    
    item = r.lpop(queue_name)
    if not item:
        return None
    
    try:
        event_data = json.loads(item)
        
        if validate:
            # Validate and return
            validated = AgentEvent.from_dict(event_data)
            return validated.to_dict()
        
        return event_data
        
    except ValidationError as e:
        logger.warning(f"Event validation warning: {e}")
        # Return raw data for backward compatibility
        return json.loads(item) if isinstance(item, str) else item
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode failed: {e}")
        return None

