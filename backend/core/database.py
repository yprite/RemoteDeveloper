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
    
    # Task History table (NEW)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            task_id TEXT PRIMARY KEY,
            original_prompt TEXT,
            status TEXT DEFAULT 'PENDING',
            current_stage TEXT DEFAULT 'REQUIREMENT',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME
        )
    """)
    
    # Task Events table (NEW)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            agent TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES task_history(task_id)
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


# =============================================================================
# TASK HISTORY CRUD (NEW)
# =============================================================================

def create_task(task_id: str, original_prompt: str) -> bool:
    """Create a new task record."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO task_history (task_id, original_prompt) VALUES (?, ?)
        """, (task_id, original_prompt))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def update_task_status(task_id: str, status: str, current_stage: str = None):
    """Update task status and optionally current stage."""
    conn = get_connection()
    cursor = conn.cursor()
    if current_stage:
        cursor.execute("""
            UPDATE task_history SET status = ?, current_stage = ? WHERE task_id = ?
        """, (status, current_stage, task_id))
    else:
        cursor.execute("""
            UPDATE task_history SET status = ? WHERE task_id = ?
        """, (status, task_id))
    if status == "COMPLETED" or status == "FAILED":
        cursor.execute("""
            UPDATE task_history SET completed_at = CURRENT_TIMESTAMP WHERE task_id = ?
        """, (task_id,))
    conn.commit()


def add_task_event(task_id: str, agent: str, status: str, message: str = None):
    """Add an event to task history."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO task_events (task_id, agent, status, message) VALUES (?, ?, ?, ?)
    """, (task_id, agent, status, message))
    conn.commit()


def get_tasks(limit: int = 50) -> List[Dict]:
    """Get recent tasks."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM task_history ORDER BY created_at DESC LIMIT ?
    """, (limit,))
    return [dict(row) for row in cursor.fetchall()]


def get_task_detail(task_id: str) -> Optional[Dict]:
    """Get task with all its events."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM task_history WHERE task_id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        return None
    
    cursor.execute("""
        SELECT * FROM task_events WHERE task_id = ? ORDER BY created_at ASC
    """, (task_id,))
    events = [dict(row) for row in cursor.fetchall()]
    
    result = dict(task)
    result["events"] = events
    return result
