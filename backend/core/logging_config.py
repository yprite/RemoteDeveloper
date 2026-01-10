"""
Logging Configuration Module - In-memory log storage and handlers.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any

# In-memory log storage
logs: List[Dict[str, Any]] = []
logs: List[Dict[str, Any]] = []
MAX_LOGS = 200

# Global logger instance
logger = logging.getLogger("ai_dev_team")


# 로그에서 제외할 경로들 (프론트엔드 폴링 API)
EXCLUDED_PATHS = [
    '/agent/logs',
    '/queues', 
    '/pending',
]


class AccessLogFilter(logging.Filter):
    """특정 경로에 대한 access log를 필터링"""
    
    def filter(self, record):
        # uvicorn access log 메시지에서 경로 확인
        message = record.getMessage()
        for path in EXCLUDED_PATHS:
            if f'"{path}' in message or f' {path} ' in message:
                return False  # 이 로그는 출력하지 않음
        return True  # 다른 로그는 출력

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

    # uvicorn.access 로거에 필터 추가 (폴링 API 로그 제외)
    access_filter = AccessLogFilter()
    logging.getLogger("uvicorn.access").addFilter(access_filter)

def get_logs() -> List[Dict[str, Any]]:
    """Get all stored logs."""
    return logs
