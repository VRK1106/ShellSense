import requests
import json
import os
import difflib
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class AICoder:
    GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
    MODEL = "qwen/qwen3-32b"  # Upgraded valid Groq model ID

    # Strict allow-list to prevent unauthorized code modifications
    ALLOWED_FILES = {
        "snippets.json",
        "file_shortcuts.json",
        "commands.json",
        "src/shellsense/web/static/index.html",
        "src/shellsense/web/static/styles.css",
        "src/shellsense/web/static/app.js",
    }

    LAST_MODIFIED_FILE = None

    @classmethod
    def get_project_root(cls) -> str:
        # Resolves project root (4 levels up from this file)
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

    @classmethod
    def execute_prompt(cls, prompt: str) -> dict:
        """
        Executes a prompt to modify the codebase safely using Groq with allow-listing and backups.
        """
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return {"success": False, "error": "GROQ_API_KEY environment variable not set."}

        from src.shellsense.core.config_manager import ConfigManager
        snippets = json.dumps(ConfigManager.get_snippets(), indent=2)
        shortcuts = json.dumps(ConfigManager.get_shortcuts(), indent=2)
        commands = json.dumps(ConfigManager.get_commands(), indent=2)

        system_prompt = f'''You are an expert Python and Web developer AI managing the ShellSense codebase.
The user will provide a prompt to modify the configuration or web interface.
Allowed files to modify:
- snippets.json, file_shortcuts.json, commands.json (in project root)
- src/shellsense/web/static/index.html
- src/shellsense/web/static/styles.css
- src/shellsense/web/static/app.js

Current content of snippets.json:
{snippets}

Current content of file_shortcuts.json:
{shortcuts}

Current content of commands.json:
{commands}

You must output ONLY valid JSON in the following format, with NO markdown formatting, NO backticks, NO explanations.
{{
    "file_path": "path/to/file.ext",
    "content": "the entire new content for the file"
}}
'''
        payload = {
            "model": cls.MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": 1200
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(cls.GROQ_URL, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                data = response.json()
                response_text = data["choices"][0]["message"]["content"]
                
                try:
                    changes = json.loads(response_text)
                    file_path = changes.get("file_path")
                    content = changes.get("content")
                    
                    if not file_path or content is None:
                        return {"success": False, "error": "LLM returned invalid JSON structure."}

                    project_root = cls.get_project_root()
                    abs_path = os.path.abspath(os.path.join(project_root, file_path))
                    rel_path = os.path.relpath(abs_path, project_root).replace('\\', '/')

                    # Security Enforcement: Check against allow-list
                    if rel_path not in cls.ALLOWED_FILES:
                        return {
                            "success": False,
                            "error": f"Security restriction: AI agent is blocked from modifying '{rel_path}'. Only allowed files can be modified."
                        }

                    old_content = ""
                    if os.path.exists(abs_path):
                        with open(abs_path, "r", encoding="utf-8") as f_old:
                            old_content = f_old.read()

                    # Compute unified diff preview
                    diff = "".join(difflib.unified_diff(
                        old_content.splitlines(keepends=True),
                        content.splitlines(keepends=True),
                        fromfile=f"a/{rel_path}",
                        tofile=f"b/{rel_path}"
                    ))

                    # Create backup for rollback
                    bak_path = abs_path + ".bak"
                    with open(bak_path, "w", encoding="utf-8") as f_bak:
                        f_bak.write(old_content)

                    # Write new content
                    with open(abs_path, "w", encoding="utf-8") as f:
                        f.write(content)

                    cls.LAST_MODIFIED_FILE = rel_path
                    return {
                        "success": True,
                        "message": f"Successfully updated {rel_path}",
                        "file_path": rel_path,
                        "diff": diff,
                        "backup_created": True
                    }

                except json.JSONDecodeError:
                    return {"success": False, "error": "LLM response was not valid JSON."}
            else:
                return {"success": False, "error": f"Groq API returned status {response.status_code}: {response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def rollback_last_change(cls) -> dict:
        """
        Reverts the last modified file from its .bak backup.
        """
        if not cls.LAST_MODIFIED_FILE:
            return {"success": False, "error": "No recent AI modification found to rollback."}

        project_root = cls.get_project_root()
        abs_path = os.path.abspath(os.path.join(project_root, cls.LAST_MODIFIED_FILE))
        bak_path = abs_path + ".bak"

        if not os.path.exists(bak_path):
            return {"success": False, "error": f"No backup file found at {bak_path}"}

        try:
            with open(bak_path, "r", encoding="utf-8") as f_bak:
                original_content = f_bak.read()

            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(original_content)

            os.remove(bak_path)
            restored_file = cls.LAST_MODIFIED_FILE
            cls.LAST_MODIFIED_FILE = None
            return {"success": True, "message": f"Successfully rolled back changes to {restored_file}"}
        except Exception as e:
            return {"success": False, "error": f"Rollback failed: {str(e)}"}
