import json
import os
from .config import SNIPPETS_PATH, FILE_SHORTCUTS_PATH, COMMANDS_PATH

class ConfigManager:
    @staticmethod
    def read_json(path):
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading {path}: {e}")
            return {}

    @staticmethod
    def write_json(path, data):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"Error writing {path}: {e}")
            return False

    @classmethod
    def get_snippets(cls):
        return cls.read_json(SNIPPETS_PATH)

    @classmethod
    def update_snippets(cls, data):
        return cls.write_json(SNIPPETS_PATH, data)

    @classmethod
    def get_shortcuts(cls):
        return cls.read_json(FILE_SHORTCUTS_PATH)

    @classmethod
    def update_shortcuts(cls, data):
        return cls.write_json(FILE_SHORTCUTS_PATH, data)

    @classmethod
    def get_commands(cls):
        return cls.read_json(COMMANDS_PATH)

    @classmethod
    def update_commands(cls, data):
        # We also need to update the in-memory config for runtime
        import src.shellsense.core.config as config
        success = cls.write_json(COMMANDS_PATH, data)
        if success:
            config.SAFE_COMMANDS = data
        return success
