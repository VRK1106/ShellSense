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
    (r"(?:restart|reboot)\s+wsl", r"wsl --shutdown; wsl"),
    (r"(?:shutdown|stop)\s+wsl", r"wsl --shutdown"),
    (r"(?:clean|clear|empty|delete)\s+(?:temp|temporary)\s*(?:files?)?", r"Remove-Item -Path \"$env:TEMP\\*\" -Recurse -Force -ErrorAction SilentlyContinue"),
    (r"(?:empty|clear)\s+recycle\s*bin", r"Clear-RecycleBin -Force"),
    (r"(?:list|show)\s+(?:running\s+)?services?", r"Get-Service | Where-Object {$_.Status -eq 'Running'}"),
    (r"(?:restart|reload)\s+explorer", r"Stop-Process -Name explorer -Force; Start-Process explorer"),
    (r"(?:docker\s+)?restart\s+all\s+containers?", r"docker restart $(docker ps -q)"),
    (r"(?:docker\s+)?stop\s+all\s+containers?", r"docker stop $(docker ps -q)"),
    (r"(?:git\s+)?pull\s+all", r"git pull --all"),
    (r"(?:kill|stop|terminate)\s+(?:process\s+)?(\w+)(?:\.exe)?", r"Stop-Process -Name '\1' -Force"),
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

        # 1. Deterministic Multi-Engine Evaluation (Math, Conversions, Downloads, Timers, Snippets)
        direct_matches = []
        try:
            from shellsense.services.math_parser import evaluate_math
            is_match, match_res = evaluate_math(cleaned)
            if is_match and match_res:
                res_str = str(match_res).strip()
                if not any(k in res_str for k in ("Active Windows Startup", "Available Functions")):
                    if res_str.startswith("Locked Snippet: "):
                        data = res_str[16:]
                        orig_key, enc_val = data.split("|", 1) if "|" in data else (data, "")
                        direct_matches.append({
                            "type": "locked_snippet",
                            "intent": "LOCKED_SNIPPET",
                            "title": f"Unlock {orig_key}",
                            "icon": "🔒",
                            "key_name": orig_key,
                            "enc_val": enc_val,
                            "command": cleaned,
                            "result": res_str,
                            "confidence": 1.0,
                            "label": f"🔒 Protected Snippet: {orig_key} (Master Password Required)"
                        })
                    else:
                        icon = "🧮"
                        intent_type = "direct_eval"
                        title = res_str
                        if any(c in res_str.lower() for c in ("inr", "usd", "eur", "gbp", "km", "miles", "celsius", "fahrenheit", "kg", "lbs", "cm", "meter", "foot", "inch", "yard")):
                            icon = "💱"
                        elif "timer" in cleaned or "remind" in cleaned:
                            icon = "⏱️"
                            intent_type = "direct_action"
                        elif "download" in cleaned or "file" in cleaned or "\\" in res_str or "/" in res_str:
                            icon = "📂"
                            intent_type = "direct_action"
                        elif "copied" in res_str.lower() or "snippet" in res_str.lower():
                            icon = "📋"

                        label = f"{icon} {res_str}"
                        direct_matches.append({
                            "type": intent_type,
                            "intent": "DIRECT_RESULT",
                            "title": title,
                            "icon": icon,
                            "command": cleaned,
                            "result": res_str,
                            "confidence": 1.0,
                            "label": label
                        })
        except Exception as e:
            logger.debug(f"Direct feature eval error: {e}")

        # Ensure brain model thread has finished loading before classifying
        if not self.brain.is_healthy() and hasattr(self.brain, '_load_thread') and self.brain._load_thread.is_alive():
            self.brain._load_thread.join(timeout=2.0)

        if not self.brain.is_healthy():
            # Allow fallback if model is still loading or unavailable
            fallback_res = self._heuristic_intent_search(cleaned, top_k)
            return direct_matches + [r for r in fallback_res if r.get('intent') != 'OPEN_CALCULATOR'] if direct_matches else fallback_res

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

            if direct_matches:
                filtered_ml = [r for r in results if r.get('intent') != 'OPEN_CALCULATOR']
                return direct_matches + filtered_ml[:max(1, top_k - len(direct_matches))]

            return results

        except Exception as e:
            logger.error(f"Error classifying intent for '{query}': {e}")
            fallback_res = self._heuristic_intent_search(cleaned, top_k)
            return direct_matches + fallback_res if direct_matches else fallback_res

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

        # Check intent classification from BrainService
        try:
            if hasattr(self, 'brain') and self.brain and self.brain.is_healthy():
                intent, prob = self.brain.predict(p_lower)
                if intent and intent != "NEUTRAL" and prob >= 0.20:
                    safe_cmd = SAFE_COMMANDS.get(intent)
                    if safe_cmd:
                        return " ".join(safe_cmd)
                    meta = INTENT_METADATA.get(intent)
                    if meta and meta.get("default_cmd"):
                        return meta["default_cmd"]
        except Exception:
            pass

        # If user typed something that already looks like shell syntax
        if any(p_lower.startswith(x) for x in ["get-", "set-", "stop-", "start-", "ping", "dir", "ls", "netstat", "ipconfig", "wsl", "taskkill", "shutdown", "rundll32", "curl", "git", "docker", "ssh"]):
            return prompt

        return f"# Executable PowerShell: {prompt}"
