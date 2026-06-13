import sys
import os

# Auto-resolve 'src' path for standalone execution
current_dir = os.path.dirname(os.path.abspath(__file__))
src_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if src_root not in sys.path:
    sys.path.insert(0, src_root)

import signal
import keyboard
from ctypes import windll, wintypes
from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit, QVBoxLayout, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer

from shellsense.services.brain_service import BrainService
from shellsense.services.executor import CommandExecutor
from shellsense.core.logger import logger

# Windows Constants for Session Notification
WM_WTSSESSION_CHANGE = 0x02B1
WTS_SESSION_UNLOCK = 0x08
NOTIFY_FOR_THIS_SESSION = 0

class HotkeySignaler(QObject):
    signal = pyqtSignal()

class ShellSenseUI(QWidget):
    def __init__(self):
        super().__init__()
        logger.info("Initializing ShellSenseUI...")
        try:
            logger.info("Loading BrainService...")
            self.brain = BrainService()
            
            logger.info("Initializing UI...")
            self.initUI()
            
            logger.info("Initializing Tray...")
            self.initTray()
            
            # Register for Windows Session Notifications (Unlock events)
            logger.info("Scheduling Session Notifications...")
            QTimer.singleShot(500, self.register_session_notifications)
            
            self.signaler = HotkeySignaler()
            self.signaler.signal.connect(self.toggle_visibility, Qt.ConnectionType.QueuedConnection)
            
            # Keep a slow watchdog as a safety net (every 30s)
            self.hotkey_handle = None
            self.hotkey_timer = QTimer(self)
            self.hotkey_timer.timeout.connect(self.refresh_hotkey)
            self.hotkey_timer.start(30000) 
            
            logger.info("Refreshing initial hotkey...")
            self.refresh_hotkey()
            logger.info("ShellSenseUI Initialization Complete.")
        except Exception as e:
            logger.critical(f"Error during UI Initialization: {e}", exc_info=True)
            raise
    
    def register_session_notifications(self):
        try:
            hwnd = self.winId()
            # Register for session change notifications
            windll.wtsapi32.WTSRegisterSessionNotification(int(hwnd), NOTIFY_FOR_THIS_SESSION)
            logger.info("Registered for Windows session notifications.")
        except Exception as e:
            logger.error(f"Failed to register session notification: {e}")

    def nativeEvent(self, eventType, message):
        try:
            event_bytes = bytes(eventType)
        except Exception:
            event_bytes = b""
            
        if event_bytes == b"windows_generic_MSG":
            try:
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == WM_WTSSESSION_CHANGE:
                    if msg.wParam == WTS_SESSION_UNLOCK:
                        logger.info("Windows Unlock detected! Immediately refreshing hotkey.")
                        self.refresh_hotkey()
            except Exception as e:
                logger.error(f"Error parsing native MSG: {e}")
                
        is_handled, res = super().nativeEvent(eventType, message)
        return is_handled, res
    
    def refresh_hotkey(self):
        try:
            # Safely remove existing hotkey if it exists
            if self.hotkey_handle is not None:
                try:
                    keyboard.remove_hotkey(self.hotkey_handle)
                except:
                    pass
            
            # Re-register
            self.hotkey_handle = keyboard.add_hotkey('ctrl+shift+space', self.signaler.signal.emit)
            logger.debug("Hotkey hook refreshed.")
        except Exception as e:
            # If the listener itself is broken, we might need to reset more aggressively
            # but for now, we just log and try again next cycle
            logger.error(f"Hotkey refresh failed: {e}")
            self.hotkey_handle = None
    
    def initTray(self):
        self.tray_icon = QSystemTrayIcon(self)
        # Use a standard system icon with a more robust fallback
        icon = QIcon.fromTheme("system-search")
        if icon.isNull():
            # Fallback to a standard platform icon if theme icon is missing
            icon = self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogContentsView)
        
        self.tray_icon.setIcon(icon) 
        
        tray_menu = QMenu()
        show_action = QAction("Show ShellSense (Ctrl+Shift+Space)", self)
        show_action.triggered.connect(self.toggle_visibility)
        
        repair_action = QAction("Repair Hotkey", self)
        repair_action.triggered.connect(self.refresh_hotkey)
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(repair_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.setToolTip("ShellSense is active")
        self.tray_icon.activated.connect(self.on_tray_activated)

    def on_tray_activated(self, reason):
        logger.info(f"Tray icon activated. Reason: {reason}")
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            logger.info("Tray icon clicked/double-clicked. Refreshing hotkey and toggling visibility.")
            self.refresh_hotkey() # Refresh hook immediately on manual interaction
            self.toggle_visibility(trigger_source="Tray")
    
    def initUI(self):
        # Using Tool flag which is safer for background utilities
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
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
        
        self.setFixedSize(600, 80)
        self.center_on_screen()

    def center_on_screen(self):
        """Centers the window on the primary screen."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def process_command(self):
        user_text = self.search_bar.text().strip()
        if not user_text: return
        
        intent, confidence = self.brain.predict(user_text)
        
        print(f"--- Brain Analysis ---")
        if confidence < 0.35:
            print(f"❓ Low confidence ({confidence:.2f}). Trying best guess: {intent}")
        else:
            print(f"✅ High confidence ({confidence:.2f}). Intent: {intent}")

        if intent == "QUIT_PROGRAM":
            print("Shutting down ShellSense Engine...")
            QApplication.quit()
            return

        # Use the hardened executor service
        CommandExecutor.execute(intent, user_text)
        
        self.search_bar.clear()
        self.hide()
    
    def toggle_visibility(self, trigger_source="Hotkey"):
        logger.info(f"{trigger_source} triggered. Toggling visibility.")
        if self.isVisible():
            self.hide()
            logger.info("Window hidden.")
        else:
            self.search_bar.clear()
            self.show()
            self.raise_()
            self.activateWindow()
            # Slightly longer delay to ensure Windows has registered the window show
            QTimer.singleShot(10, self.search_bar.setFocus)
            logger.info("Window shown and focused.")

def main():
    try:
        # Let Python handle Ctrl+C
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        
        app = QApplication(sys.argv)
        logger.info("Application instance created.")
        app.setQuitOnLastWindowClosed(False)
        window = ShellSenseUI()
        
        logger.info("Starting Event Loop...")
        result = app.exec()
        logger.info(f"Event Loop Exited with code: {result}")
        sys.exit(result)
    except Exception as e:
        import traceback
        error_msg = f"Unhandled exception in main: {e}\n{traceback.format_exc()}"
        print(error_msg)
        if 'logger' in globals():
            logger.critical(error_msg)
        else:
            with open("startup_crash.log", "a") as f:
                f.write(error_msg + "\n")

if __name__ == "__main__":
    main()