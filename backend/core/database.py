"""
Database Module - SQLite3 database for persistent settings and configuration.
"""
import sqlite3
import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger("database")

# Database path
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DATA_DIR, "settings.db")

# Global connection
_connection: Optional[sqlite3.Connection] = None


def get_connection() -> sqlite3.Connection:
    """Get the global database connection."""
    global _connection
    if _connection is None:
        os.makedirs(DATA_DIR, exist_ok=True)
        _connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        _connection.row_factory = sqlite3.Row
    return _connection


def init_database():
    """Initialize database tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Settings table (key-value store)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Repositories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repositories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            name TEXT,
            local_path TEXT,
            last_indexed DATETIME,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # LLM Settings table (per-agent adapter configuration)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS llm_settings (
            agent TEXT PRIMARY KEY,
            adapter TEXT NOT NULL DEFAULT 'openai',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    logger.info(f"Database initialized at {DB_PATH}")
    
    # Insert default LLM settings if not exists
    _insert_default_llm_settings(cursor)
    conn.commit()


def _insert_default_llm_settings(cursor):
    """Insert default LLM settings for all agents."""
    defaults = {
        "REQUIREMENT": "openai",
        "PLAN": "openai",
        "UXUI": "openai",
        "ARCHITECT": "openai",
        "CODE": "claude_cli",
        "REFACTORING": "cursor_cli",
        "TESTQA": "openai",
        "DOC": "openai",
        "RELEASE": "openai",
        "MONITORING": "openai",
        "EVALUATION": "openai",
    }
    for agent, adapter in defaults.items():
        cursor.execute("""
            INSERT OR IGNORE INTO llm_settings (agent, adapter) VALUES (?, ?)
        """, (agent, adapter))


# =============================================================================
# SETTINGS CRUD
# =============================================================================

def get_setting(key: str, default: Any = None) -> Any:
    """Get a setting value by key."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    if row:
        try:
            return json.loads(row["value"])
        except:
            return row["value"]
    return default


def set_setting(key: str, value: Any):
    """Set a setting value."""
    conn = get_connection()
    cursor = conn.cursor()
    value_str = json.dumps(value) if not isinstance(value, str) else value
    cursor.execute("""
        INSERT INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP
    """, (key, value_str, value_str))
    conn.commit()


# =============================================================================
# REPOSITORIES CRUD
# =============================================================================

def add_repository(url: str, name: Optional[str] = None) -> int:
    """Add a repository to track."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Extract name from URL if not provided
    if not name:
        name = url.rstrip("/").split("/")[-1].replace(".git", "")
    
    cursor.execute("""
        INSERT INTO repositories (url, name) VALUES (?, ?)
        ON CONFLICT(url) DO UPDATE SET name = ?, is_active = 1
    """, (url, name, name))
    conn.commit()
    return cursor.lastrowid


def get_repositories(active_only: bool = True) -> List[Dict]:
    """Get all tracked repositories."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if active_only:
        cursor.execute("SELECT * FROM repositories WHERE is_active = 1")
    else:
        cursor.execute("SELECT * FROM repositories")
    
    return [dict(row) for row in cursor.fetchall()]


def remove_repository(repo_id: int):
    """Deactivate a repository."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE repositories SET is_active = 0 WHERE id = ?", (repo_id,))
    conn.commit()


def update_repository_indexed(repo_id: int, local_path: str):
    """Update repository last indexed time."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE repositories SET last_indexed = CURRENT_TIMESTAMP, local_path = ? WHERE id = ?
    """, (local_path, repo_id))
    conn.commit()


# =============================================================================
# LLM SETTINGS CRUD
# =============================================================================

def get_llm_settings() -> Dict[str, str]:
    """Get all LLM settings."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT agent, adapter FROM llm_settings")
    return {row["agent"]: row["adapter"] for row in cursor.fetchall()}


def set_llm_setting(agent: str, adapter: str):
    """Set LLM adapter for an agent."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO llm_settings (agent, adapter, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(agent) DO UPDATE SET adapter = ?, updated_at = CURRENT_TIMESTAMP
    """, (agent, adapter, adapter))
    conn.commit()


def set_llm_settings_bulk(settings: Dict[str, str]):
    """Set multiple LLM settings at once."""
    conn = get_connection()
    cursor = conn.cursor()
    for agent, adapter in settings.items():
        cursor.execute("""
            INSERT INTO llm_settings (agent, adapter, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(agent) DO UPDATE SET adapter = ?, updated_at = CURRENT_TIMESTAMP
        """, (agent, adapter, adapter))
    conn.commit()
