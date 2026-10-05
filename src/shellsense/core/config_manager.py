import json
import os
import firebase_admin
from firebase_admin import credentials, firestore
from .config import SNIPPETS_PATH, FILE_SHORTCUTS_PATH, COMMANDS_PATH

# Initialize Firebase if credentials are provided in environment
FIREBASE_CREDENTIALS = os.environ.get("FIREBASE_CREDENTIALS")
db = None
if FIREBASE_CREDENTIALS:
    try:
        cred_dict = json.loads(FIREBASE_CREDENTIALS)
        cred = credentials.Certificate(cred_dict)
        # Check if already initialized to avoid errors in hot-reloading
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize Firebase: {e}")

class ConfigManager:
    @staticmethod
    def read_data(local_path, collection_name, doc_id="default"):
        if db:
            try:
                doc_ref = db.collection(collection_name).document(doc_id)
                doc = doc_ref.get()
                if doc.exists:
                    return doc.to_dict().get("data", {})
                return {}
            except Exception as e:
                print(f"Error reading from Firebase ({collection_name}): {e}")
                return {}
        else:
            if not os.path.exists(local_path):
                return {}
            try:
                with open(local_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading {local_path}: {e}")
                return {}

    @staticmethod
    def write_data(local_path, collection_name, data, doc_id="default"):
        if db:
            try:
                doc_ref = db.collection(collection_name).document(doc_id)
                doc_ref.set({"data": data})
                return True
            except Exception as e:
                print(f"Error writing to Firebase ({collection_name}): {e}")
                return False
        else:
            try:
                with open(local_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
                return True
            except Exception as e:
                print(f"Error writing {local_path}: {e}")
                return False

    @classmethod
    def get_snippets(cls):
        return cls.read_data(SNIPPETS_PATH, "config_snippets")

    @classmethod
    def update_snippets(cls, data):
        return cls.write_data(SNIPPETS_PATH, "config_snippets", data)

    @classmethod
    def get_shortcuts(cls):
        return cls.read_data(FILE_SHORTCUTS_PATH, "config_shortcuts")

    @classmethod
    def update_shortcuts(cls, data):
        return cls.write_data(FILE_SHORTCUTS_PATH, "config_shortcuts", data)

    @classmethod
    def get_commands(cls):
        return cls.read_data(COMMANDS_PATH, "config_commands")

    @classmethod
    def update_commands(cls, data):
        import src.shellsense.core.config as config
        success = cls.write_data(COMMANDS_PATH, "config_commands", data)
        if success:
            config.SAFE_COMMANDS = data
        return success
