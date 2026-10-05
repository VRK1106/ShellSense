import os
import sys

# Base paths
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    USER_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    USER_DIR = BASE_DIR

DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_PATH = os.path.join(BASE_DIR, "shellsense_v3.pkl")
FILE_SHORTCUTS_PATH = os.path.join(USER_DIR, "file_shortcuts.json")
SNIPPETS_PATH = os.path.join(USER_DIR, "snippets.json")
if getattr(sys, 'frozen', False):
    TIMERS_PATH = os.path.join(USER_DIR, "timers.json")
else:
    TIMERS_PATH = os.path.join(USER_DIR, "src", "timers.json")

COMMANDS_PATH = os.path.join(USER_DIR, "commands.json")

def load_safe_commands():
    import json
    if os.path.exists(COMMANDS_PATH):
        try:
            with open(COMMANDS_PATH, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading commands.json: {e}")
    return {}

SAFE_COMMANDS = load_safe_commands()

# Feedback Configuration (Centralized Google Sheets/Forms or local backup log)
FEEDBACK_URL = "https://docs.google.com/forms/u/0/d/e/1FAIpQLSeOPykvnD1_GHa5zGlvbbOlKBehc7FaOU_8Jm383SBfQwW-VQ/formResponse"
FEEDBACK_ENTRY_CATEGORY = "entry.1060351434"
FEEDBACK_ENTRY_QUERY = "entry.1031596501"
FEEDBACK_ENTRY_OUTPUT = "entry.55134923"
FEEDBACK_ENTRY_RATING = "entry.1053210131"
FEEDBACK_ENTRY_COMMENT = "entry.1635821479"
FEEDBACK_ENTRY_USER_NAME = "entry.2142960445"
FEEDBACK_ENTRY_USER_EMAIL = "entry.1486106542"


