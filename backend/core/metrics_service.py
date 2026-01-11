import time
import json
import logging
from typing import Dict, Any, Optional, List
from core.redis_client import get_redis

logger = logging.getLogger("metrics")

class MetricsService:
    """Service for storing and retrieving agent performance metrics."""
    
    METRICS_KEY_PREFIX = "metrics:agent:"
    IMPROVEMENTS_KEY = "metrics:improvements"
    
    def __init__(self):
        self.redis = None
    
    def _get_redis(self):
        if not self.redis:
            self.redis = get_redis()
        return self.redis
    
    def record_task(self, agent_name: str, success: bool, duration_ms: int, details: Optional[str] = None):
        """Record a task execution for an agent."""
        r = self._get_redis()
        key = f"{self.METRICS_KEY_PREFIX}{agent_name}"
        
        # Get current stats
        stats = self.get_agent_stats(agent_name)
        
        # Update counters
        stats["total"] = stats.get("total", 0) + 1
        if success:
            stats["success"] = stats.get("success", 0) + 1
        else:
            stats["fail"] = stats.get("fail", 0) + 1
        
        # Update average duration (running average)
        old_avg = stats.get("avg_duration_ms", 0)
        old_count = stats["total"] - 1
        if old_count > 0:
            stats["avg_duration_ms"] = int((old_avg * old_count + duration_ms) / stats["total"])
        else:
            stats["avg_duration_ms"] = duration_ms
        
        stats["last_updated"] = time.time()
        
        # Store
        r.set(key, json.dumps(stats))
        logger.info(f"Recorded metric for {agent_name}: success={success}, duration={duration_ms}ms")
    
    def get_agent_stats(self, agent_name: str) -> Dict[str, Any]:
        """Get statistics for a specific agent."""
        r = self._get_redis()
        key = f"{self.METRICS_KEY_PREFIX}{agent_name}"
        data = r.get(key)
        if data:
            return json.loads(data)
        return {"total": 0, "success": 0, "fail": 0, "avg_duration_ms": 0}
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all agents."""
        r = self._get_redis()
        result = {}
        
        # Scan for all metric keys
        for key in r.scan_iter(f"{self.METRICS_KEY_PREFIX}*"):
            agent_name = key.decode().replace(self.METRICS_KEY_PREFIX, "")
            result[agent_name] = self.get_agent_stats(agent_name)
        
        return result
    
    def store_improvement(self, improvement: str):
        """Store an improvement suggestion."""
        r = self._get_redis()
        r.lpush(self.IMPROVEMENTS_KEY, improvement)
        # Keep only last 50 improvements
        r.ltrim(self.IMPROVEMENTS_KEY, 0, 49)
    
    def get_improvements(self, limit: int = 10) -> List[str]:
        """Get recent improvement suggestions."""
        r = self._get_redis()
        items = r.lrange(self.IMPROVEMENTS_KEY, 0, limit - 1)
        return [item.decode() for item in items]
    
    def clear_stats(self, agent_name: Optional[str] = None):
        """Clear statistics for an agent or all agents."""
        r = self._get_redis()
        if agent_name:
            r.delete(f"{self.METRICS_KEY_PREFIX}{agent_name}")
        else:
            for key in r.scan_iter(f"{self.METRICS_KEY_PREFIX}*"):
                r.delete(key)
