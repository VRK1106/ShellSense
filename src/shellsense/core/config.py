import os

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA_DIR = os.path.join(BASE_DIR, "data") # Future-proofing for data move
MODEL_PATH = os.path.join(BASE_DIR, "shellsense_v3.pkl")

# Intent to Command Mapping
# Hardened to use lists for subprocess.Popen(shell=False)
SAFE_COMMANDS = {
    "POWER_OFF": ["shutdown", "/s", "/t", "0"],
    "POWER_OFF_TIMER": ["shutdown", "/s", "/t", "{s}"],
    "RESTART": ["shutdown", "/r", "/t", "0"],
    "ABORT_ACTION": ["shutdown", "/a"],
    "LOCK_SCREEN": ["rundll32.exe", "user32.dll,LockWorkStation"],
    "CHECK_RESOURCES": ["taskmgr", "/7"],
    "SERVICE_MGMT": ["cmd", "/c", "net start & pause"],
    "PROCESS_KILL": ["taskkill", "/F", "/PID", "{pid}"],
    "STORAGE_INFO": ["cmd", "/c", "wmic logicaldisk get size,freespace,caption & pause"],
    "SYSTEM_DETAILS": ["msinfo32"],
    "DRIVER_MGMT": ["devmgmt.msc"],
    "POWER_MGMT": ["cmd", "/c", "powercfg /batteryreport & start battery-report.html"],
    "OPEN_CALCULATOR": ["calc"],
    "OPEN_CMD": ["cmd", "/c", "start", "cmd"],
    "OPEN_TASK_MANAGER": ["taskmgr"],
    "OPEN_NETWORK_SETTINGS": ["control", "ncpa.cpl"],
    "CHECK_IP": ["cmd", "/c", "ipconfig /all & pause"],
    "PING_GOOGLE": ["cmd", "/c", "ping 8.8.8.8 & pause"],
    "DNS_LOOKUP": ["cmd", "/c", "nslookup google.com & pause"],
    "TRACE_ROUTE": ["cmd", "/c", "tracert 8.8.8.8 & pause"],
    "QUIT_PROGRAM": None,
    "NEUTRAL": None
}
