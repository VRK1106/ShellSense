import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class AICoder:
    GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
    MODEL = "qwen/qwen3.8-27b" # Fast, lightweight model on Groq

    @classmethod
    def execute_prompt(cls, prompt: str) -> dict:
        """
        Executes a prompt to modify the codebase using Groq.
        """
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return {"success": False, "error": "GROQ_API_KEY environment variable not set."}

        from src.shellsense.core.config_manager import ConfigManager
        snippets = json.dumps(ConfigManager.get_snippets(), indent=2)
        shortcuts = json.dumps(ConfigManager.get_shortcuts(), indent=2)
        commands = json.dumps(ConfigManager.get_commands(), indent=2)

        system_prompt = f'''You are an expert Python and Web developer AI managing the ShellSense codebase.
The user will provide a prompt to modify the tool.
You are fully capable of editing the backend and the frontend UI.
Key Frontend files (located in src/shellsense/web/static/):
- index.html
- styles.css
- app.js
Key Backend files:
- snippets.json, file_shortcuts.json, commands.json (in project root)
- src/shellsense/web/server.py

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
            "max_tokens": 800
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
                    
                    if file_path and content:
                        abs_path = os.path.abspath(file_path)
                        with open(abs_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        return {"success": True, "message": f"Successfully updated {file_path}"}
                    else:
                        return {"success": False, "error": "LLM returned invalid JSON structure."}
                except json.JSONDecodeError:
                    return {"success": False, "error": "LLM response was not valid JSON."}
            else:
                return {"success": False, "error": f"Groq API returned status {response.status_code}: {response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
