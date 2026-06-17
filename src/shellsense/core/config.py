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

# Intent to Command Mapping
# Hardened to use lists for subprocess.Popen(shell=False)
SAFE_COMMANDS = {
    "POWER_OFF": ["shutdown", "/s", "/t", "0"],
    "POWER_OFF_TIMER": ["shutdown", "/s", "/t", "{s}"],
    "SHUTDOWN_TIMER": ["shutdown", "/s", "/t", "{s}"],
    "RESTART": ["shutdown", "/r", "/t", "0"],
    "ABORT_ACTION": ["shutdown", "/a"],
    "LOCK_SCREEN": ["rundll32.exe", "user32.dll,LockWorkStation"],
    "CHECK_RESOURCES": ["taskmgr.exe", "/7"],
    "SERVICE_MGMT": ["cmd", "/c", "net start & pause"],
    "PROCESS_KILL": ["taskkill", "/F", "/PID", "{pid}"],
    "STORAGE_INFO": ["cmd", "/c", "wmic logicaldisk get size,freespace,caption & pause"],
    "SYSTEM_DETAILS": ["msinfo32.exe"],
    "SHOW_SYSTEM_INFO": ["msinfo32.exe"],
    "DRIVER_MGMT": ["cmd", "/c", "start", "devmgmt.msc"],
    "POWER_MGMT": ["cmd", "/c", "powercfg /batteryreport & start battery-report.html"],
    "OPEN_CALCULATOR": ["calc.exe"],
    "OPEN_CMD": ["cmd", "/c", "start", "cmd"],
    "OPEN_TASK_MANAGER": ["taskmgr.exe"],
    "SHOW_TASKS": ["taskmgr.exe"],
    "OPEN_NETWORK_SETTINGS": ["explorer.exe", "ms-settings:network-wifi"],
    "OPEN_NET": ["explorer.exe", "ms-settings:network-wifi"],
    "CHECK_IP": ["cmd", "/c", "ipconfig /all & pause"],
    "PING_GOOGLE": ["cmd", "/c", "ping 8.8.8.8 & pause"],
    "DNS_LOOKUP": ["cmd", "/c", "nslookup google.com & pause"],
    "TRACE_ROUTE": ["cmd", "/c", "tracert 8.8.8.8 & pause"],
    "QUIT_PROGRAM": None,
    "NEUTRAL": None
}

# Feedback Configuration (Centralized Google Sheets/Forms or local backup log)
FEEDBACK_URL = "https://docs.google.com/forms/u/0/d/e/1FAIpQLSeOPykvnD1_GHa5zGlvbbOlKBehc7FaOU_8Jm383SBfQwW-VQ/formResponse"
FEEDBACK_ENTRY_CATEGORY = "entry.1060351434"
FEEDBACK_ENTRY_QUERY = "entry.1031596501"
FEEDBACK_ENTRY_OUTPUT = "entry.55134923"
FEEDBACK_ENTRY_RATING = "entry.1053210131"
FEEDBACK_ENTRY_COMMENT = "entry.1635821479"
FEEDBACK_ENTRY_USER_NAME = "entry.2142960445"
FEEDBACK_ENTRY_USER_EMAIL = "entry.1486106542"


