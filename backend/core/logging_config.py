"""
Logging Configuration Module - In-memory log storage and handlers.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any

# In-memory log storage
logs: List[Dict[str, Any]] = []
MAX_LOGS = 200


class InMemoryLogHandler(logging.Handler):
    """Custom log handler that stores logs in memory for API access."""
    
    def emit(self, record):
        try:
            msg = self.format(record)
            level = record.levelname.lower()
            status = "info"
            if level in ["warning"]:
                status = "pending"
            if level in ["error", "critical"]:
                status = "failed"
            
            entry = {
                "timestamp": datetime.now().isoformat(),
                "agent": "SYSTEM",
                "message": msg,
                "status": status
            }
            logs.append(entry)
            if len(logs) > MAX_LOGS:
                logs.pop(0)
        except Exception:
            self.handleError(record)


def add_log(agent: str, message: str, status: str = "info") -> None:
    """
    Add a log entry to the in-memory log storage.
    
    Args:
        agent: Agent name (e.g., "SYSTEM", "REQUIREMENT", etc.)
        message: Log message
        status: Status indicator ("info", "success", "pending", "failed")
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent,
        "message": message,
        "status": status
    }
    logs.append(entry)
    if len(logs) > MAX_LOGS:
        logs.pop(0)


def setup_logging() -> None:
    """Setup logging with the in-memory handler."""
    log_handler = InMemoryLogHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_handler.setFormatter(formatter)
    
    # Add handler to root logger and uvicorn loggers
    logging.getLogger().addHandler(log_handler)
    logging.getLogger("uvicorn").addHandler(log_handler)
    logging.getLogger("uvicorn.access").addHandler(log_handler)
    logging.getLogger().setLevel(logging.INFO)


def get_logs() -> List[Dict[str, Any]]:
    """Get all stored logs."""
    return logs
