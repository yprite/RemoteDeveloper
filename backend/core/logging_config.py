"""
Logging Configuration Module - In-memory log storage and file logging for errors.
"""
import logging
import os
from datetime import datetime
from typing import List, Dict, Any
from logging.handlers import RotatingFileHandler
import re

# In-memory log storage
logs: List[Dict[str, Any]] = []
MAX_LOGS = 200

# Log directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Global logger instance
logger = logging.getLogger("ai_dev_team")


# 로그에서 제외할 경로들 (프론트엔드 폴링 API)
EXCLUDED_PATHS = [
    '/agent/logs',
    '/queues', 
    '/pending',
    '/metrics',
]


class ErrorOnlyFilter(logging.Filter):
    """Filter that only allows ERROR/CRITICAL or non-200 HTTP responses."""
    
    # Pattern to match HTTP status codes in uvicorn access logs
    HTTP_STATUS_PATTERN = re.compile(r'HTTP/\d\.\d" (\d{3})')
    
    def filter(self, record):
        # Always allow ERROR and CRITICAL
        if record.levelno >= logging.ERROR:
            return True
        
        # Check for non-200 HTTP status in access logs
        message = record.getMessage()
        match = self.HTTP_STATUS_PATTERN.search(message)
        if match:
            status_code = int(match.group(1))
            if status_code != 200:
                return True
        
        return False


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
    
    # Also log errors to file via standard logging
    if status == "failed":
        logger.error(f"[{agent}] {message}")


def setup_logging() -> None:
    """Setup logging with in-memory handler and file handler for errors."""
    # In-memory handler (all logs for dashboard)
    memory_handler = InMemoryLogHandler()
    memory_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    memory_handler.setFormatter(memory_formatter)
    
    # File handler (errors and non-200 only)
    log_file = os.path.join(LOG_DIR, "error.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(ErrorOnlyFilter())
    
    # Add handlers to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(memory_handler)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)
    
    # Add handlers to uvicorn loggers
    logging.getLogger("uvicorn").addHandler(memory_handler)
    logging.getLogger("uvicorn").addHandler(file_handler)
    logging.getLogger("uvicorn.access").addHandler(memory_handler)
    logging.getLogger("uvicorn.access").addHandler(file_handler)
    
    # uvicorn.access 로거에 필터 추가 (폴링 API 로그 제외 - 메모리용)
    access_filter = AccessLogFilter()
    logging.getLogger("uvicorn.access").addFilter(access_filter)
    
    logger.info(f"File logging enabled: {log_file} (errors and non-200 only)")


def get_logs() -> List[Dict[str, Any]]:
    """Get all stored logs."""
    return logs
