import sys
import keyboard
import subprocess
import re
import joblib
from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QObject

class HotkeySignaler(QObject):
    signal = pyqtSignal()

vectorizer, le, clf = joblib.load('shellsense_v2.pkl')

SAFE_COMMANDS = {
    "POWER_OFF": ["shutdown", "/s", "/t", "0"],
    "POWER_OFF_TIMER": ["shutdown", "/s", "/t", "{s}"],
    "RESTART": ["shutdown", "/r", "/t", "0"],
    "ABORT_ACTION": ["shutdown", "/a"],
    "LOCK_SCREEN": ["rundll32.exe", "user32.dll,LockWorkStation"],
    "CHECK_RESOURCES": ["taskmgr", "/7"],
    "SERVICE_MGMT": ["cmd", "/c", "net start & pause"],
    "PROCESS_KILL": ["cmd", "/c", "tasklist & pause"],
    "STORAGE_INFO": ["cmd", "/c", "wmic logicaldisk get size,freespace,caption & pause"],
    "SYSTEM_DETAILS": ["cmd", "/c", "msinfo32"],
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
    "NEUTRAL": None
}

class ShellSenseUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.signaler = HotkeySignaler()
        self.signaler.signal.connect(self.toggle_visibility)
    
    def initUI(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search ShellSense Features...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background-color: rgba(20, 20, 20, 230);
                border: 2px solid #0078d4;
                border-radius: 12px;
                color: white;
                font-size: 18px;
                padding: 12px;
                font-family: 'Segoe UI', sans-serif;
            }
        """)
        self.search_bar.returnPressed.connect(self.process_command)
        
        layout = QVBoxLayout()
        layout.addWidget(self.search_bar)
        self.setLayout(layout)
        self.setGeometry(660, 450, 600, 80)

    def process_command(self):
        user_text = self.search_bar.text().strip()
        if not user_text: return
        
        text_vec = vectorizer.transform([user_text.lower()])
        probs = clf.predict_proba(text_vec)[0]
        max_prob = max(probs)
        
        prediction_id = clf.predict(text_vec)[0]
        intent = le.inverse_transform([prediction_id])[0]

        # LOGIC: If confidence is above 0.35, we trust it. 
        # For a student project on an i7, this is a safe 'usability' threshold.
        if max_prob < 0.35:
            print(f"⚠️ Confidence too low ({max_prob:.2f}). Try being more specific.")
            self.search_bar.clear()
            self.hide()
            return
            
        print(f"✅ Intent: {intent} ({max_prob:.2f})")
        self.execute_logic(intent, user_text)
        self.search_bar.clear()
        self.hide()

    def execute_logic(self, intent, user_text):
        if intent == "QUIT_PROGRAM":
            print("Shutting down ShellSense Engine...")
            QApplication.quit()
            return

        if intent not in SAFE_COMMANDS or SAFE_COMMANDS[intent] is None:
            return

        cmd = SAFE_COMMANDS[intent].copy()

        if intent == "POWER_OFF_TIMER":
            nums = re.findall(r'\d+', user_text)
            if nums:
                cmd[3] = str(int(nums[0]) * 60)
            else:
                return
        
        elif intent == "PROCESS_KILL":
            nums = re.findall(r'\d+', user_text)
            if nums:
                cmd = ["taskkill", "/F", "/PID", nums[0]]

        try:
            subprocess.Popen(cmd, shell=True)
        except Exception as e:
            print(f"Error: {e}")
    
    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()
            self.search_bar.setFocus()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ShellSenseUI()
    keyboard.add_hotkey('ctrl+shift+space', window.signaler.signal.emit)
    print("--- ShellSense Engine Active ---")
    print("Hooking global keyboard listeners...")
    print("Press Ctrl+Shift+Space to summon.")
    sys.exit(app.exec())