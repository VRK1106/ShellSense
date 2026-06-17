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
from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit, QVBoxLayout, QSystemTrayIcon, QMenu, QLabel, QFrame, QHBoxLayout, QComboBox, QPushButton, QScrollArea, QGraphicsOpacityEffect
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QPropertyAnimation

from shellsense.services.brain_service import BrainService
from shellsense.services.math_parser import evaluate_math
from shellsense.services.executor import CommandExecutor
from shellsense.core.logger import logger

# Windows Constants for Session Notification
WM_WTSSESSION_CHANGE = 0x02B1
WTS_SESSION_UNLOCK = 0x08
NOTIFY_FOR_THIS_SESSION = 0

CONVERSION_CATEGORIES_UNITS = {
    "length": ["m", "km", "cm", "mm", "mile", "yard", "foot", "inch"],
    "area": ["sq_m", "sq_km", "sq_ft", "sq_yard", "sq_mile", "acre", "hectare"],
    "volume": ["l", "ml", "gal", "qt", "pt", "cup", "fl_oz"],
    "weight": ["g", "kg", "lb", "oz", "ton"],
    "mass": ["g", "kg", "lb", "oz", "ton"],
    "mass/weight": ["g", "kg", "lb", "oz", "ton"],
    "speed": ["m/s", "km/h", "mph", "knot"],
    "pressure": ["pa", "kpa", "bar", "psi", "atm"],
    "power": ["w", "kw", "hp"],
    "temperature": ["celsius", "fahrenheit", "kelvin"],
    "temp": ["celsius", "fahrenheit", "kelvin"],
    "currency": ["USD", "EUR", "GBP", "INR", "JPY", "CAD", "AUD", "CNY", "SGD", "CHF", "AED", "SAR"]
}

class HotkeySignaler(QObject):
    signal = pyqtSignal()

class ScrollableLabel(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.verticalScrollBar().setStyleSheet("""
            QScrollBar:vertical {
                border: none;
                background: rgba(20, 20, 20, 150);
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 60);
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 90);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                border: none;
                background: none;
            }
        """)
        
        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.setWidget(self.label)
        
    def setText(self, text):
        self.label.setText(text)
        
    def text(self):
        return self.label.text() if hasattr(self, 'label') else ""
        
    def setStyleSheet(self, style):
        if hasattr(self, 'label'):
            self.label.setStyleSheet(style)
        else:
            super().setStyleSheet(style)
        
    def setWordWrap(self, wrap):
        if hasattr(self, 'label'):
            self.label.setWordWrap(wrap)

class ShellSenseUI(QWidget):
    def setFixedSize(self, *args):
        super().setFixedSize(*args)
        if hasattr(self, 'divider') and hasattr(self, 'result_label'):
            has_results = (self.result_label.isVisible() or 
                           self.timer_widget.isVisible() or 
                           self.alert_widget.isVisible() or
                           (hasattr(self, 'conversion_widget') and self.conversion_widget.isVisible()))
            self.divider.setVisible(has_results)
            if hasattr(self, 'result_actions_widget'):
                self.result_actions_widget.setVisible(self.result_label.isVisible())

    def showEvent(self, event):
        if hasattr(self, 'fade_animation'):
            self.fade_animation.stop()
            self.fade_animation.setStartValue(0.0)
            self.fade_animation.setEndValue(1.0)
            self.fade_animation.start()
        super().showEvent(event)
        if hasattr(self, 'search_bar'):
            self.search_bar.setFocus()
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
            
            # Load any persisted timers from previous session
            logger.info("Loading persisted timers...")
            self.load_persisted_timers()
            
            logger.info("ShellSenseUI Initialization Complete.")
        except Exception as e:
            logger.critical(f"Error during UI Initialization: {e}", exc_info=True)
            raise
    
    def start_background_timer(self, task, duration_ms, time_desc, save=True):
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
        
        if save:
            self.save_active_timers()
        
        def on_timeout():
            import winsound
            # 1. Native Windows Notification
            self.tray_icon.showMessage(
                "ShellSense Alert",
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
            self.save_active_timers()
            
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
            self.timer_val_input.setStyleSheet("QLineEdit { border: 1px solid #ff5252; color: #ff5252; background-color: rgba(255, 255, 255, 15); border-radius: 6px; padding: 6px; }")
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
        self.show_result_message(f"Timer set for '{task}' in {time_desc}!", show_actions=False, auto_hide=True)

    def show_conversion_panel(self, category):
        self.current_conv_category = category
        
        # Format display title
        display_name = category.title()
        if category == "temp":
            display_name = "Temperature"
        elif category == "mass/weight":
            display_name = "Mass/Weight"
            
        self.conv_title_label.setText(f"{display_name} Conversion:")
        
        units = CONVERSION_CATEGORIES_UNITS.get(category.lower(), [])
        
        self.conv_from_combo.clear()
        self.conv_to_combo.clear()
        self.conv_from_combo.addItems(units)
        self.conv_to_combo.addItems(units)
        
        # Select defaults (e.g. from index 0, to index 1 if available)
        if len(units) > 1:
            self.conv_to_combo.setCurrentIndex(1)
            
        self.result_label.setVisible(False)
        self.timer_widget.setVisible(False)
        if hasattr(self, 'alert_widget'):
            self.alert_widget.setVisible(False)
            
        self.conversion_widget.setVisible(True)
        self.conv_val_input.clear()
        self.conv_val_input.setStyleSheet("")
        
        # Expand window height to support form
        self.setFixedSize(600, 135)
        self.center_on_screen()
        QTimer.singleShot(10, self.conv_val_input.setFocus)

    def submit_interactive_conversion(self):
        val_str = self.conv_val_input.text().strip()
        if not val_str:
            return
            
        try:
            val = float(val_str)
        except ValueError:
            self.conv_val_input.setStyleSheet("QLineEdit { border: 1px solid #ff5252; color: #ff5252; background-color: rgba(255, 255, 255, 15); border-radius: 6px; padding: 6px; }")
            return
            
        self.conv_val_input.setStyleSheet("") # reset
        from_unit = self.conv_from_combo.currentText()
        to_unit = self.conv_to_combo.currentText()
        
        # Construct conversion query
        query = f"{val} {from_unit} to {to_unit}"
        
        # Evaluate using conversion parser
        from shellsense.services.conversion_parser import evaluate_conversion
        success, result = evaluate_conversion(query)
        
        if success:
            res_str = f"Result: {result}"
        else:
            res_str = f"<span style='color: #ff5252;'>Error:</span> Conversion failed"
            
        # Hide conversion widget and show result label
        self.conversion_widget.setVisible(False)
        self.search_bar.clear()
        self.show_result_message(res_str, show_actions=True, auto_hide=False)
    def show_snooze_panel(self, task):
        self.current_alert_task = task
        self.alert_message_label.setText(f"Alert: Time is up for '{task}'!")
        
        self.result_label.setVisible(False)
        self.timer_widget.setVisible(False)
        self.alert_widget.setVisible(True)
        
        self.setFixedSize(600, 175)
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
        self.show_result_message(f"Snoozed '{task}' for {time_desc}!", show_actions=False, auto_hide=True)

    def snooze_timer_custom(self):
        val_str = self.snooze_custom_val.text().strip()
        if not val_str:
            return
        try:
            val = float(val_str)
            if val <= 0:
                raise ValueError("Must be positive")
        except ValueError:
            self.snooze_custom_val.setStyleSheet("QLineEdit { border: 1px solid #ff5252; color: #ff5252; background-color: rgba(255, 255, 255, 15); border-radius: 6px; padding: 4px; }")
            return
        self.snooze_timer(val)

    def show_result_message(self, text, show_actions=True, auto_hide=False):
        self.result_label.setText(text)
        self.result_label.setVisible(True)
        if hasattr(self, 'result_actions_widget'):
            self.result_actions_widget.setVisible(show_actions)
        if show_actions:
            self.setFixedSize(600, 175)
        else:
            self.setFixedSize(600, 135)
        self.center_on_screen()
        if hasattr(self, 'search_bar'):
            self.search_bar.setFocus()
        if auto_hide:
            QTimer.singleShot(1500, self.hide_and_clear)

    def copy_result_and_close(self):
        text = self.result_label.text().strip()
        if text.startswith("Result: "):
            text = text[8:]
        import re
        clean_text = re.sub(r'<[^>]*>', '', text)
        clipboard = QApplication.clipboard()
        clipboard.setText(clean_text)
        self.tray_icon.showMessage(
            "ShellSense",
            "Result copied to clipboard!",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
        self.hide_and_clear()

    def hide_and_clear(self):
        self.result_label.setVisible(False)
        if hasattr(self, 'result_actions_widget'):
            self.result_actions_widget.setVisible(False)
        if hasattr(self, 'timer_widget'):
            self.timer_widget.setVisible(False)
        if hasattr(self, 'alert_widget'):
            self.alert_widget.setVisible(False)
        if hasattr(self, 'conversion_widget'):
            self.conversion_widget.setVisible(False)
        self.setFixedSize(600, 78)
        self.search_bar.clear()
        self.hide()

    def load_persisted_timers(self):
        import json
        import time
        
        from shellsense.core.config import TIMERS_PATH
        timers_file = TIMERS_PATH
        
        if not os.path.exists(timers_file):
            return
            
        try:
            with open(timers_file, "r") as f:
                saved = json.load(f)
        except Exception as e:
            logger.error(f"Error loading persisted timers: {e}")
            return
            
        now = time.time()
        updated_list = []
        
        for item in saved:
            task = item.get("task")
            end_time = item.get("end_time")
            time_desc = item.get("time_desc", "")
            
            if not task or not end_time:
                continue
                
            remaining_ms = int((end_time - now) * 1000)
            if remaining_ms <= 0:
                # Use a default arg in lambda to capture the value correctly in the loop
                QTimer.singleShot(1000, lambda t=task: self.trigger_missed_timer(t))
            else:
                self.start_background_timer(task, remaining_ms, time_desc, save=False)
                updated_list.append(item)
                
        try:
            with open(timers_file, "w") as f:
                json.dump(updated_list, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving updated persisted timers: {e}")

    def save_active_timers(self):
        import json
        import time
        
        from shellsense.core.config import TIMERS_PATH
        timers_file = TIMERS_PATH
        
        saved_list = []
        for t in self.active_timers:
            remaining_ms = t["timer"].remainingTime()
            if remaining_ms > 0:
                end_time = time.time() + (remaining_ms / 1000.0)
                saved_list.append({
                    "task": t["task"],
                    "end_time": end_time,
                    "time_desc": t["time_desc"]
                })
                
        try:
            with open(timers_file, "w") as f:
                json.dump(saved_list, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving persisted timers: {e}")

    def trigger_missed_timer(self, task):
        import winsound
        self.tray_icon.showMessage(
            "ShellSense Missed Alert",
            f"Missed alarm: {task}",
            QSystemTrayIcon.MessageIcon.Warning,
            10000
        )
        try:
            import threading
            def play_beeps():
                import winsound
                import time
                for _ in range(3):
                    try:
                        winsound.Beep(800, 600)
                    except Exception:
                        pass
                    time.sleep(1.0)
            threading.Thread(target=play_beeps, daemon=True).start()
        except Exception:
            pass
            
        self.show_snooze_panel(task)
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
        tray_menu.setStyleSheet("""
            QMenu {
                background-color: rgb(20, 20, 25);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                background-color: transparent;
                padding: 6px 20px;
                color: rgba(255, 255, 255, 200);
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(255, 255, 255, 20);
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background-color: rgba(255, 255, 255, 20);
                margin: 4px 0px;
            }
        """)
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
        
        # 1. Main layout of QWidget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 2. Central container holding frosted glass style
        self.container = QFrame(self)
        self.container.setObjectName("CentralContainer")
        self.container.setStyleSheet("""
            QFrame#CentralContainer {
                background-color: rgba(20, 20, 25, 220);
                border: 1px solid rgba(255, 255, 255, 35);
                border-radius: 12px;
            }
        """)
        main_layout.addWidget(self.container)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.setSpacing(8)
        
        # 3. Search Bar Widget
        self.search_bar = QLineEdit(self.container)
        self.search_bar.setPlaceholderText("Search ShellSense Features...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #ffffff;
                font-size: 22px;
                font-family: 'Segoe UI', 'Inter', sans-serif;
                padding: 14px 16px;
                font-weight: 300;
            }
        """)
        self.search_bar.returnPressed.connect(self.process_command)
        self.search_bar.textChanged.connect(self.on_text_changed)
        container_layout.addWidget(self.search_bar)
        
        # 4. Divider Line
        self.divider = QFrame(self.container)
        self.divider.setFrameShape(QFrame.Shape.HLine)
        self.divider.setStyleSheet("background-color: rgba(255, 255, 255, 25); max-height: 1px; border: none; margin: 0px 10px;")
        self.divider.setVisible(False)
        container_layout.addWidget(self.divider)
        
        # 5. Results Label Widget
        self.result_label = ScrollableLabel(self.container)
        self.result_label.setWordWrap(True)
        self.result_label.setVisible(False)
        self.result_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
                color: #e0e0e0;
                font-size: 14px;
                padding: 6px 16px;
                font-family: 'Segoe UI', 'Inter', sans-serif;
            }
        """)
        container_layout.addWidget(self.result_label)
        
        # 5b. Result Actions Widget
        self.result_actions_widget = QFrame(self.container)
        self.result_actions_widget.setObjectName("ResultActionsWidget")
        self.result_actions_widget.setVisible(False)
        self.result_actions_widget.setStyleSheet("""
            QFrame#ResultActionsWidget {
                background: transparent;
                border: none;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 20);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                color: white;
                font-size: 13px;
                font-weight: 500;
                padding: 6px 12px;
                font-family: 'Segoe UI', sans-serif;
                min-width: 90px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 35);
            }
        """)
        
        result_actions_layout = QHBoxLayout(self.result_actions_widget)
        result_actions_layout.setContentsMargins(10, 0, 10, 5)
        result_actions_layout.setSpacing(8)
        
        result_actions_layout.addStretch()
        
        self.result_copy_btn = QPushButton("Copy && Close", self.result_actions_widget)
        self.result_copy_btn.clicked.connect(self.copy_result_and_close)
        result_actions_layout.addWidget(self.result_copy_btn)
        
        self.result_close_btn = QPushButton("Close", self.result_actions_widget)
        self.result_close_btn.clicked.connect(self.hide_and_clear)
        result_actions_layout.addWidget(self.result_close_btn)
        
        container_layout.addWidget(self.result_actions_widget)
        
        # Build interactive Timer form widget
        self.timer_widget = QFrame(self.container)
        self.timer_widget.setObjectName("TimerWidget")
        self.timer_widget.setVisible(False)
        self.timer_widget.setStyleSheet("""
            QFrame#TimerWidget {
                background: transparent;
                border: none;
            }
            QLabel {
                border: none;
                background: transparent;
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QLineEdit {
                background-color: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                color: white;
                font-size: 14px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
            }
            QComboBox {
                background-color: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                color: white;
                font-size: 14px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
                min-width: 90px;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 20);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                color: white;
                font-size: 13px;
                font-weight: 500;
                padding: 6px 12px;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 35);
            }
        """)
        
        timer_layout = QVBoxLayout(self.timer_widget)
        timer_layout.setContentsMargins(10, 5, 10, 5)
        timer_layout.setSpacing(8)
        
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(8)
        
        title_label = QLabel("Create Alarm:", self.timer_widget)
        title_label.setStyleSheet("font-weight: 500; color: #ffffff; font-size: 15px;")
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
        container_layout.addWidget(self.timer_widget)
        
        # Build interactive Conversion widget
        self.conversion_widget = QFrame(self.container)
        self.conversion_widget.setObjectName("ConversionWidget")
        self.conversion_widget.setVisible(False)
        self.conversion_widget.setStyleSheet("""
            QFrame#ConversionWidget {
                background: transparent;
                border: none;
            }
            QLabel {
                border: none;
                background: transparent;
                color: #ffffff;
                font-family: 'Segoe UI', 'Inter', sans-serif;
                font-size: 14px;
            }
            QLineEdit {
                background-color: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                color: white;
                font-size: 14px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
            }
            QComboBox {
                background-color: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                color: white;
                font-size: 14px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
                min-width: 80px;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 20);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                color: white;
                font-size: 13px;
                font-weight: 500;
                padding: 6px 12px;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 35);
            }
        """)
        
        conv_layout = QHBoxLayout(self.conversion_widget)
        conv_layout.setContentsMargins(10, 5, 10, 5)
        conv_layout.setSpacing(8)
        
        self.conv_title_label = QLabel("Conversion:", self.conversion_widget)
        self.conv_title_label.setStyleSheet("font-weight: 500; color: #ffffff; font-size: 15px;")
        conv_layout.addWidget(self.conv_title_label)
        conv_layout.addStretch()
        
        self.conv_val_input = QLineEdit(self.conversion_widget)
        self.conv_val_input.setPlaceholderText("Value...")
        self.conv_val_input.setFixedWidth(80)
        conv_layout.addWidget(self.conv_val_input)
        
        self.conv_from_combo = QComboBox(self.conversion_widget)
        conv_layout.addWidget(self.conv_from_combo)
        
        to_label = QLabel("to", self.conversion_widget)
        to_label.setStyleSheet("color: rgba(255, 255, 255, 150);")
        conv_layout.addWidget(to_label)
        
        self.conv_to_combo = QComboBox(self.conversion_widget)
        conv_layout.addWidget(self.conv_to_combo)
        
        self.conv_convert_btn = QPushButton("Convert", self.conversion_widget)
        self.conv_convert_btn.clicked.connect(self.submit_interactive_conversion)
        conv_layout.addWidget(self.conv_convert_btn)
        
        self.conv_val_input.returnPressed.connect(self.submit_interactive_conversion)
        container_layout.addWidget(self.conversion_widget)
        
        # Build interactive Alert/Snooze widget
        self.alert_widget = QFrame(self.container)
        self.alert_widget.setObjectName("AlertWidget")
        self.alert_widget.setVisible(False)
        self.alert_widget.setStyleSheet("""
            QFrame#AlertWidget {
                background: transparent;
                border: none;
            }
            QLabel {
                border: none;
                background: transparent;
                color: #ffb86c;
                font-family: 'Segoe UI', 'Inter', sans-serif;
                font-size: 14px;
                font-weight: 500;
            }
            QLineEdit {
                background-color: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                color: white;
                font-size: 13px;
                padding: 4px;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 20);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                color: white;
                font-size: 13px;
                font-weight: 500;
                padding: 6px 10px;
                font-family: 'Segoe UI', 'Inter', sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 35);
            }
        """)
        
        alert_layout = QVBoxLayout(self.alert_widget)
        alert_layout.setContentsMargins(10, 5, 10, 5)
        alert_layout.setSpacing(10)
        
        self.alert_message_label = QLabel("Alert: Time is up!", self.alert_widget)
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
        container_layout.addWidget(self.alert_widget)
        
        self.snooze_custom_val.returnPressed.connect(self.snooze_timer_custom)
        
        # 6. Animation & Opacity Setup
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(150)
        
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
            
        # Collapse conversion widget if search bar text is edited to something other than bare category words
        if hasattr(self, 'conversion_widget') and self.conversion_widget.isVisible():
            txt = self.search_bar.text().strip().lower()
            categories = ('length', 'distance', 'area', 'volume', 'weight', 'mass', 'mass/weight', 'speed', 'pressure', 'power', 'temperature', 'temp', 'currency')
            if txt not in categories:
                self.conversion_widget.setVisible(False)
                self.setFixedSize(600, 78)
                self.center_on_screen()

    def process_command(self):
        user_text = self.search_bar.text().strip()
        if not user_text:
            if self.result_label.isVisible():
                self.copy_result_and_close()
            return
        
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
                
            if "Active Windows Startup Applications:" in result:
                self.result_label.setText(result)
                self.result_label.setVisible(True)
                self.setFixedSize(600, 350)
                self.center_on_screen()
                return
                
            if "Timer Command Formats:" in result:
                self.result_label.setVisible(False)
                self.timer_widget.setVisible(True)
                self.timer_val_input.clear()
                self.timer_task_input.clear()
                self.timer_val_input.setStyleSheet("")
                self.setFixedSize(600, 230)
                self.center_on_screen()
                QTimer.singleShot(10, self.timer_val_input.setFocus)
                return
                
            if result.startswith("Open Conversion: "):
                category = result[17:].strip()
                self.show_conversion_panel(category)
                return
                
            if result.startswith("Timer Created: "):
                data = result[15:]
                task, duration_ms_str, time_desc = data.split("|", 2)
                duration_ms = int(float(duration_ms_str))
                self.start_background_timer(task, duration_ms, time_desc)
                self.show_result_message(f"Timer set for '{task}' in {time_desc}!", show_actions=False, auto_hide=True)
                return

            if result == "Cancel Timers":
                if hasattr(self, 'active_timers') and self.active_timers:
                    count = len(self.active_timers)
                    for t in self.active_timers:
                        t["timer"].stop()
                        t["timer"].deleteLater()
                    self.active_timers.clear()
                    self.save_active_timers()
                    msg = f"Cancelled all active timers ({count} stopped)."
                else:
                    msg = "No active timers running."
                self.show_result_message(msg, show_actions=False, auto_hide=True)
                return

            if result.startswith("Cancel Timer Name: "):
                target_name = result[19:].strip().lower()
                if not hasattr(self, 'active_timers') or not self.active_timers:
                    msg = "No active timers running."
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
                        msg = f"No active timer matches '{target_name}'."
                    elif len(matches) == 1:
                        matched_timer = matches[0]
                        matched_timer["timer"].stop()
                        matched_timer["timer"].deleteLater()
                        self.active_timers.remove(matched_timer)
                        self.save_active_timers()
                        msg = f"Cancelled timer '{matched_timer['task']}'."
                    else:
                        names_str = ", ".join(f"'{t['task']}'" for t in matches)
                        msg = f"Multiple matches found ({names_str}). Please be more specific."
                        
                self.show_result_message(msg, show_actions=False, auto_hide=True)
                return

            if result.startswith("Copied: "):
                val = result[8:]
                clipboard = QApplication.clipboard()
                clipboard.setText(val)
                self.show_result_message(f"Copied '{val}' to clipboard!", show_actions=False, auto_hide=True)
                return

            if result.startswith("Copied File: "):
                data = result[13:]
                filepath, key = data.split("|", 1)
                from shellsense.services.file_shortcuts_parser import copy_file_to_clipboard
                try:
                    copy_file_to_clipboard(filepath)
                    msg = f"Copied file '{key}' to clipboard!"
                except Exception as e:
                    msg = f"<span style='color: #ff5252;'>Error copying file: {e}</span>"
                self.show_result_message(msg, show_actions=False, auto_hide=True)
                return

            if result.startswith("Copied Path: "):
                data = result[13:]
                filepath, key = data.split("|", 1)
                clipboard = QApplication.clipboard()
                clipboard.setText(filepath)
                self.show_result_message(f"Copied path '{filepath}' to clipboard!", show_actions=False, auto_hide=True)
                return

            if result.startswith("Opened File: "):
                data = result[13:]
                filepath, key = data.split("|", 1)
                try:
                    os.startfile(filepath)
                    msg = f"Opened file '{key}' successfully!"
                except Exception as e:
                    msg = f"<span style='color: #ff5252;'>Error opening file: {e}</span>"
                self.show_result_message(msg, show_actions=False, auto_hide=True)
                return
                
            if result.startswith("Error:"):
                msg = f"<span style='color: #ff5252;'>{result}</span>"
            else:
                msg = f"Result: {result}"
            self.show_result_message(msg, show_actions=True, auto_hide=False)
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
            self.show_result_message("<span style='color: #ff5252;'>Error:</span> Command failed to execute", show_actions=True, auto_hide=False)
            return
        
        self.search_bar.clear()
        self.hide()
    
    def toggle_visibility(self, trigger_source="Hotkey"):
        logger.info(f"{trigger_source} triggered. Toggling visibility.")
        if self.isVisible():
            if hasattr(self, 'timer_widget'):
                self.timer_widget.setVisible(False)
            if hasattr(self, 'conversion_widget'):
                self.conversion_widget.setVisible(False)
            self.hide()
            logger.info("Window hidden.")
        else:
            self.search_bar.clear()
            self.last_math_result = None
            self.result_label.setVisible(False)
            if hasattr(self, 'timer_widget'):
                self.timer_widget.setVisible(False)
            if hasattr(self, 'conversion_widget'):
                self.conversion_widget.setVisible(False)
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
            self.hide_and_clear()
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