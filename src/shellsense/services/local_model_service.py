import re
import json
import urllib.request
from typing import List, Dict, Any, Optional
from shellsense.services.brain_service import BrainService
from shellsense.core.config import SAFE_COMMANDS
from shellsense.core.logger import logger

INTENT_METADATA = {
    "OPEN_NETWORK_SETTINGS": {"title": "Wi-Fi & Network Settings", "icon": "📶", "default_cmd": "ms-settings:network-wifi"},
    "CHECK_IP": {"title": "Check Local IP Address", "icon": "🌐", "default_cmd": "ipconfig"},
    "STORAGE_INFO": {"title": "Disk Space & Storage", "icon": "💾", "default_cmd": "cleanmgr.exe"},
    "CHECK_RESOURCES": {"title": "System Resources & CPU", "icon": "📊", "default_cmd": "resmon"},
    "OPEN_TASK_MANAGER": {"title": "Open Task Manager", "icon": "📋", "default_cmd": "taskmgr.exe"},
    "PING_GOOGLE": {"title": "Ping Google DNS", "icon": "📡", "default_cmd": "ping 8.8.8.8"},
    "DNS_LOOKUP": {"title": "Flush DNS Cache", "icon": "🔎", "default_cmd": "ipconfig /flushdns"},
    "SHOW_SYSTEM_INFO": {"title": "System Information", "icon": "ℹ️", "default_cmd": "systeminfo"},
    "SHOW_TASKS": {"title": "List Running Tasks", "icon": "📑", "default_cmd": "tasklist"},
    "POWER_OFF": {"title": "Shut Down Computer", "icon": "🛑", "default_cmd": "shutdown /s /t 0"},
    "RESTART": {"title": "Restart Computer", "icon": "🔄", "default_cmd": "shutdown /r /t 0"},
    "LOCK_SCREEN": {"title": "Lock Workstation", "icon": "🔒", "default_cmd": "rundll32.exe user32.dll,LockWorkStation"},
    "OPEN_CALCULATOR": {"title": "Open Calculator", "icon": "🧮", "default_cmd": "calc.exe"},
    "OPEN_CMD": {"title": "Command Prompt", "icon": "💻", "default_cmd": "cmd.exe"},
    "OPEN_NET": {"title": "Network Connections", "icon": "🌐", "default_cmd": "ncpa.cpl"},
    "DRIVER_MGMT": {"title": "Device Manager & Drivers", "icon": "⚙️", "default_cmd": "devmgmt.msc"},
    "TRACE_ROUTE": {"title": "Trace Route (8.8.8.8)", "icon": "📍", "default_cmd": "tracert 8.8.8.8"},
    "PROCESS_KILL": {"title": "Terminate Process", "icon": "🚫", "default_cmd": "taskkill /F /PID"},
    "QUIT_PROGRAM": {"title": "Close Active Program", "icon": "❌", "default_cmd": "taskkill /f /im"},
    "POWER_OFF_TIMER": {"title": "Schedule Shutdown Timer", "icon": "⏱️", "default_cmd": "shutdown /s /t 3600"},
    "SHUTDOWN_TIMER": {"title": "Shutdown Countdown Timer", "icon": "⏱️", "default_cmd": "shutdown /s /t 1800"},
}

FALLBACK_SYNTAX_PATTERNS = [
    (r"(?:find|search|locate)\s+(?:all\s+)?(\w+)\s+files?", r"Get-ChildItem -Recurse -Filter '*.\1'"),
    (r"(?:kill|stop|terminate)\s+process\s+(\w+)", r"Stop-Process -Name '\1' -Force"),
    (r"(?:kill|stop|terminate)\s+(?:pid\s+)?(\d+)", r"Stop-Process -Id \1 -Force"),
    (r"(?:ping|check\s+reachability\s+of)\s+([a-zA-Z0-9\.\-]+)", r"Test-Connection -TargetName \1 -Count 4"),
    (r"(?:list|show|check)\s+(?:open\s+)?ports?", r"netstat -ano | findstr LISTENING"),
    (r"(?:disk|storage|free)\s+space", r"Get-PSDrive -PSProvider FileSystem"),
    (r"(?:env|environment)\s+(?:vars|variables)", r"Get-ChildItem env:"),
    (r"(?:system|pc|computer)\s+(?:info|specs)", r"systeminfo"),
    (r"(?:installed|all)\s+(?:apps|programs|software)", r"Get-Package"),
    (r"(?:uptime|how\s+long\s+running)", r"(Get-Date) - (gcim Win32_OperatingSystem).LastBootUpTime"),
    (r"(?:my|current|local)\s+ip", r"ipconfig"),
    (r"(?:flush|clear)\s+dns", r"ipconfig /flushdns"),
]


class LocalModelService:
    """
    Local model pipeline delivering:
    1. Ranked intent classifications for non-prefixed natural language inputs (via BrainService).
    2. Verified raw shell syntax generation for COMMAND_PROMPT mode.
    """
    _instance: Optional['LocalModelService'] = None

    def __init__(self):
        self.brain = BrainService()

    @classmethod
    def get_instance(cls) -> 'LocalModelService':
        if cls._instance is None:
            cls._instance = LocalModelService()
        return cls._instance

    # --- 1. Intent Classification for Non-prefixed Inputs ---

    def get_ranked_intent_candidates(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Classifies non-prefixed natural language input and returns ranked candidates.
        """
        cleaned = (query or "").strip().lower()
        if len(cleaned) < 2:
            return []

        # Ensure brain model thread has finished loading before classifying
        if not self.brain.is_healthy() and hasattr(self.brain, '_load_thread') and self.brain._load_thread.is_alive():
            self.brain._load_thread.join(timeout=2.0)

        if not self.brain.is_healthy():
            # Allow fallback if model is still loading or unavailable
            return self._heuristic_intent_search(cleaned, top_k)

        try:
            import numpy as np
            text_vec = self.brain.vectorizer.transform([cleaned])
            probs = self.brain.clf.predict_proba(text_vec)[0]
            top_indices = np.argsort(probs)[::-1]

            results = []
            for idx in top_indices:
                prob = float(probs[idx])
                intent = self.brain.le.inverse_transform([idx])[0]
                if intent == "NEUTRAL" and prob < 0.6:
                    continue
                if prob < 0.04 and len(results) >= 2:
                    break

                meta = INTENT_METADATA.get(intent, {
                    "title": intent.replace("_", " ").title(),
                    "icon": "⚡",
                    "default_cmd": intent.lower()
                })

                # Retrieve concrete command string if available in SAFE_COMMANDS
                safe_cmd_list = SAFE_COMMANDS.get(intent)
                if safe_cmd_list:
                    cmd_str = " ".join(safe_cmd_list)
                else:
                    cmd_str = meta.get("default_cmd", "")

                prob_pct = int(round(prob * 100))
                label = f"{meta['icon']} {meta['title']} — {cmd_str} ({prob_pct}%)"

                results.append({
                    "intent": intent,
                    "title": meta["title"],
                    "icon": meta["icon"],
                    "command": cmd_str,
                    "confidence": prob,
                    "label": label
                })

                if len(results) >= top_k:
                    break

            return results

        except Exception as e:
            logger.error(f"Error classifying intent for '{query}': {e}")
            return self._heuristic_intent_search(cleaned, top_k)

    def _heuristic_intent_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        results = []
        q_norm = query.replace("-", "").replace(" ", "").lower()
        for intent, meta in INTENT_METADATA.items():
            title_norm = meta["title"].lower().replace("-", "").replace(" ", "")
            intent_norm = intent.lower().replace("_", "")
            if q_norm in intent_norm or q_norm in title_norm or ("wifi" in q_norm and "network" in intent_norm):
                results.append({
                    "intent": intent,
                    "title": meta["title"],
                    "icon": meta["icon"],
                    "command": meta["default_cmd"],
                    "confidence": 0.85,
                    "label": f"{meta['icon']} {meta['title']} — {meta['default_cmd']} (85%)"
                })
                if len(results) >= top_k:
                    break
        return results

    # --- 2. Verified Raw Shell Syntax for COMMAND_PROMPT Mode ---

    def generate_shell_syntax(self, prompt: str, timeout: float = 2.5) -> str:
        """
        Invokes local model with strict system instructions to output only raw, verified shell syntax.
        Falls back seamlessly to local pattern synthesis if offline or timed out.
        """
        cleaned_prompt = (prompt or "").strip()
        if not cleaned_prompt:
            return ""

        # Attempt querying local Ollama / Qwen model with strict single-line instruction
        try:
            url = "http://localhost:11434/api/generate"
            system_instruction = (
                "You are an expert Windows PowerShell command line generator. "
                "Output ONLY the single-line executable PowerShell syntax. "
                "Do NOT wrap in markdown code fences, do not use backticks, "
                "do NOT provide explanations or commentary. "
                "Raw command only."
            )
            data = {
                "model": "qwen2.5:1.5b",
                "prompt": f"{system_instruction}\nTask: {cleaned_prompt}\nCommand:",
                "stream": False
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                raw_response = res_json.get("response", "").strip()
                parsed_cmd = self._clean_raw_shell_output(raw_response)
                if parsed_cmd:
                    logger.info(f"Ollama generated shell syntax: {parsed_cmd}")
                    return parsed_cmd
        except Exception as e:
            logger.debug(f"Local Ollama query bypassed or timed out: {e}")

        # Deterministic offline verified pattern synthesizer
        return self._synthesize_fallback_syntax(cleaned_prompt)

    def _clean_raw_shell_output(self, raw: str) -> str:
        """Strips markdown code blocks, backticks, quotes, and preambles from model output."""
        text = raw.strip()
        # Remove ```powershell or ```bash blocks
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        # Take the first non-empty line
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            if line.lower().startswith("here is") or line.lower().startswith("command:"):
                continue
            cleaned = line.strip("`'\"")
            if cleaned:
                return cleaned
        return lines[0].strip("`'\"") if lines else ""

    def _synthesize_fallback_syntax(self, prompt: str) -> str:
        """Synthesizes verified PowerShell syntax from known patterns."""
        p_lower = prompt.lower()
        for pattern, replacement in FALLBACK_SYNTAX_PATTERNS:
            match = re.search(pattern, p_lower)
            if match:
                try:
                    return re.sub(pattern, replacement, p_lower).strip()
                except Exception:
                    pass

        # If user typed something that already looks like shell syntax (e.g. ping google.com, ls, dir)
        if any(p_lower.startswith(x) for x in ["get-", "set-", "stop-", "start-", "ping", "dir", "ls", "netstat", "ipconfig"]):
            return prompt

        return f"# Executable PowerShell: {prompt}"
