import json
import os
import firebase_admin
from firebase_admin import credentials, firestore

def migrate():
    key_path = "firebase_key.json"
    if not os.path.exists(key_path):
        print(f"Error: {key_path} not found.")
        return

    print("Authenticating with Firebase...")
    cred = credentials.Certificate(key_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    files_to_collections = {
        "snippets.json": "config_snippets",
        "file_shortcuts.json": "config_shortcuts",
        "commands.json": "config_commands"
    }

    for filename, collection_name in files_to_collections.items():
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                doc_ref = db.collection(collection_name).document("default")
                doc_ref.set({"data": data})
                print(f"[SUCCESS] Uploaded {filename} ({len(data)} entries) to Firestore collection '{collection_name}'")
            except Exception as e:
                print(f"[ERROR] Failed to upload {filename}: {e}")
        else:
            print(f"[SKIP] {filename} (file does not exist locally)")

    print("\nMigration complete! Your cloud database is now fully populated.")

if __name__ == "__main__":
    migrate()
