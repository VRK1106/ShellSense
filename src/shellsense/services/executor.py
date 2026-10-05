import subprocess
import re
import shlex
import logging
from shellsense.core.config import SAFE_COMMANDS

logger = logging.getLogger(__name__)

class CommandExecutor:
    DESTRUCTIVE_INTENTS = {
        "POWER_OFF": "Shut down your computer immediately",
        "RESTART": "Restart your computer immediately",
        "PROCESS_KILL": "Terminate running process",
    }

    @classmethod
    def is_destructive(cls, intent: str) -> bool:
        """Checks if an intent performs a destructive or disruptive system action."""
        return intent in cls.DESTRUCTIVE_INTENTS

    @classmethod
    def get_destructive_description(cls, intent: str, user_text: str = "") -> str:
        """Returns a user-friendly description of what the destructive command will do."""
        if intent == "PROCESS_KILL":
            nums = re.findall(r'\d+', user_text)
            pid = nums[0] if nums else "specified"
            return f"Force kill process PID {pid}"
        return cls.DESTRUCTIVE_INTENTS.get(intent, intent.replace('_', ' ').title())

    @staticmethod
    def execute(intent: str, user_text: str = ""):
        """
        Executes the command associated with an intent safely.
        """
        if intent not in SAFE_COMMANDS or SAFE_COMMANDS[intent] is None:
            logger.warning(f"Intent '{intent}' has no executable command mapping.")
            return False

        # Get a copy of the command list
        cmd_template = SAFE_COMMANDS[intent][:]
        
        try:
            # Handle specialized logic for certain intents
            if intent in ("POWER_OFF_TIMER", "SHUTDOWN_TIMER"):
                nums = re.findall(r'\d+', user_text)
                if nums:
                    val = int(nums[0])
                    lower_text = user_text.lower()
                    # If user specifies hours, multiply by 3600; otherwise assume minutes and multiply by 60
                    if "hour" in lower_text or "hr" in lower_text:
                        seconds = str(val * 3600)
                    else:
                        seconds = str(val * 60)
                    cmd_template = [seconds if x == "{s}" else x for x in cmd_template]
                else:
                    logger.error("Timer intent detected but no duration found in user text.")
                    return False
            
            elif intent == "PROCESS_KILL":
                nums = re.findall(r'\d+', user_text)
                if nums:
                    # Replace placeholder {pid} with actual PID
                    cmd_template = [nums[0] if x == "{pid}" else x for x in cmd_template]
                else:
                    logger.error("Process kill intent detected but no PID found.")
                    return False

            # Execute with shell=False for security (prevent injection)
            logger.info(f"Executing hardened command: {cmd_template}")
            subprocess.Popen(cmd_template, shell=False)
            return True

        except Exception as e:
            logger.exception(f"Failed to execute command for intent '{intent}': {e}")
            return False
