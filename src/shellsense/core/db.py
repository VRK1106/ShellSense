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
        if self.db_path == DEFAULT_DB_PATH:
            self.sync_with_json_files()

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

    # --- Unified Memory Synchronization ---

    def sync_with_json_files(self):
        """
        Bidirectionally unifies SQLite memory with local JSON files:
        1. Migrates existing items from snippets.json, file_shortcuts.json, and commands.json into SQLite.
        2. Ensures any new AI-generated or SQLite-stored items are written into the JSON files.
        """
        import json
        from shellsense.core.config import SNIPPETS_PATH, FILE_SHORTCUTS_PATH, COMMANDS_PATH

        # 1. Sync Vault / Snippets
        try:
            snippets_data = {}
            if os.path.exists(SNIPPETS_PATH):
                with open(SNIPPETS_PATH, "r", encoding="utf-8") as f:
                    snippets_data = json.load(f)

            existing_vault = {row["key_name"]: row["encrypted_value"] for row in self.get_vault_passwords()}

            # JSON -> SQLite
            for k, v in snippets_data.items():
                if k and v and k not in existing_vault:
                    self.save_entry("vault", k, str(v), sync_json=False)
                    existing_vault[k] = str(v)

            # SQLite -> JSON
            changed_snippets = False
            for k, v in existing_vault.items():
                if k not in snippets_data:
                    snippets_data[k] = v
                    changed_snippets = True

            if changed_snippets:
                with open(SNIPPETS_PATH, "w", encoding="utf-8") as f:
                    json.dump(snippets_data, f, indent=4)
        except Exception as e:
            logger.error(f"Error synchronizing snippets memory: {e}")

        # 2. Sync File Shortcuts
        try:
            shortcuts_data = {}
            if os.path.exists(FILE_SHORTCUTS_PATH):
                with open(FILE_SHORTCUTS_PATH, "r", encoding="utf-8") as f:
                    shortcuts_data = json.load(f)

            existing_shortcuts = {row["shortcut_name"]: row["file_path"] for row in self.get_file_shortcuts()}

            # JSON -> SQLite
            for k, v in shortcuts_data.items():
                if k and v and k not in existing_shortcuts:
                    self.save_entry("file", k, str(v), sync_json=False)
                    existing_shortcuts[k] = str(v)

            # SQLite -> JSON
            changed_shortcuts = False
            for k, v in existing_shortcuts.items():
                if k not in shortcuts_data:
                    shortcuts_data[k] = v
                    changed_shortcuts = True

            if changed_shortcuts:
                with open(FILE_SHORTCUTS_PATH, "w", encoding="utf-8") as f:
                    json.dump(shortcuts_data, f, indent=4)
        except Exception as e:
            logger.error(f"Error synchronizing file shortcuts memory: {e}")

        # 3. Sync Terminal Commands
        try:
            commands_data = {}
            if os.path.exists(COMMANDS_PATH):
                with open(COMMANDS_PATH, "r", encoding="utf-8") as f:
                    commands_data = json.load(f)

            existing_commands = {row["command_name"]: row["command_string"] for row in self.get_terminal_commands()}

            # JSON -> SQLite
            for k, v in commands_data.items():
                if not k or v is None:
                    continue
                cmd_str = " ".join(v) if isinstance(v, list) else str(v)
                if k not in existing_commands and cmd_str:
                    self.save_entry("command", k, cmd_str, sync_json=False)
                    existing_commands[k] = cmd_str

            # SQLite -> JSON
            changed_commands = False
            for k, v in existing_commands.items():
                if k not in commands_data:
                    commands_data[k] = v
                    changed_commands = True

            if changed_commands:
                with open(COMMANDS_PATH, "w", encoding="utf-8") as f:
                    json.dump(commands_data, f, indent=4)
        except Exception as e:
            logger.error(f"Error synchronizing terminal commands memory: {e}")

    def _sync_entry_to_json(self, norm_cat: str, key: str, value: str):
        try:
            import json
            from shellsense.core.config import SNIPPETS_PATH, FILE_SHORTCUTS_PATH, COMMANDS_PATH
            target_path = None
            if norm_cat in ("password", "vault"):
                target_path = SNIPPETS_PATH
            elif norm_cat in ("file", "shortcut"):
                target_path = FILE_SHORTCUTS_PATH
            elif norm_cat in ("command", "cmd", "terminal"):
                target_path = COMMANDS_PATH

            if target_path:
                data = {}
                if os.path.exists(target_path):
                    try:
                        with open(target_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    except Exception:
                        data = {}
                data[key] = value
                with open(target_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)

                # Keep SAFE_COMMANDS updated in memory
                if norm_cat in ("command", "cmd", "terminal"):
                    try:
                        import shellsense.core.config as config
                        config.SAFE_COMMANDS[key] = value
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Error syncing entry to JSON file: {e}")

    def _sync_delete_from_json(self, norm_cat: str, key: str):
        try:
            import json
            from shellsense.core.config import SNIPPETS_PATH, FILE_SHORTCUTS_PATH, COMMANDS_PATH
            target_path = None
            if norm_cat in ("password", "vault"):
                target_path = SNIPPETS_PATH
            elif norm_cat in ("file", "shortcut"):
                target_path = FILE_SHORTCUTS_PATH
            elif norm_cat in ("command", "cmd", "terminal"):
                target_path = COMMANDS_PATH

            if target_path and os.path.exists(target_path):
                data = {}
                try:
                    with open(target_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    return
                if key in data:
                    del data[key]
                    with open(target_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4)

                if norm_cat in ("command", "cmd", "terminal"):
                    try:
                        import shellsense.core.config as config
                        if key in config.SAFE_COMMANDS:
                            del config.SAFE_COMMANDS[key]
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Error syncing deletion to JSON file: {e}")

    # --- Write / Persist API ---

    def save_entry(self, category: str, key: str, value: str, sync_json: bool = True) -> bool:
        """
        Persists an entry into the respective SQLite table based on category.
        Emits entry_persisted signal upon successful commit.
        Automatically mirrors to local JSON memory when sync_json=True.
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

            # Mirror to JSON file if requested
            if sync_json:
                self._sync_entry_to_json(norm_cat, key, value)

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

    def delete_entry(self, category: str, key: str, sync_json: bool = True) -> bool:
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
            rowcount = cursor.rowcount

        if rowcount > 0 and sync_json:
            self._sync_delete_from_json(norm_cat, key)

        return rowcount > 0
