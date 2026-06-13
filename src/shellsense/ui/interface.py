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
            
            # Watchdog to make sure hotkey stays active (runs without forcing if already registered)
            self.hotkey_handle = None
            self.hotkey_timer = QTimer(self)
            self.hotkey_timer.timeout.connect(self.refresh_hotkey)
            self.hotkey_timer.start(30000) 
            
            logger.info("Refreshing initial hotkey...")
            self.refresh_hotkey(force=True)
            logger.info("ShellSenseUI Initialization Complete.")
        except Exception as e:
            logger.critical(f"Error during UI Initialization: {e}", exc_info=True)
            raise
    
    def register_session_notifications(self):
        try:
            hwnd = self.winId()
            if not hwnd:
                logger.error("No valid HWND found for session notifications.")
                return
            
            # Explicitly define ctypes signature to prevent 64-bit truncation crashes
            wtsapi32 = windll.wtsapi32
            wtsapi32.WTSRegisterSessionNotification.argtypes = [wintypes.HWND, wintypes.DWORD]
            wtsapi32.WTSRegisterSessionNotification.restype = wintypes.BOOL
            
            success = wtsapi32.WTSRegisterSessionNotification(int(hwnd), NOTIFY_FOR_THIS_SESSION)
            if success:
                logger.info("Registered for Windows session notifications.")
            else:
                logger.warning("WTSRegisterSessionNotification returned False.")
        except Exception as e:
            logger.error(f"Failed to register session notification: {e}")

    # def nativeEvent(self, eventType, message):
    #     try:
    #         event_bytes = bytes(eventType)
    #     except Exception:
    #         event_bytes = b""
    #         
    #     if event_bytes == b"windows_generic_MSG" and message:
    #         try:
    #             addr = int(message)
    #             if addr != 0:
    #                 msg = wintypes.MSG.from_address(addr)
    #                 if msg.message == WM_WTSSESSION_CHANGE:
    #                     if msg.wParam == WTS_SESSION_UNLOCK:
    #                         logger.info("Windows Unlock detected! Refreshing hotkey.")
    #                         self.refresh_hotkey(force=True)
    #         except Exception as e:
    #             logger.error(f"Error parsing native MSG: {e}")
    #             
    #     try:
    #         is_handled, res = super().nativeEvent(eventType, message)
    #         return is_handled, res
    #     except Exception as e:
    #         logger.error(f"Exception in super().nativeEvent: {e}")
    #         return False, 0
    
    def refresh_hotkey(self, force=False):
        try:
            # Avoid re-registering if already registered and not forced.
            # Unconditional recreation of keyboard hooks in a loop causes stability/crash issues in the keyboard library.
            if self.hotkey_handle is not None and not force:
                logger.debug("Hotkey already registered, skipping refresh.")
                return

            # Safely remove existing hotkey if it exists or if forcing a refresh
            if self.hotkey_handle is not None:
                try:
                    keyboard.remove_hotkey(self.hotkey_handle)
                except:
                    pass
                self.hotkey_handle = None
            
            # Re-register
            self.hotkey_handle = keyboard.add_hotkey('ctrl+shift+space', self.signaler.signal.emit)
            logger.info("Hotkey hook registered successfully.")
        except Exception as e:
            logger.error(f"Hotkey registration failed: {e}")
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
        repair_action.triggered.connect(lambda: self.refresh_hotkey(force=True))
        
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
            self.refresh_hotkey(force=True) # Refresh hook immediately on manual interaction
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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            logger.info("Escape key pressed. Hiding search bar window.")
            self.hide()
        else:
            super().keyPressEvent(event)

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