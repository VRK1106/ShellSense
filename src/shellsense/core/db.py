import os
import sqlite3
from typing import Optional, List, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal
from shellsense.core.config import USER_DIR
from shellsense.core.logger import logger

DEFAULT_DB_PATH = os.path.join(USER_DIR, "shellsense.db")


class DatabaseManager(QObject):
    """
    Thread-safe SQLite persistence manager for ShellSense.
    Maintains vault passwords, file shortcuts, and terminal commands
    with indexing and emits PyQt signals on database persistence.
    """
    entry_persisted = pyqtSignal(str, str, str)  # (category, key, value)
    _instance: Optional['DatabaseManager'] = None

    def __init__(self, db_path: Optional[str] = None):
        super().__init__()
        self.db_path = db_path or DEFAULT_DB_PATH
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        self.init_schema()

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> 'DatabaseManager':
        if cls._instance is None or (db_path and cls._instance.db_path != db_path):
            cls._instance = DatabaseManager(db_path)
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self):
        """Initializes tables and indexes for vault_passwords, file_shortcuts, and terminal_commands."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. vault_passwords table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vault_passwords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_name TEXT UNIQUE NOT NULL,
                    encrypted_value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vault_key 
                ON vault_passwords(key_name);
            """)

            # 2. file_shortcuts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_shortcuts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    shortcut_name TEXT UNIQUE NOT NULL,
                    file_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_shortcut_name 
                ON file_shortcuts(shortcut_name);
            """)

            # 3. terminal_commands table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS terminal_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command_name TEXT UNIQUE NOT NULL,
                    command_string TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_terminal_cmd_name 
                ON terminal_commands(command_name);
            """)

            conn.commit()
            logger.info(f"Database schema initialized at {self.db_path}")

    # --- Write / Persist API ---

    def save_entry(self, category: str, key: str, value: str) -> bool:
        """
        Persists an entry into the respective SQLite table based on category.
        Emits entry_persisted signal upon successful commit.
        """
        norm_cat = (category or "").lower().strip()
        key = (key or "").strip()
        value = (value or "").strip()

        if not key or not value:
            logger.warning(f"Skipping save_entry: invalid key='{key}' or value='{value}'")
            return False

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                if norm_cat in ("password", "vault"):
                    cursor.execute("""
                        INSERT INTO vault_passwords (key_name, encrypted_value, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(key_name) DO UPDATE SET 
                            encrypted_value = excluded.encrypted_value,
                            updated_at = CURRENT_TIMESTAMP;
                    """, (key, value))

                elif norm_cat in ("file", "shortcut"):
                    cursor.execute("""
                        INSERT INTO file_shortcuts (shortcut_name, file_path, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(shortcut_name) DO UPDATE SET 
                            file_path = excluded.file_path,
                            updated_at = CURRENT_TIMESTAMP;
                    """, (key, value))

                elif norm_cat in ("command", "cmd", "terminal"):
                    cursor.execute("""
                        INSERT INTO terminal_commands (command_name, command_string, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(command_name) DO UPDATE SET 
                            command_string = excluded.command_string,
                            updated_at = CURRENT_TIMESTAMP;
                    """, (key, value))

                else:
                    logger.error(f"Unknown category for persistence: {category}")
                    return False

                conn.commit()

            # Emit PyQt signal to notify all listening UI tab views
            self.entry_persisted.emit(norm_cat, key, value)
            logger.info(f"Successfully persisted entry to SQLite: [{norm_cat}] {key}")
            return True

        except Exception as e:
            logger.error(f"Error saving entry to SQLite ({norm_cat}, {key}): {e}")
            return False

    # --- Query API ---

    def get_vault_passwords(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, key_name, encrypted_value, created_at, updated_at FROM vault_passwords ORDER BY updated_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_file_shortcuts(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, shortcut_name, file_path, created_at, updated_at FROM file_shortcuts ORDER BY updated_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_terminal_commands(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, command_name, command_string, created_at, updated_at FROM terminal_commands ORDER BY updated_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_entry(self, category: str, key: str) -> Optional[Dict[str, Any]]:
        norm_cat = (category or "").lower().strip()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if norm_cat in ("password", "vault"):
                cursor.execute("SELECT * FROM vault_passwords WHERE key_name = ?", (key,))
            elif norm_cat in ("file", "shortcut"):
                cursor.execute("SELECT * FROM file_shortcuts WHERE shortcut_name = ?", (key,))
            elif norm_cat in ("command", "cmd", "terminal"):
                cursor.execute("SELECT * FROM terminal_commands WHERE command_name = ?", (key,))
            else:
                return None
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_entry(self, category: str, key: str) -> bool:
        norm_cat = (category or "").lower().strip()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if norm_cat in ("password", "vault"):
                cursor.execute("DELETE FROM vault_passwords WHERE key_name = ?", (key,))
            elif norm_cat in ("file", "shortcut"):
                cursor.execute("DELETE FROM file_shortcuts WHERE shortcut_name = ?", (key,))
            elif norm_cat in ("command", "cmd", "terminal"):
                cursor.execute("DELETE FROM terminal_commands WHERE command_name = ?", (key,))
            else:
                return False
            conn.commit()
            return cursor.rowcount > 0
