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
from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit, QVBoxLayout, QSystemTrayIcon, QMenu, QLabel, QFrame, QHBoxLayout, QComboBox, QPushButton
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer

from shellsense.services.brain_service import BrainService
from shellsense.services.math_parser import evaluate_math
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
            self.last_math_result = None
            self.active_timers = []
            
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
    
    def start_background_timer(self, task, duration_ms, time_desc):
        if not hasattr(self, 'active_timers'):
            self.active_timers = []
            
        timer = QTimer(self)
        timer.setSingleShot(True)
        
        timer_info = {
            "task": task,
            "time_desc": time_desc,
            "timer": timer
        }
        self.active_timers.append(timer_info)
        
        def on_timeout():
            import winsound
            # 1. Native Windows Notification
            self.tray_icon.showMessage(
                "⏰ ShellSense Alert",
                f"Time is up: {task}",
                QSystemTrayIcon.MessageIcon.Information,
                10000
            )
            # 2. Audible alerts
            try:
                import threading
                def play_beeps():
                    import winsound
                    import time
                    for _ in range(3):
                        try:
                            winsound.Beep(1000, 600)
                        except Exception:
                            pass
                        time.sleep(1.0)
                threading.Thread(target=play_beeps, daemon=True).start()
            except Exception:
                pass
            
            # 3. Bring ShellSense bar to screen and show visual overlay alert & snooze options
            self.show_snooze_panel(task)
            
            if timer_info in self.active_timers:
                self.active_timers.remove(timer_info)
            timer.deleteLater()
            
        timer.timeout.connect(on_timeout)
        timer.start(duration_ms)

    def submit_interactive_timer(self):
        val_str = self.timer_val_input.text().strip()
        if not val_str:
            return
        try:
            val = float(val_str)
            if val <= 0:
                raise ValueError("Must be positive")
        except ValueError:
            self.timer_val_input.setStyleSheet("QLineEdit { border: 2px solid #ff5252; color: #ff5252; background-color: rgba(20, 20, 20, 230); border-radius: 6px; padding: 6px; }")
            return
            
        self.timer_val_input.setStyleSheet("") # reset
        unit_label = self.timer_unit_combo.currentText().lower()
        if unit_label.startswith("minute"):
            unit = "minute"
        elif unit_label.startswith("second"):
            unit = "second"
        else:
            unit = "hour"
            
        task = self.timer_task_input.text().strip()
        if not task:
            task = "Timer"
            
        from shellsense.services.timer_service import calculate_ms
        duration_ms = calculate_ms(val, unit)
        time_desc = f"{val} {unit}" + ("s" if val != 1 else "")
        
        self.start_background_timer(task, duration_ms, time_desc)
        
        # Reset and hide form
        self.timer_widget.setVisible(False)
        self.search_bar.clear()
        
        # Show success message
        self.result_label.setText(f"Timer set for '{task}' in {time_desc}!")
        self.result_label.setVisible(True)
        self.setFixedSize(600, 125)
        self.center_on_screen()
        QTimer.singleShot(1500, self.hide_and_clear)
    def show_snooze_panel(self, task):
        self.current_alert_task = task
        self.alert_message_label.setText(f"⏰ Alert: Time is up for '{task}'!")
        
        self.result_label.setVisible(False)
        self.timer_widget.setVisible(False)
        self.alert_widget.setVisible(True)
        
        self.setFixedSize(600, 160)
        self.center_on_screen()
        self.show()
        self.raise_()
        self.activateWindow()
        self.snooze_custom_val.clear()
        self.snooze_custom_val.setStyleSheet("")
        QTimer.singleShot(10, self.snooze_5_btn.setFocus)

    def snooze_timer(self, minutes):
        if not hasattr(self, 'current_alert_task') or not self.current_alert_task:
            return
            
        task = self.current_alert_task
        duration_ms = int(minutes * 60 * 1000)
        time_desc = f"{minutes} minute" + ("s" if minutes != 1 else "")
        
        # Start new snoozed background timer
        self.start_background_timer(task, duration_ms, time_desc)
        
        # Hide alert widget
        self.alert_widget.setVisible(False)
        
        # Show success confirm
        self.result_label.setText(f"Snoozed '{task}' for {time_desc}!")
        self.result_label.setVisible(True)
        self.setFixedSize(600, 125)
        self.center_on_screen()
        QTimer.singleShot(1500, self.hide_and_clear)

    def snooze_timer_custom(self):
        val_str = self.snooze_custom_val.text().strip()
        if not val_str:
            return
        try:
            val = float(val_str)
            if val <= 0:
                raise ValueError("Must be positive")
        except ValueError:
            self.snooze_custom_val.setStyleSheet("QLineEdit { border: 2px solid #ff5252; color: #ff5252; background-color: rgba(20, 20, 20, 230); border-radius: 6px; padding: 4px; }")
            return
        self.snooze_timer(val)

    def hide_and_clear(self):
        self.result_label.setVisible(False)
        if hasattr(self, 'timer_widget'):
            self.timer_widget.setVisible(False)
        if hasattr(self, 'alert_widget'):
            self.alert_widget.setVisible(False)
        self.setFixedSize(600, 78)
        self.search_bar.clear()
        self.hide()
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
        self.search_bar.textChanged.connect(self.on_text_changed)
        
        self.result_label = QLabel(self)
        self.result_label.setWordWrap(True)
        self.result_label.setVisible(False)
        self.result_label.setStyleSheet("""
            QLabel {
                background-color: rgba(30, 30, 30, 210);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: #00bcd4;
                font-size: 16px;
                padding: 8px;
                font-family: 'Segoe UI', sans-serif;
            }
        """)
        
        # Build interactive Timer form widget
        self.timer_widget = QFrame(self)
        self.timer_widget.setVisible(False)
        self.timer_widget.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 30, 220);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
                padding: 10px;
            }
            QLabel {
                border: none;
                background: transparent;
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QLineEdit {
                background-color: rgba(20, 20, 20, 230);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                color: white;
                font-size: 14px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
            }
            QComboBox {
                background-color: rgba(20, 20, 20, 230);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                color: white;
                font-size: 14px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
                min-width: 90px;
            }
            QPushButton {
                background-color: #0078d4;
                border: none;
                border-radius: 6px;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 16px;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
        """)
        
        timer_layout = QVBoxLayout(self.timer_widget)
        timer_layout.setContentsMargins(5, 5, 5, 5)
        timer_layout.setSpacing(8)
        
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(8)
        
        title_label = QLabel("⏰ Create Alarm:", self.timer_widget)
        title_label.setStyleSheet("font-weight: bold; color: #00bcd4; font-size: 15px;")
        row1_layout.addWidget(title_label)
        
        row1_layout.addStretch()
        
        self.timer_val_input = QLineEdit(self.timer_widget)
        self.timer_val_input.setPlaceholderText("Time...")
        self.timer_val_input.setFixedWidth(80)
        row1_layout.addWidget(self.timer_val_input)
        
        self.timer_unit_combo = QComboBox(self.timer_widget)
        self.timer_unit_combo.addItems(["Minutes", "Seconds", "Hours"])
        row1_layout.addWidget(self.timer_unit_combo)
        
        timer_layout.addLayout(row1_layout)
        
        self.timer_task_input = QLineEdit(self.timer_widget)
        self.timer_task_input.setPlaceholderText("Reminder message (e.g. check the oven, sleep, eat)")
        timer_layout.addWidget(self.timer_task_input)
        
        row3_layout = QHBoxLayout()
        self.start_timer_btn = QPushButton("Start Timer", self.timer_widget)
        self.start_timer_btn.clicked.connect(self.submit_interactive_timer)
        row3_layout.addStretch()
        row3_layout.addWidget(self.start_timer_btn)
        timer_layout.addLayout(row3_layout)
        
        self.timer_val_input.returnPressed.connect(self.submit_interactive_timer)
        self.timer_task_input.returnPressed.connect(self.submit_interactive_timer)
        
        # Build interactive Alert/Snooze widget
        self.alert_widget = QFrame(self)
        self.alert_widget.setVisible(False)
        self.alert_widget.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 30, 220);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
                padding: 10px;
            }
            QLabel {
                border: none;
                background: transparent;
                color: #ffb74d;
                font-family: 'Segoe UI', sans-serif;
                font-size: 15px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: rgba(20, 20, 20, 230);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                color: white;
                font-size: 13px;
                padding: 4px;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton {
                background-color: rgba(0, 120, 212, 0.85);
                border: none;
                border-radius: 6px;
                color: white;
                font-size: 13px;
                font-weight: bold;
                padding: 6px 10px;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
        """)
        
        alert_layout = QVBoxLayout(self.alert_widget)
        alert_layout.setContentsMargins(5, 5, 5, 5)
        alert_layout.setSpacing(10)
        
        self.alert_message_label = QLabel("⏰ Alert: Time is up!", self.alert_widget)
        self.alert_message_label.setWordWrap(True)
        alert_layout.addWidget(self.alert_message_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        
        self.snooze_5_btn = QPushButton("Snooze 5m", self.alert_widget)
        self.snooze_5_btn.clicked.connect(lambda: self.snooze_timer(5))
        btn_layout.addWidget(self.snooze_5_btn)
        
        self.snooze_10_btn = QPushButton("Snooze 10m", self.alert_widget)
        self.snooze_10_btn.clicked.connect(lambda: self.snooze_timer(10))
        btn_layout.addWidget(self.snooze_10_btn)
        
        self.snooze_20_btn = QPushButton("Snooze 20m", self.alert_widget)
        self.snooze_20_btn.clicked.connect(lambda: self.snooze_timer(20))
        btn_layout.addWidget(self.snooze_20_btn)
        
        btn_layout.addStretch()
        
        self.snooze_custom_val = QLineEdit(self.alert_widget)
        self.snooze_custom_val.setPlaceholderText("mins...")
        self.snooze_custom_val.setFixedWidth(55)
        btn_layout.addWidget(self.snooze_custom_val)
        
        self.snooze_custom_btn = QPushButton("Snooze", self.alert_widget)
        self.snooze_custom_btn.clicked.connect(self.snooze_timer_custom)
        btn_layout.addWidget(self.snooze_custom_btn)
        
        alert_layout.addLayout(btn_layout)
        
        self.snooze_custom_val.returnPressed.connect(self.snooze_timer_custom)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(self.search_bar)
        layout.addWidget(self.result_label)
        layout.addWidget(self.timer_widget)
        layout.addWidget(self.alert_widget)
        self.setLayout(layout)
        
        self.setFixedSize(600, 78)
        self.center_on_screen()

    def center_on_screen(self):
        """Centers the window on the primary screen."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def on_text_changed(self):
        # Reset math results, clear error states, and collapse UI if the search query is modified
        self.last_math_result = None
        if self.result_label.isVisible():
            self.result_label.setVisible(False)
            self.setFixedSize(600, 78)
            self.center_on_screen()
            
        # Collapse timer widget if search bar text is edited to something other than "timer" / "alarm" / "timers" / "alarms"
        if hasattr(self, 'timer_widget') and self.timer_widget.isVisible():
            txt = self.search_bar.text().strip().lower()
            if txt not in ('timer', 'timers', 'alarm', 'alarms'):
                self.timer_widget.setVisible(False)
                self.setFixedSize(600, 78)
                self.center_on_screen()
                
        # Collapse alert widget if user types a new command
        if hasattr(self, 'alert_widget') and self.alert_widget.isVisible():
            self.alert_widget.setVisible(False)
            self.setFixedSize(600, 78)
            self.center_on_screen()

    def process_command(self):
        user_text = self.search_bar.text().strip()
        if not user_text: return
        
        # If user presses Enter twice on the calculated math result
        if getattr(self, 'last_math_result', None) is not None:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.last_math_result)
            
            self.tray_icon.showMessage(
                "ShellSense Math",
                f"Result: {self.last_math_result} (Copied to Clipboard)",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
            
            self.last_math_result = None
            self.result_label.setVisible(False)
            self.setFixedSize(600, 78)
            self.search_bar.clear()
            self.hide()
            return
        
        # Intercept math calculations, conversions, and translations
        is_math, result = evaluate_math(user_text)
        if is_math:
            self.last_math_result = result
            if "Available Functions:" in result:
                self.result_label.setText(result)
                self.result_label.setVisible(True)
                self.setFixedSize(600, 350)
                self.center_on_screen()
                return
                
            if "Timer Formats:" in result:
                self.result_label.setVisible(False)
                self.timer_widget.setVisible(True)
                self.timer_val_input.clear()
                self.timer_task_input.clear()
                self.timer_val_input.setStyleSheet("")
                self.setFixedSize(600, 230)
                self.center_on_screen()
                QTimer.singleShot(10, self.timer_val_input.setFocus)
                return
                
            if result.startswith("Timer Created: "):
                data = result[15:]
                task, duration_ms_str, time_desc = data.split("|", 2)
                duration_ms = int(float(duration_ms_str))
                self.start_background_timer(task, duration_ms, time_desc)
                self.result_label.setText(f"Timer set for '{task}' in {time_desc}!")
                self.result_label.setVisible(True)
                self.setFixedSize(600, 125)
                self.center_on_screen()
                QTimer.singleShot(1500, self.hide_and_clear)
                return

            if result == "Cancel Timers":
                if hasattr(self, 'active_timers') and self.active_timers:
                    count = len(self.active_timers)
                    for t in self.active_timers:
                        t["timer"].stop()
                        t["timer"].deleteLater()
                    self.active_timers.clear()
                    self.result_label.setText(f"Cancelled all active timers ({count} stopped).  [Esc to Close]")
                else:
                    self.result_label.setText("No active timers running.  [Esc to Close]")
                self.result_label.setVisible(True)
                self.setFixedSize(600, 125)
                self.center_on_screen()
                return

            if result.startswith("Cancel Timer Name: "):
                target_name = result[19:].strip().lower()
                if not hasattr(self, 'active_timers') or not self.active_timers:
                    self.result_label.setText("No active timers running.  [Esc to Close]")
                else:
                    import re
                    norm_target = re.sub(r'[^a-z0-9]', '', target_name)
                    matches = []
                    for t in self.active_timers:
                        t_name = t["task"].lower()
                        norm_t_name = re.sub(r'[^a-z0-9]', '', t_name)
                        if target_name in t_name or norm_target in norm_t_name:
                            matches.append(t)
                            
                    if not matches:
                        self.result_label.setText(f"No active timer matches '{target_name}'.  [Esc to Close]")
                    elif len(matches) == 1:
                        matched_timer = matches[0]
                        matched_timer["timer"].stop()
                        matched_timer["timer"].deleteLater()
                        self.active_timers.remove(matched_timer)
                        self.result_label.setText(f"Cancelled timer '{matched_timer['task']}'.  [Esc to Close]")
                    else:
                        names_str = ", ".join(f"'{t['task']}'" for t in matches)
                        self.result_label.setText(f"Multiple matches found ({names_str}). Please be more specific.  [Esc to Close]")
                        
                self.result_label.setVisible(True)
                self.setFixedSize(600, 125)
                self.center_on_screen()
                return

            if result.startswith("Copied: "):
                val = result[8:]
                clipboard = QApplication.clipboard()
                clipboard.setText(val)
                self.result_label.setText(f"Copied '{val}' to clipboard!  [Esc to Close]")
                self.result_label.setVisible(True)
                self.setFixedSize(600, 125)
                self.center_on_screen()
                return

            if result.startswith("Copied File: "):
                data = result[13:]
                filepath, key = data.split("|", 1)
                from shellsense.services.file_shortcuts_parser import copy_file_to_clipboard
                try:
                    copy_file_to_clipboard(filepath)
                    self.result_label.setText(f"Copied file '{key}' to clipboard!  [Esc to Close]")
                except Exception as e:
                    self.result_label.setText(f"<span style='color: #ff5252;'>Error copying file: {e}</span>  [Esc to Close]")
                self.result_label.setVisible(True)
                self.setFixedSize(600, 125)
                self.center_on_screen()
                return

            if result.startswith("Copied Path: "):
                data = result[13:]
                filepath, key = data.split("|", 1)
                clipboard = QApplication.clipboard()
                clipboard.setText(filepath)
                self.result_label.setText(f"Copied path '{filepath}' to clipboard!  [Esc to Close]")
                self.result_label.setVisible(True)
                self.setFixedSize(600, 125)
                self.center_on_screen()
                return

            if result.startswith("Opened File: "):
                data = result[13:]
                filepath, key = data.split("|", 1)
                try:
                    os.startfile(filepath)
                    self.result_label.setText(f"Opened file '{key}' successfully!  [Esc to Close]")
                except Exception as e:
                    self.result_label.setText(f"<span style='color: #ff5252;'>Error opening file: {e}</span>  [Esc to Close]")
                self.result_label.setVisible(True)
                self.setFixedSize(600, 125)
                self.center_on_screen()
                return
                
            if result.startswith("Error:"):
                self.result_label.setText(f"<span style='color: #ff5252;'>{result}</span>  [Esc to Close]")
            else:
                self.result_label.setText(f"Result: {result}  [Enter to Copy & Close | Esc to Close]")
            self.result_label.setVisible(True)
            self.setFixedSize(600, 125)
            self.center_on_screen()
            return
        
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
        success = CommandExecutor.execute(intent, user_text)
        if not success:
            self.result_label.setText("<span style='color: #ff5252;'>Error:</span> Command failed to execute  [Esc to Close]")
            self.result_label.setVisible(True)
            self.setFixedSize(600, 125)
            self.center_on_screen()
            return
        
        self.search_bar.clear()
        self.hide()
    
    def toggle_visibility(self, trigger_source="Hotkey"):
        logger.info(f"{trigger_source} triggered. Toggling visibility.")
        if self.isVisible():
            if hasattr(self, 'timer_widget'):
                self.timer_widget.setVisible(False)
            self.hide()
            logger.info("Window hidden.")
        else:
            self.search_bar.clear()
            self.last_math_result = None
            self.result_label.setVisible(False)
            if hasattr(self, 'timer_widget'):
                self.timer_widget.setVisible(False)
            self.setFixedSize(600, 78)
            self.show()
            self.raise_()
            self.activateWindow()
            # Slightly longer delay to ensure Windows has registered the window show
            QTimer.singleShot(10, self.search_bar.setFocus)
            logger.info("Window shown and focused.")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            logger.info("Escape key pressed. Hiding search bar window.")
            self.last_math_result = None
            self.result_label.setVisible(False)
            if hasattr(self, 'timer_widget'):
                self.timer_widget.setVisible(False)
            self.setFixedSize(600, 78)
            self.search_bar.clear()
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