import sys
import os

# Auto-resolve 'src' path for standalone execution
current_dir = os.path.dirname(os.path.abspath(__file__))
src_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if src_root not in sys.path:
    sys.path.insert(0, src_root)

import signal
import keyboard
import webbrowser
from ctypes import windll, wintypes
from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit, QVBoxLayout, QSystemTrayIcon, QMenu, QLabel, QFrame, QHBoxLayout, QComboBox, QPushButton, QScrollArea, QGraphicsOpacityEffect, QDialog
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QPropertyAnimation, QEvent

from shellsense.services.brain_service import BrainService
from shellsense.services.math_parser import evaluate_math
from shellsense.services.executor import CommandExecutor
from shellsense.ui.widgets import ScrollableLabel, ViewerTabWidget, TokenizedBar, SuggestionsDropdown
from shellsense.ui.dialogs import VaultPasswordDialog, DestructiveConfirmDialog, RegistrationDialog
from shellsense.core.logger import logger
from shellsense.core.constants import (
    CONVERSION_CATEGORIES_UNITS,
    CURRENCY_NAMES,
    TRANSLATE_LANGUAGES_MAP,
    TIMEZONE_NAMES
)

# Windows Constants for Session Notification
WM_WTSSESSION_CHANGE = 0x02B1
WTS_SESSION_UNLOCK = 0x08
NOTIFY_FOR_THIS_SESSION = 0

class HotkeySignaler(QObject):
    signal = pyqtSignal()

class ShellSenseUI(QWidget):
    feedback_submitted_signal = pyqtSignal(bool)
    
    def setFixedSize(self, *args):
        super().setFixedSize(*args)
        if hasattr(self, 'divider') and hasattr(self, 'result_label'):
            has_results = (self.result_label.isVisible() or 
                           self.timer_widget.isVisible() or 
                           (hasattr(self, 'viewer_tabs') and self.viewer_tabs.isVisible()) or
                           (hasattr(self, 'alarm_widget') and self.alarm_widget.isVisible()) or
                           self.alert_widget.isVisible() or
                           (hasattr(self, 'conversion_widget') and self.conversion_widget.isVisible()) or
                           (hasattr(self, 'feedback_panel') and self.feedback_panel.isVisible()))
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
            
            # Load user info
            import json
            from shellsense.core.config import USER_DIR
            user_info_path = os.path.join(USER_DIR, "user_info.json")
            self.user_info = None
            if os.path.exists(user_info_path):
                try:
                    with open(user_info_path, "r") as f:
                        self.user_info = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading user info: {e}")
            
            # Feedback States
            self.last_query = ""
            self.last_category = ""
            self.last_output = ""
            
            logger.info("Initializing UI...")
            self.initUI()
            
            # Install global event filter
            QApplication.instance().installEventFilter(self)
            
            logger.info("Initializing Tray...")
            self.initTray()
            
            # Register for Windows Session Notifications (Unlock events)
            logger.info("Scheduling Session Notifications...")
            QTimer.singleShot(500, self.register_session_notifications)
            
            self.signaler = HotkeySignaler()
            self.signaler.signal.connect(self.toggle_visibility, Qt.ConnectionType.QueuedConnection)
            self.feedback_submitted_signal.connect(self.on_feedback_submitted)
            
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
        
        self.last_query = f"timer {val} {unit}"
        self.last_category = "Timer (Interactive)"
        
        self.start_background_timer(task, duration_ms, time_desc)
        
        # Reset and hide form
        self.timer_widget.setVisible(False)
        self.search_bar.clear()
        
        # Show success message
        self.show_result_message(f"Timer set for '{task}' in {time_desc}!", show_actions=True, auto_hide=False)

    def set_timer_preset(self, val, unit):
        self.timer_val_input.setText(val)
        self.timer_unit_combo.setCurrentText(unit)
        self.timer_task_input.setFocus()

    def prepopulate_alarm_time(self):
        import datetime
        now = datetime.datetime.now()
        self.alarm_hour.setCurrentText(now.strftime("%I"))
        self.alarm_minute.setCurrentText(now.strftime("%M"))
        self.alarm_ampm.setCurrentText(now.strftime("%p"))
        self.alarm_task_input.clear()

    def submit_interactive_alarm(self):
        try:
            hour = int(self.alarm_hour.currentText())
            minute = int(self.alarm_minute.currentText())
        except ValueError:
            return
            
        ampm = self.alarm_ampm.currentText()
        task = self.alarm_task_input.text().strip() or "Alarm"
        
        # Parse into 24-hour format
        if ampm == "PM" and hour < 12:
            hour_24 = hour + 12
        elif ampm == "AM" and hour == 12:
            hour_24 = 0
        else:
            hour_24 = hour
            
        import datetime
        now = datetime.datetime.now()
        target_time = now.replace(hour=hour_24, minute=minute, second=0, microsecond=0)
        
        # If target time is in the past for today, set it for tomorrow
        if target_time <= now:
            target_time += datetime.timedelta(days=1)
            
        diff_ms = int((target_time - now).total_seconds() * 1000)
        time_desc = target_time.strftime("%I:%M %p")
        
        self.last_query = f"alarm {time_desc}"
        self.last_category = "Alarm (Interactive)"
        
        self.start_background_timer(task, diff_ms, f"Alarm at {time_desc}")
        
        # Reset and hide form
        self.alarm_widget.setVisible(False)
        self.search_bar.clear()
        
        # Show success message
        self.show_result_message(f"Alarm set for '{task}' at {time_desc}!", show_actions=True, auto_hide=False)

    def show_conversion_panel(self, category):
        self.current_conv_category = category
        
        # Format display title
        display_name = category.title()
        if category.lower() == "temp":
            display_name = "Temperature"
        elif category.lower() == "mass/weight":
            display_name = "Mass/Weight"
        elif category.lower() == "timezone":
            display_name = "Timezone"
        elif category.lower() == "number system":
            display_name = "Number System"
            
        self.conv_title_label.setText(f"{display_name} Conversion:")
        
        units = CONVERSION_CATEGORIES_UNITS.get(category.lower(), [])
        
        display_units = []
        if category.lower() == "currency":
            for u in units:
                display_units.append(CURRENCY_NAMES.get(u, u))
        elif category.lower() == "timezone":
            for u in units:
                display_units.append(TIMEZONE_NAMES.get(u, u))
        else:
            display_units = units
            
        self.conv_from_combo.clear()
        self.conv_to_combo.clear()
        self.conv_from_combo.addItems(display_units)
        self.conv_to_combo.addItems(display_units)
        
        try:
            self.conv_from_combo.view().setMinimumWidth(280)
            self.conv_to_combo.view().setMinimumWidth(280)
        except Exception:
            pass
        
        # Select defaults (e.g. from index 0, to index 1 if available)
        if len(units) > 1:
            self.conv_to_combo.setCurrentIndex(1)
            
        self.result_label.setVisible(False)
        self.timer_widget.setVisible(False)
        if hasattr(self, 'alert_widget'):
            self.alert_widget.setVisible(False)
            
        self.conversion_widget.setVisible(True)
        
        is_timezone = (category.lower() == "timezone")
        self.conv_val_input.setVisible(not is_timezone)
        self.conv_time_hour.setVisible(is_timezone)
        self.conv_time_minute.setVisible(is_timezone)
        self.conv_time_ampm.setVisible(is_timezone)
        
        # Expand window height to support form
        self.setFixedSize(700, 160)
        self.center_on_screen()
        
        if is_timezone:
            import datetime
            now = datetime.datetime.now()
            hour_12 = now.hour % 12
            if hour_12 == 0:
                hour_12 = 12
            ampm_str = "PM" if now.hour >= 12 else "AM"
            
            self.conv_time_hour.setCurrentText(f"{hour_12:02d}")
            self.conv_time_minute.setCurrentText(f"{now.minute:02d}")
            self.conv_time_ampm.setCurrentText(ampm_str)
            
            QTimer.singleShot(10, self.conv_time_hour.setFocus)
        else:
            self.conv_val_input.clear()
            self.conv_val_input.setStyleSheet("")
            QTimer.singleShot(10, self.conv_val_input.setFocus)

    def submit_interactive_conversion(self):
        category_lower = self.current_conv_category.lower()
        is_timezone = (category_lower == "timezone")
        
        if is_timezone:
            hour = self.conv_time_hour.currentText()
            minute = self.conv_time_minute.currentText()
            ampm = self.conv_time_ampm.currentText()
            val_str = f"{hour}:{minute} {ampm}"
        else:
            val_str = self.conv_val_input.text().strip()
            if not val_str:
                return
            
        is_number_system = (category_lower == "number system")
        
        from_unit = self.conv_from_combo.currentText()
        to_unit = self.conv_to_combo.currentText()
        
        if is_number_system:
            valid = True
            from_unit_clean = from_unit.lower()
            if "bin" in from_unit_clean:
                valid = all(c in "01" for c in val_str)
            elif "oct" in from_unit_clean:
                valid = all(c in "01234567" for c in val_str)
            elif "hex" in from_unit_clean:
                valid = all(c in "0123456789abcdefABCDEF" for c in val_str)
            elif "dec" in from_unit_clean:
                valid = all(c in "0123456789" for c in val_str)
                
            if not valid:
                self.conv_val_input.setStyleSheet("QLineEdit { border: 1px solid #ff5252; color: #ff5252; background-color: rgba(255, 255, 255, 15); border-radius: 6px; padding: 6px; }")
                return
            val = val_str
        else:
            if is_timezone:
                val = val_str
            else:
                try:
                    val = float(val_str)
                    if val.is_integer():
                        val = int(val)
                except ValueError:
                    self.conv_val_input.setStyleSheet("QLineEdit { border: 1px solid #ff5252; color: #ff5252; background-color: rgba(255, 255, 255, 15); border-radius: 6px; padding: 6px; }")
                    return
                
        self.conv_val_input.setStyleSheet("") # reset
        
        # Extract the short code (e.g. "USD" or "EST") if it is currency or timezone
        if category_lower in ("currency", "timezone"):
            from_unit = from_unit.split(" ")[0].strip()
            to_unit = to_unit.split(" ")[0].strip()
            
        # Construct conversion query
        if is_number_system:
            query = f"{from_unit} {val} to {to_unit}"
        else:
            query = f"{val} {from_unit} to {to_unit}"
        
        self.last_query = query
        self.last_category = "Unit/Base Conversion (Interactive)"
        
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

    def show_translation_panel(self):
        self.result_label.setVisible(False)
        self.timer_widget.setVisible(False)
        if hasattr(self, 'alert_widget'):
            self.alert_widget.setVisible(False)
        if hasattr(self, 'conversion_widget'):
            self.conversion_widget.setVisible(False)
            
        self.translation_widget.setVisible(True)
        self.trans_text_input.clear()
        self.trans_text_input.setStyleSheet("")
        
        try:
            self.trans_src_combo.view().setMinimumWidth(180)
            self.trans_dest_combo.view().setMinimumWidth(180)
        except Exception:
            pass
        
        # Select English to Tamil as default
        langs = sorted(list(TRANSLATE_LANGUAGES_MAP.keys()))
        if "English" in langs:
            self.trans_src_combo.setCurrentIndex(langs.index("English"))
        if "Tamil" in langs:
            self.trans_dest_combo.setCurrentIndex(langs.index("Tamil"))
        elif len(langs) > 1:
            self.trans_dest_combo.setCurrentIndex(1)
            
        self.setFixedSize(700, 160)
        self.center_on_screen()
        QTimer.singleShot(10, self.trans_text_input.setFocus)

    def submit_interactive_translation(self):
        phrase = self.trans_text_input.text().strip()
        if not phrase:
            return
            
        src_lang_name = self.trans_src_combo.currentText()
        dest_lang_name = self.trans_dest_combo.currentText()
        
        src_lang = TRANSLATE_LANGUAGES_MAP[src_lang_name]
        dest_lang = TRANSLATE_LANGUAGES_MAP[dest_lang_name]
        
        # Construct translation query
        query = f"translate {phrase} from {src_lang} to {dest_lang}"
        
        self.last_query = query
        self.last_category = "Translation (Interactive)"
        
        from shellsense.services.conversion_parser import evaluate_translation
        success, result = evaluate_translation(query)
        
        if success:
            res_str = result
        else:
            res_str = f"<span style='color: #ff5252;'>Error:</span> Translation failed"
            
        self.translation_widget.setVisible(False)
        self.search_bar.clear()
        self.show_result_message(res_str, show_actions=True, auto_hide=False)

    def show_snooze_panel(self, task):
        self.current_alert_task = task
        self.alert_message_label.setText(f"Alert: Time is up for '{task}'!")
        
        self.result_label.setVisible(False)
        self.timer_widget.setVisible(False)
        self.alert_widget.setVisible(True)
        
        self.setFixedSize(600, 190)
        self.center_on_screen()
        self.show()
        self.raise_()
        self.activateWindow()
        self.snooze_custom_val.clear()
        self.snooze_custom_val.setStyleSheet("QLineEdit { background-color: rgba(255, 255, 255, 15); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; color: white; font-size: 13px; padding: 4px; font-family: 'Segoe UI', sans-serif; }")
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
        self.show_result_message(f"Snoozed '{task}' for {time_desc}!", show_actions=True, auto_hide=False)

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
        if hasattr(self, 'divider'):
            self.divider.setVisible(True)
        
        # Store output for feedback (strip HTML tags)
        import re
        self.last_output = re.sub(r'<[^>]*>', '', text).strip()
        
        if hasattr(self, 'feedback_panel'):
            self.feedback_panel.setVisible(False)
            
        if hasattr(self, 'result_actions_widget'):
            self.result_actions_widget.setVisible(show_actions)
        if show_actions:
            self.setFixedSize(620, 220)
        else:
            self.setFixedSize(620, 160)
        self.center_on_screen()
        if hasattr(self, 'search_bar'):
            self.search_bar.blockSignals(True)
            self.search_bar.clear()
            self.search_bar.blockSignals(False)
            self.search_bar.setFocus()
        if auto_hide:
            QTimer.singleShot(1500, self.hide_and_clear)

    def set_feedback_rating(self, rating):
        self.selected_rating = rating
        for i, btn in enumerate(self.rating_buttons):
            btn.setChecked(i + 1 == rating)

    def toggle_feedback_panel(self):
        if not hasattr(self, 'feedback_panel'):
            return
            
        is_visible = not self.feedback_panel.isVisible()
        self.feedback_panel.setVisible(is_visible)
        
        if is_visible:
            # Clear previous status/input
            self.feedback_status_label.setVisible(False)
            self.feedback_status_label.setText("")
            self.feedback_comment_input.clear()
            self.selected_rating = None
            for btn in self.rating_buttons:
                btn.setChecked(False)
                
            self.setFixedSize(600, 360)
            self.feedback_comment_input.setFocus()
        else:
            self.setFixedSize(600, 220)
            
        self.center_on_screen()

    def toggle_records_panel(self):
        if not hasattr(self, 'viewer_tabs'):
            return
        is_visible = not self.viewer_tabs.isVisible()
        self.viewer_tabs.setVisible(is_visible)
        if is_visible:
            self.viewer_tabs.refresh_all()
            self.setFixedSize(680, 480)
            self.viewer_tabs.setFixedHeight(340)
        else:
            self.setFixedSize(620, 84)
        self.center_on_screen()

    def _on_command_bar_collected(self, payload: dict):
        cmd_type = payload.get("type")
        if cmd_type == "command":
            cmd = payload.get("command") or payload.get("value")
            if cmd:
                logger.info(f"Executing collected command from TokenizedBar: {cmd}")
                import subprocess
                try:
                    subprocess.Popen(cmd, shell=True)
                    self.show_result_message(f"⚡ Executed: <code>{cmd}</code>", show_actions=True, auto_hide=False)
                except Exception as e:
                    self.show_result_message(f"<span style='color: #ff5252;'>Execution Error:</span> {e}", show_actions=True, auto_hide=False)
        elif cmd_type == "password":
            self.show_result_message(f"🔒 Password securely saved in SQLite Vault: <b>{payload.get('key')}</b>", show_actions=False, auto_hide=True)
            if hasattr(self, 'viewer_tabs'):
                self.viewer_tabs.refresh_all()
        elif cmd_type == "file":
            self.show_result_message(f"📁 File shortcut saved: <b>{payload.get('key')}</b>", show_actions=False, auto_hide=True)
            if hasattr(self, 'viewer_tabs'):
                self.viewer_tabs.refresh_all()

    def _on_intent_selected(self, candidate: dict):
        cand_type = candidate.get("type")
        if cand_type == "locked_snippet":
            key_name = candidate.get("key_name", "")
            enc_val = candidate.get("enc_val", "")
            dialog = VaultPasswordDialog(key_name, enc_val, self)
            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.decrypted_text:
                try:
                    clipboard = QApplication.clipboard()
                    if clipboard:
                        clipboard.setText(dialog.decrypted_text)
                except Exception:
                    pass
                self.show_result_message(f"🔓 Unlocked & copied '{key_name}' to clipboard!", show_actions=True, auto_hide=False)
            else:
                self.show_result_message("<span style='color: #ef4444;'>🔒 Access Denied: Incorrect or cancelled password prompt.</span>", show_actions=True, auto_hide=False)
            return
        elif cand_type == "direct_eval":
            res = candidate.get("result", "")
            self.last_math_result = res
            self.last_query = candidate.get("command", "")
            self.last_category = "Calculation / Conversion"
            self.last_output = res
            self.show_result_message(f"✅ Copied to clipboard: <b>{res}</b>", show_actions=True, auto_hide=False)
            return
        elif cand_type == "direct_action":
            # Direct action (timers, file downloads) - route into process_command
            cmd = candidate.get("command", "")
            if hasattr(self, 'search_bar'):
                self.search_bar.blockSignals(True)
                self.search_bar.setText(cmd)
                self.search_bar.blockSignals(False)
            self.process_command()
            return

        cmd = candidate.get("command", "")
        title = candidate.get("title", "")
        self.show_result_message(f"⚡ Ready to execute: <code>{cmd}</code> (Press Enter to run)", show_actions=True, auto_hide=False)

    def close_interactive_pane_and_show_feedback(self, query, category, output_msg):
        # Hide interactive widgets
        if hasattr(self, 'timer_widget'):
            self.timer_widget.setVisible(False)
        if hasattr(self, 'alarm_widget'):
            self.alarm_widget.setVisible(False)
        if hasattr(self, 'conversion_widget'):
            self.conversion_widget.setVisible(False)
        if hasattr(self, 'translation_widget'):
            self.translation_widget.setVisible(False)
        if hasattr(self, 'alert_widget'):
            self.alert_widget.setVisible(False)
            
        # Store metadata for feedback
        self.last_query = query
        self.last_category = category
        self.last_output = output_msg
        
        # Show feedback panel
        if hasattr(self, 'feedback_panel'):
            self.feedback_panel.setVisible(True)
            self.feedback_status_label.setVisible(False)
            self.feedback_status_label.setText("")
            self.feedback_comment_input.clear()
            self.selected_rating = None
            if hasattr(self, 'rating_buttons'):
                for btn in self.rating_buttons:
                    btn.setChecked(False)
            
            # Show a size appropriate for the search bar + feedback panel
            self.setFixedSize(600, 260)
            self.center_on_screen()
            self.feedback_comment_input.setFocus()

    def submit_feedback(self):
        if not getattr(self, 'selected_rating', None):
            self.feedback_status_label.setText("<span style='color: #ff5252;'>Please select a rating (1-5) before submitting.</span>")
            self.feedback_status_label.setVisible(True)
            return

        comment = self.feedback_comment_input.text().strip()
        
        # Prepare payload
        payload = {
            "category": self.last_category,
            "query": self.last_query,
            "output": self.last_output,
            "rating": str(self.selected_rating),
            "comment": comment,
            "name": self.user_info.get("name", "Unknown") if self.user_info else "Unknown",
            "email": self.user_info.get("email", "Unknown") if self.user_info else "Unknown"
        }
        
        self.feedback_status_label.setText("Submitting feedback...")
        self.feedback_status_label.setStyleSheet("QLabel { color: #007aff; }")
        self.feedback_status_label.setVisible(True)
        
        # Submit in background thread
        def run_submission():
            import time
            from shellsense.core.config import FEEDBACK_URL, FEEDBACK_ENTRY_CATEGORY, FEEDBACK_ENTRY_QUERY, FEEDBACK_ENTRY_OUTPUT, FEEDBACK_ENTRY_RATING, FEEDBACK_ENTRY_COMMENT, FEEDBACK_ENTRY_USER_NAME, FEEDBACK_ENTRY_USER_EMAIL
            success = False
            
            if FEEDBACK_URL:
                # Map payload keys to Google Form entries
                form_data = {
                    FEEDBACK_ENTRY_CATEGORY: payload["category"],
                    FEEDBACK_ENTRY_QUERY: payload["query"],
                    FEEDBACK_ENTRY_OUTPUT: payload["output"],
                    FEEDBACK_ENTRY_RATING: payload["rating"],
                    FEEDBACK_ENTRY_COMMENT: payload["comment"],
                    FEEDBACK_ENTRY_USER_NAME: payload["name"],
                    FEEDBACK_ENTRY_USER_EMAIL: payload["email"]
                }
                
                import urllib.request
                import urllib.parse
                try:
                    encoded_data = urllib.parse.urlencode(form_data).encode('utf-8')
                    req = urllib.request.Request(FEEDBACK_URL, data=encoded_data, method='POST')
                    with urllib.request.urlopen(req, timeout=5) as response:
                        success = True
                except Exception as e:
                    logger.error(f"Failed to send feedback to Google Form: {e}")
                    success = False
            
            # Save locally as fallback or primary if no URL
            import json
            from shellsense.core.config import USER_DIR
            local_log_path = os.path.join(USER_DIR, "feedback_log.json")
            
            feedback_entry = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                **payload,
                "submitted_online": success
            }
            
            try:
                log_data = []
                if os.path.exists(local_log_path):
                    with open(local_log_path, "r", encoding="utf-8") as f:
                        log_data = json.load(f)
                log_data.append(feedback_entry)
                with open(local_log_path, "w", encoding="utf-8") as f:
                    json.dump(log_data, f, indent=4)
            except Exception as e:
                logger.error(f"Failed to save feedback log locally: {e}")
            
            # Thread-safe GUI notification via pyqtSignal
            self.feedback_submitted_signal.emit(success)
            
        import threading
        threading.Thread(target=run_submission, daemon=True).start()

    def on_feedback_submitted(self, success):
        if success:
            msg = "Thank you! Feedback submitted successfully."
            style = "QLabel { color: #4cd964; }"
        else:
            msg = "Feedback saved locally. Thank you!"
            style = "QLabel { color: #ff9500; }"
            
        self.feedback_status_label.setText(msg)
        self.feedback_status_label.setStyleSheet(style)
        self.feedback_status_label.setVisible(True)
        
        # Close the window after 1.5 seconds
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
        if hasattr(self, 'viewer_tabs'):
            self.viewer_tabs.setVisible(False)
        if hasattr(self, 'timer_widget'):
            self.timer_widget.setVisible(False)
        if hasattr(self, 'alarm_widget'):
            self.alarm_widget.setVisible(False)
        if hasattr(self, 'alert_widget'):
            self.alert_widget.setVisible(False)
        if hasattr(self, 'conversion_widget'):
            self.conversion_widget.setVisible(False)
        if hasattr(self, 'translation_widget'):
            self.translation_widget.setVisible(False)
        if hasattr(self, 'feedback_panel'):
            self.feedback_panel.setVisible(False)
            self.feedback_comment_input.clear()
            self.selected_rating = None
            if hasattr(self, 'rating_buttons'):
                for btn in self.rating_buttons:
                    btn.setChecked(False)
        self.setFixedSize(620, 84)
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
        
        hub_action = QAction("Open ShellSense Hub (Records & Settings)", self)
        hub_action.triggered.connect(self.open_storage_viewer)

        repair_action = QAction("Repair Hotkey", self)
        repair_action.triggered.connect(lambda: self.refresh_hotkey(force=True))
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(hub_action)
        tray_menu.addAction(repair_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.setToolTip("ShellSense is active")
        self.tray_icon.activated.connect(self.on_tray_activated)

    def open_storage_viewer(self):
        """Opens the desktop SQLite Command & Storage Hub tabs dialog."""
        if not hasattr(self, '_storage_viewer_dialog') or self._storage_viewer_dialog is None:
            self._storage_viewer_dialog = QDialog()
            self._storage_viewer_dialog.setWindowTitle("ShellSense Hub — Storage & Preferences")
            self._storage_viewer_dialog.resize(860, 560)
            self._storage_viewer_dialog.setStyleSheet("""
                QDialog {
                    background-color: #0f1118;
                }
            """)
            dialog_layout = QVBoxLayout(self._storage_viewer_dialog)
            dialog_layout.setContentsMargins(14, 14, 14, 14)
            self.storage_viewer_widget = ViewerTabWidget(self._storage_viewer_dialog)
            dialog_layout.addWidget(self.storage_viewer_widget)
        self.storage_viewer_widget.refresh_all()
        self._storage_viewer_dialog.show()
        self._storage_viewer_dialog.raise_()
        self._storage_viewer_dialog.activateWindow()

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
                background-color: rgba(18, 20, 28, 0.96);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 14px;
            }
        """)
        main_layout.addWidget(self.container)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(14, 14, 14, 14)
        container_layout.setSpacing(10)
        
        # 3. Modern Minimalist TokenizedBar (Clean, distraction-free single-stage entry)
        self.search_bar = TokenizedBar(self.container)
        self.search_bar.setFixedHeight(46)
        self.suggestions_dropdown = None
        self.search_bar.returnPressed.connect(self.process_command)
        self.search_bar.textChanged.connect(self.on_text_changed)
        self.search_bar.command_collected.connect(self._on_command_bar_collected)
        self.search_bar.intent_selected.connect(self._on_intent_selected)
        self.search_bar.installEventFilter(self)
        container_layout.addWidget(self.search_bar)
        
        # Placeholder rotation timer
        self.placeholder_timer = QTimer(self)
        self.placeholder_timer.timeout.connect(self.update_placeholder_suggestion)
        
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
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 7px;
                color: #e2e8f0;
                font-size: 12px;
                font-weight: 500;
                padding: 6px 14px;
                font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, sans-serif;
                min-width: 90px;
            }
            QPushButton:hover {
                background-color: rgba(59, 130, 246, 0.22);
                border-color: rgba(59, 130, 246, 0.45);
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: rgba(59, 130, 246, 0.35);
            }
            QPushButton:focus {
                border: 1px solid rgba(59, 130, 246, 0.5);
                outline: none;
            }
        """)
        
        result_actions_layout = QHBoxLayout(self.result_actions_widget)
        result_actions_layout.setContentsMargins(10, 0, 10, 5)
        result_actions_layout.setSpacing(8)
        
        result_actions_layout.addStretch()
        
        self.result_records_btn = QPushButton("Records 📋", self.result_actions_widget)
        self.result_records_btn.clicked.connect(self.toggle_records_panel)
        result_actions_layout.addWidget(self.result_records_btn)

        self.result_feedback_btn = QPushButton("Feedback 💬", self.result_actions_widget)
        self.result_feedback_btn.clicked.connect(self.toggle_feedback_panel)
        result_actions_layout.addWidget(self.result_feedback_btn)
        
        self.result_close_btn = QPushButton("Close [Esc/Enter]", self.result_actions_widget)
        self.result_close_btn.clicked.connect(self.hide_and_clear)
        result_actions_layout.addWidget(self.result_close_btn)
        
        container_layout.addWidget(self.result_actions_widget)

        # 5c. SQLite Viewer Tabs for Vault, Shortcuts, Commands
        self.viewer_tabs = ViewerTabWidget(self.container)
        self.viewer_tabs.wire_to_bar(self.search_bar)
        self.viewer_tabs.setVisible(False)
        self.viewer_tabs.setFixedHeight(340)
        container_layout.addWidget(self.viewer_tabs)
        
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
            QLineEdit:focus {
                border: 1px solid rgba(255, 255, 255, 0.4);
                background-color: rgba(255, 255, 255, 20);
                outline: none;
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
            QComboBox:focus {
                border: 1px solid rgba(255, 255, 255, 0.4);
                background-color: rgba(255, 255, 255, 20);
                outline: none;
            }
            QComboBox::drop-down {
                border: none;
                background: transparent;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a24;
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.15);
                selection-background-color: rgba(255, 255, 255, 30);
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
            QPushButton:focus {
                border: 1px solid rgba(255, 255, 255, 0.4);
                outline: none;
            }
        """)
        
        timer_layout = QVBoxLayout(self.timer_widget)
        timer_layout.setContentsMargins(10, 5, 10, 5)
        timer_layout.setSpacing(8)
        
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(8)
        
        title_label = QLabel("Set Timer:", self.timer_widget)
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

        # Timer Presets Row
        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        preset_label = QLabel("Presets:", self.timer_widget)
        preset_label.setStyleSheet("color: rgba(255, 255, 255, 180); font-size: 12px;")
        preset_row.addWidget(preset_label)
        
        presets = [("5m", "5", "Minutes"), ("10m", "10", "Minutes"), ("15m", "15", "Minutes"), ("30m", "30", "Minutes"), ("1h", "1", "Hours")]
        for label, val, unit in presets:
            pbtn = QPushButton(label, self.timer_widget)
            pbtn.setFixedWidth(45)
            pbtn.setFixedHeight(24)
            pbtn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 15);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 4px;
                    color: rgba(255, 255, 255, 220);
                    font-size: 11px;
                    font-weight: 500;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 30);
                    color: white;
                }
            """)
            pbtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            def make_setter(v=val, u=unit):
                return lambda: self.set_timer_preset(v, u)
            pbtn.clicked.connect(make_setter())
            preset_row.addWidget(pbtn)
        preset_row.addStretch()
        timer_layout.addLayout(preset_row)
        
        self.timer_task_input = QLineEdit(self.timer_widget)
        self.timer_task_input.setPlaceholderText("Reminder message (e.g. check the oven, sleep, eat)")
        timer_layout.addWidget(self.timer_task_input)
        
        row3_layout = QHBoxLayout()
        self.timer_close_btn = QPushButton("Close", self.timer_widget)
        self.timer_close_btn.clicked.connect(self.hide_and_clear)
        self.start_timer_btn = QPushButton("Start Timer", self.timer_widget)
        self.start_timer_btn.clicked.connect(self.submit_interactive_timer)
        row3_layout.addStretch()
        row3_layout.addWidget(self.timer_close_btn)
        row3_layout.addWidget(self.start_timer_btn)
        timer_layout.addLayout(row3_layout)
        
        self.timer_val_input.returnPressed.connect(self.submit_interactive_timer)
        self.timer_task_input.returnPressed.connect(self.submit_interactive_timer)
        container_layout.addWidget(self.timer_widget)

        # Build interactive Alarm form widget
        self.alarm_widget = QFrame(self.container)
        self.alarm_widget.setObjectName("AlarmWidget")
        self.alarm_widget.setVisible(False)
        self.alarm_widget.setStyleSheet("""
            QFrame#AlarmWidget {
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
                min-width: 60px;
            }
            QComboBox::drop-down {
                border: none;
                background: transparent;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a24;
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.15);
                selection-background-color: rgba(255, 255, 255, 30);
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
        
        alarm_layout = QVBoxLayout(self.alarm_widget)
        alarm_layout.setContentsMargins(10, 5, 10, 5)
        alarm_layout.setSpacing(8)
        
        arow1_layout = QHBoxLayout()
        arow1_layout.setSpacing(8)
        
        atitle_label = QLabel("Set Alarm:", self.alarm_widget)
        atitle_label.setStyleSheet("background: transparent; font-weight: 500; color: #ffffff; font-size: 15px;")
        arow1_layout.addWidget(atitle_label)
        
        arow1_layout.addStretch()
        
        # Hour dropdown
        self.alarm_hour = QComboBox(self.alarm_widget)
        self.alarm_hour.addItems([f"{i:02d}" for i in range(1, 13)])
        arow1_layout.addWidget(self.alarm_hour)
        
        # Minute dropdown
        self.alarm_minute = QComboBox(self.alarm_widget)
        self.alarm_minute.addItems([f"{i:02d}" for i in range(60)])
        arow1_layout.addWidget(self.alarm_minute)
        
        # AM/PM dropdown
        self.alarm_ampm = QComboBox(self.alarm_widget)
        self.alarm_ampm.addItems(["AM", "PM"])
        arow1_layout.addWidget(self.alarm_ampm)
        
        alarm_layout.addLayout(arow1_layout)
        
        self.alarm_task_input = QLineEdit(self.alarm_widget)
        self.alarm_task_input.setPlaceholderText("Alarm message (e.g. daily standup, catch the train)")
        alarm_layout.addWidget(self.alarm_task_input)
        
        arow3_layout = QHBoxLayout()
        self.alarm_close_btn = QPushButton("Close", self.alarm_widget)
        self.alarm_close_btn.clicked.connect(self.hide_and_clear)
        self.start_alarm_btn = QPushButton("Set Alarm", self.alarm_widget)
        self.start_alarm_btn.clicked.connect(self.submit_interactive_alarm)
        arow3_layout.addStretch()
        arow3_layout.addWidget(self.alarm_close_btn)
        arow3_layout.addWidget(self.start_alarm_btn)
        alarm_layout.addLayout(arow3_layout)
        
        self.alarm_task_input.returnPressed.connect(self.submit_interactive_alarm)
        container_layout.addWidget(self.alarm_widget)
        
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
            QComboBox::drop-down {
                border: none;
                background: transparent;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a24;
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.15);
                selection-background-color: rgba(255, 255, 255, 30);
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
        
        self.conv_time_hour = QComboBox(self.conversion_widget)
        self.conv_time_hour.addItems([f"{i:02d}" for i in range(1, 13)])
        self.conv_time_hour.setFixedWidth(55)
        self.conv_time_hour.setVisible(False)
        conv_layout.addWidget(self.conv_time_hour)
        
        self.conv_time_minute = QComboBox(self.conversion_widget)
        self.conv_time_minute.addItems([f"{i:02d}" for i in range(0, 60)])
        self.conv_time_minute.setFixedWidth(55)
        self.conv_time_minute.setVisible(False)
        conv_layout.addWidget(self.conv_time_minute)
        
        self.conv_time_ampm = QComboBox(self.conversion_widget)
        self.conv_time_ampm.addItems(["AM", "PM"])
        self.conv_time_ampm.setFixedWidth(65)
        self.conv_time_ampm.setVisible(False)
        conv_layout.addWidget(self.conv_time_ampm)
        
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
        
        # Build interactive Translation widget
        self.translation_widget = QFrame(self.container)
        self.translation_widget.setObjectName("TranslationWidget")
        self.translation_widget.setVisible(False)
        self.translation_widget.setStyleSheet("""
            QFrame#TranslationWidget {
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
            QComboBox::drop-down {
                border: none;
                background: transparent;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a24;
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.15);
                selection-background-color: rgba(255, 255, 255, 30);
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
        
        trans_layout = QHBoxLayout(self.translation_widget)
        trans_layout.setContentsMargins(10, 5, 10, 5)
        trans_layout.setSpacing(8)
        
        self.trans_title_label = QLabel("Translation:", self.translation_widget)
        self.trans_title_label.setStyleSheet("font-weight: 500; color: #ffffff; font-size: 15px;")
        trans_layout.addWidget(self.trans_title_label)
        trans_layout.addStretch()
        
        self.trans_text_input = QLineEdit(self.translation_widget)
        self.trans_text_input.setPlaceholderText("Enter text...")
        self.trans_text_input.setFixedWidth(120)
        trans_layout.addWidget(self.trans_text_input)
        
        self.trans_src_combo = QComboBox(self.translation_widget)
        trans_layout.addWidget(self.trans_src_combo)
        
        to_trans_label = QLabel("to", self.translation_widget)
        to_trans_label.setStyleSheet("color: rgba(255, 255, 255, 150);")
        trans_layout.addWidget(to_trans_label)
        
        self.trans_dest_combo = QComboBox(self.translation_widget)
        trans_layout.addWidget(self.trans_dest_combo)
        
        self.trans_translate_btn = QPushButton("Translate", self.translation_widget)
        self.trans_translate_btn.clicked.connect(self.submit_interactive_translation)
        trans_layout.addWidget(self.trans_translate_btn)
        
        self.trans_text_input.returnPressed.connect(self.submit_interactive_translation)
        
        langs = sorted(list(TRANSLATE_LANGUAGES_MAP.keys()))
        self.trans_src_combo.addItems(langs)
        self.trans_dest_combo.addItems(langs)
        
        container_layout.addWidget(self.translation_widget)
        
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
        
        self.snooze_close_btn = QPushButton("Close", self.alert_widget)
        self.snooze_close_btn.clicked.connect(lambda: self.close_interactive_pane_and_show_feedback("snooze", "Snooze", "Snooze Alert Closed"))
        btn_layout.addWidget(self.snooze_close_btn)
        
        alert_layout.addLayout(btn_layout)
        container_layout.addWidget(self.alert_widget)
        
        self.snooze_custom_val.returnPressed.connect(self.snooze_timer_custom)
        
        # Build interactive Feedback widget
        self.feedback_panel = QFrame(self.container)
        self.feedback_panel.setObjectName("FeedbackPanel")
        self.feedback_panel.setVisible(False)
        self.feedback_panel.setStyleSheet("""
            QFrame#FeedbackPanel {
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
            QPushButton {
                background-color: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                color: white;
                font-size: 13px;
                font-weight: 500;
                padding: 6px 12px;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 30);
            }
            QPushButton:checked {
                background-color: rgba(0, 122, 255, 180);
                border-color: rgba(0, 122, 255, 255);
            }
        """)

        feedback_layout = QVBoxLayout(self.feedback_panel)
        feedback_layout.setContentsMargins(10, 5, 10, 5)
        feedback_layout.setSpacing(8)

        # Rating row
        rating_row = QHBoxLayout()
        rating_row.setSpacing(6)
        
        rate_title = QLabel("Rate this result:", self.feedback_panel)
        rate_title.setStyleSheet("font-weight: 500; color: #ffffff;")
        rating_row.addWidget(rate_title)
        rating_row.addStretch()

        self.rating_buttons = []
        self.selected_rating = None

        # Build 1-5 rating buttons
        for i in range(1, 6):
            btn = QPushButton(str(i), self.feedback_panel)
            btn.setCheckable(True)
            btn.setFixedWidth(30)
            btn.setFixedHeight(30)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 15);
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 15px;
                    color: white;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 30);
                }
                QPushButton:checked {
                    background-color: rgba(0, 122, 255, 200);
                    border-color: rgba(0, 122, 255, 255);
                    color: white;
                }
                QPushButton:focus {
                    outline: none;
                }
            """)
            btn.clicked.connect(lambda checked, r=i: self.set_feedback_rating(r))
            rating_row.addWidget(btn)
            self.rating_buttons.append(btn)

        feedback_layout.addLayout(rating_row)

        # Suggestion row
        comment_row = QHBoxLayout()
        comment_row.setSpacing(8)

        self.feedback_comment_input = QLineEdit(self.feedback_panel)
        self.feedback_comment_input.setPlaceholderText("How can we improve this result? (Optional)")
        comment_row.addWidget(self.feedback_comment_input)

        self.feedback_submit_btn = QPushButton("Submit", self.feedback_panel)
        self.feedback_submit_btn.clicked.connect(self.submit_feedback)
        self.feedback_comment_input.returnPressed.connect(self.submit_feedback)
        comment_row.addWidget(self.feedback_submit_btn)
        
        feedback_layout.addLayout(comment_row)

        # Status label
        self.feedback_status_label = QLabel("", self.feedback_panel)
        self.feedback_status_label.setStyleSheet("color: rgba(255, 255, 255, 180); font-size: 12px; font-style: italic;")
        self.feedback_status_label.setVisible(False)
        feedback_layout.addWidget(self.feedback_status_label)

        container_layout.addWidget(self.feedback_panel)

        # 6. Animation & Opacity Setup
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(150)
        
        self.setFixedSize(600, 88)
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
        if self.result_label.isVisible() or (hasattr(self, 'result_actions_widget') and self.result_actions_widget.isVisible()) or (hasattr(self, 'viewer_tabs') and self.viewer_tabs.isVisible()):
            self.result_label.setVisible(False)
            if hasattr(self, 'result_actions_widget'):
                self.result_actions_widget.setVisible(False)
            if hasattr(self, 'viewer_tabs'):
                self.viewer_tabs.setVisible(False)
            if hasattr(self, 'divider'):
                self.divider.setVisible(False)
            self.setFixedSize(620, 84)
            self.center_on_screen()
            
        # Collapse timer widget if search bar text is edited to something other than timer triggers
        if hasattr(self, 'timer_widget') and self.timer_widget.isVisible():
            txt = self.search_bar.text().strip().lower()
            if txt not in ('timer', 'timers', 'set timer', 'set a timer', 'timer pane'):
                self.timer_widget.setVisible(False)
                self.setFixedSize(600, 88)
                self.center_on_screen()
                
        # Collapse alarm widget if search bar text is edited to something other than alarm triggers
        if hasattr(self, 'alarm_widget') and self.alarm_widget.isVisible():
            txt = self.search_bar.text().strip().lower()
            if txt not in ('alarm', 'alarms', 'set alarm', 'set a alarm', 'set an alarm', 'alarm pane'):
                self.alarm_widget.setVisible(False)
                self.setFixedSize(600, 88)
                self.center_on_screen()
                
        # Collapse alert widget if user types a new command
        if hasattr(self, 'alert_widget') and self.alert_widget.isVisible():
            self.alert_widget.setVisible(False)
            self.setFixedSize(600, 88)
            self.center_on_screen()
            
        # Collapse conversion widget if search bar text is edited to something other than bare category words
        if hasattr(self, 'conversion_widget') and self.conversion_widget.isVisible():
            txt = self.search_bar.text().strip().lower()
            categories = ('length', 'distance', 'area', 'volume', 'weight', 'mass', 'mass/weight', 'speed', 'pressure', 'power', 'temperature', 'temp', 'currency', 'timezone', 'tz', 'time', 'timezone conversion', 'time conversion', 'number system', 'number conversion', 'number system conversion', 'base conversion', 'base', 'number base')
            if txt not in categories:
                self.conversion_widget.setVisible(False)
                self.setFixedSize(600, 88)
                self.center_on_screen()

        # Collapse translation widget if search bar text is edited to something other than translation keywords
        if hasattr(self, 'translation_widget') and self.translation_widget.isVisible():
            txt = self.search_bar.text().strip().lower()
            trans_keywords = ("translate", "translation", "translate language", "translation pane")
            if txt not in trans_keywords:
                self.translation_widget.setVisible(False)
                self.setFixedSize(600, 88)
                self.center_on_screen()

    def process_command(self):
        user_text = self.search_bar.text().strip()
        if not user_text:
            if self.result_label.isVisible():
                self.hide_and_clear()
            return
            
        if user_text.lower() in ("exit", "quit", "close"):
            logger.info("Direct exit command received. Shutting down...")
            try:
                import keyboard
                keyboard.unhook_all()
            except:
                pass
            QApplication.quit()
            return
            
        if user_text.lower() in ("cancel shutdown", "abort shutdown", "cancel scheduled shutdown", "shutdown -a", "shutdown /a", "stop shutdown"):
            logger.info("Direct abort shutdown command received.")
            import subprocess
            try:
                subprocess.Popen(["shutdown", "/a"], shell=False)
                self.show_result_message("Scheduled shutdown cancelled successfully!", show_actions=True, auto_hide=False)
            except Exception as e:
                self.show_result_message(f"<span style='color: #ff5252;'>Error:</span> Failed to cancel shutdown: {e}", show_actions=True, auto_hide=False)
            return
        
        self.last_query = user_text
        
        # Intercept math calculations, conversions, and translations
        is_math, result = evaluate_math(user_text)
        if is_math:
            # Determine which sub-parser matched to resolve category for feedback
            from shellsense.services.math_parser import evaluate_help, evaluate_snippets
            from shellsense.services.download_finder import evaluate_last_download
            from shellsense.services.system_tuner import evaluate_system_tuner
            from shellsense.services.file_shortcuts_parser import evaluate_file_shortcuts
            from shellsense.services.timer_service import evaluate_timer
            from shellsense.services.conversion_parser import evaluate_conversion, evaluate_translation

            if evaluate_help(user_text)[0]:
                self.last_category = "Help"
            elif evaluate_snippets(user_text)[0]:
                self.last_category = "Snippets"
            elif evaluate_last_download(user_text)[0]:
                self.last_category = "File Finder"
            elif evaluate_system_tuner(user_text)[0]:
                self.last_category = "System Tuning"
            elif evaluate_file_shortcuts(user_text)[0]:
                self.last_category = "File Shortcut"
            elif evaluate_timer(user_text)[0]:
                self.last_category = "Timer"
            elif evaluate_conversion(user_text)[0]:
                self.last_category = "Unit/Base Conversion"
            elif evaluate_translation(user_text)[0]:
                self.last_category = "Translation"
            else:
                self.last_category = "Math & Science"

            if "Available Functions:" in result:
                self.result_label.setText(result)
                self.result_label.setVisible(True)
                self.setFixedSize(600, 380)
                self.center_on_screen()
                return
                
            if "Active Windows Startup Applications:" in result:
                self.result_label.setText(result)
                self.result_label.setVisible(True)
                self.setFixedSize(600, 380)
                self.center_on_screen()
                return
                
            if result.startswith("Open Timer: "):
                self.result_label.setVisible(False)
                self.timer_widget.setVisible(True)
                self.timer_val_input.clear()
                self.timer_task_input.clear()
                self.timer_val_input.setStyleSheet("")
                self.setFixedSize(600, 290)
                self.center_on_screen()
                QTimer.singleShot(10, self.timer_val_input.setFocus)
                return
                
            if result.startswith("Open Alarm: "):
                self.result_label.setVisible(False)
                self.alarm_widget.setVisible(True)
                self.prepopulate_alarm_time()
                self.setFixedSize(600, 260)
                self.center_on_screen()
                QTimer.singleShot(10, self.alarm_task_input.setFocus)
                return
                
            if result.startswith("Open Conversion: "):
                category = result[17:].strip()
                self.show_conversion_panel(category)
                return
                
            if result.startswith("Open Translation: "):
                self.show_translation_panel()
                return
                
            if result.startswith("Timer Created: "):
                data = result[15:]
                task, duration_ms_str, time_desc = data.split("|", 2)
                duration_ms = int(float(duration_ms_str))
                self.start_background_timer(task, duration_ms, time_desc)
                self.show_result_message(f"Timer set for '{task}' in {time_desc}!", show_actions=True, auto_hide=False)
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
                self.show_result_message(msg, show_actions=True, auto_hide=False)
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
                        
                self.show_result_message(msg, show_actions=True, auto_hide=False)
                return

            if result.startswith("Locked Snippet: "):
                data = result[16:]
                orig_key, enc_val = data.split("|", 1)
                dialog = VaultPasswordDialog(orig_key, enc_val, self)
                if dialog.exec() == QDialog.DialogCode.Accepted and dialog.decrypted_text:
                    clipboard = QApplication.clipboard()
                    clipboard.setText(dialog.decrypted_text)
                    self.show_result_message(f"🔓 Unlocked & copied '{orig_key}' to clipboard!", show_actions=True, auto_hide=False)
                else:
                    self.show_result_message("<span style='color: #ef4444;'>🔒 Access Denied: Incorrect or cancelled password prompt.</span>", show_actions=True, auto_hide=False)
                return

            if result.startswith("Copied: "):
                val = result[8:]
                clipboard = QApplication.clipboard()
                clipboard.setText(val)
                self.show_result_message(f"Copied '{val}' to clipboard!", show_actions=True, auto_hide=False)
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
                self.show_result_message(msg, show_actions=True, auto_hide=False)
                return

            if result.startswith("Copied Path: "):
                data = result[13:]
                filepath, key = data.split("|", 1)
                clipboard = QApplication.clipboard()
                clipboard.setText(filepath)
                self.show_result_message(f"Copied path '{filepath}' to clipboard!", show_actions=True, auto_hide=False)
                return

            if result.startswith("Opened File: "):
                data = result[13:]
                filepath, key = data.split("|", 1)
                try:
                    os.startfile(filepath)
                    msg = f"Opened file '{key}' successfully!"
                except Exception as e:
                    msg = f"<span style='color: #ff5252;'>Error opening file: {e}</span>"
                self.show_result_message(msg, show_actions=True, auto_hide=False)
                return
                
            if result.startswith("Error:"):
                msg = f"<span style='color: #ff5252;'>{result}</span>"
            else:
                clean_copy = result.split('(')[0].strip() if '(' in result else result.strip()
                try:
                    clipboard = QApplication.clipboard()
                    if clipboard:
                        clipboard.setText(clean_copy)
                    self.last_math_result = clean_copy
                except Exception:
                    pass
                msg = f"<b>{result}</b> <span style='color: #4ade80;'>[Copied to clipboard]</span>"
            self.show_result_message(msg, show_actions=True, auto_hide=False)
            return
        
        intent, confidence = self.brain.predict(user_text)
        self.last_category = f"ML Intent: {intent}"
        logger.info(f"Brain predicted intent '{intent}' with confidence {confidence:.2f} for query '{user_text}'")
        
        if confidence < 0.35:
            logger.warning(f"Rejected low-confidence match: '{intent}' (confidence: {confidence:.2f} < 0.35)")
            self.show_result_message(
                f"<span style='color: #fbbf24;'>⚠️ Low confidence ({confidence*100:.0f}%):</span> Did you mean <b>{intent.replace('_', ' ').title()}</b>? Please be more specific.",
                show_actions=False,
                auto_hide=False
            )
            return

        if intent == "QUIT_PROGRAM":
            logger.info("Shutting down ShellSense Engine...")
            try:
                import keyboard
                keyboard.unhook_all()
            except:
                pass
            QApplication.quit()
            return

        # Hardened confirmation check for destructive intents
        if CommandExecutor.is_destructive(intent):
            action_desc = CommandExecutor.get_destructive_description(intent, user_text)
            confirm_dialog = DestructiveConfirmDialog(intent, action_desc, self)
            if confirm_dialog.exec() != QDialog.DialogCode.Accepted:
                self.show_result_message(
                    f"<span style='color: #94a3b8;'>Action cancelled:</span> {intent.replace('_', ' ').title()}",
                    show_actions=False,
                    auto_hide=True
                )
                return

        # Use the hardened executor service
        success = CommandExecutor.execute(intent, user_text)
        if not success:
            self.show_result_message("<span style='color: #ff5252;'>Error:</span> Command failed to execute", show_actions=True, auto_hide=False)
            return
        
        self.search_bar.blockSignals(True)
        self.search_bar.clear()
        self.search_bar.blockSignals(False)
        self.show_result_message(f"Command executed successfully: {intent}", show_actions=True, auto_hide=False)
    
    def toggle_visibility(self, trigger_source="Hotkey"):
        logger.info(f"{trigger_source} triggered. Toggling visibility.")
        if self.isVisible():
            if hasattr(self, 'timer_widget'):
                self.timer_widget.setVisible(False)
            if hasattr(self, 'alarm_widget'):
                self.alarm_widget.setVisible(False)
            if hasattr(self, 'conversion_widget'):
                self.conversion_widget.setVisible(False)
            if hasattr(self, 'translation_widget'):
                self.translation_widget.setVisible(False)
            if hasattr(self, 'alert_widget'):
                self.alert_widget.setVisible(False)
            if hasattr(self, 'feedback_panel'):
                self.feedback_panel.setVisible(False)
            self.hide()
            self.placeholder_timer.stop()
            logger.info("Window hidden.")
        else:
            self.search_bar.blockSignals(True)
            self.search_bar.clear()
            self.search_bar.blockSignals(False)
            self.last_math_result = None
            self.result_label.setVisible(False)
            if hasattr(self, 'result_actions_widget'):
                self.result_actions_widget.setVisible(False)
            if hasattr(self, 'timer_widget'):
                self.timer_widget.setVisible(False)
            if hasattr(self, 'alarm_widget'):
                self.alarm_widget.setVisible(False)
            if hasattr(self, 'conversion_widget'):
                self.conversion_widget.setVisible(False)
            if hasattr(self, 'translation_widget'):
                self.translation_widget.setVisible(False)
            if hasattr(self, 'alert_widget'):
                self.alert_widget.setVisible(False)
            if hasattr(self, 'feedback_panel'):
                self.feedback_panel.setVisible(False)
            self.setFixedSize(600, 88)
            self.show()
            self.raise_()
            self.activateWindow()
            
            # Force active focus on Windows, bypassing background focus-stealing rules
            try:
                import ctypes
                hwnd_foreground = ctypes.windll.user32.GetForegroundWindow()
                hwnd_our = int(self.winId())
                if hwnd_foreground != hwnd_our:
                    thread_foreground = ctypes.windll.user32.GetWindowThreadProcessId(hwnd_foreground, None)
                    thread_our = ctypes.windll.kernel32.GetCurrentThreadId()
                    ctypes.windll.user32.AttachThreadInput(thread_foreground, thread_our, True)
                    ctypes.windll.user32.SetForegroundWindow(hwnd_our)
                    ctypes.windll.user32.SetFocus(hwnd_our)
                    ctypes.windll.user32.AttachThreadInput(thread_foreground, thread_our, False)
            except Exception as e:
                logger.error(f"Error forcing window focus: {e}")

            # Setup placeholder rotation
            try:
                from shellsense.core.config_manager import ConfigManager
                snippets = ConfigManager.get_snippets() or {}
                shortcuts = ConfigManager.get_shortcuts() or {}
                self.suggestion_pool = [k for k in snippets.keys()] + [k for k in shortcuts.keys()]
                self.suggestion_pool.extend(["10 USD to EUR", "5 miles to km", "timer 10m", "last download", "clean temp files", "lock screen"])
                import random
                random.shuffle(self.suggestion_pool)
                self.suggestion_index = 0
                
                if not hasattr(self, 'typing_timer'):
                    self.typing_timer = QTimer(self)
                    self.typing_timer.timeout.connect(self.type_next_char)
                    self.current_suggestion = ""
                    self.typing_index = 0
                    
                self.update_placeholder_suggestion()
                # The placeholder timer triggers the NEXT suggestion cycle.
                # Let's set it to 3000ms (1.5s typing + 1.5s reading)
                self.placeholder_timer.start(3000)
            except Exception as e:
                logger.error(f"Error setting up placeholder: {e}")

            QTimer.singleShot(10, self.search_bar.setFocus)
            logger.info("Window shown and focused.")

    def update_placeholder_suggestion(self):
        if hasattr(self, 'suggestion_pool') and self.suggestion_pool:
            if hasattr(self, 'typing_timer'):
                self.typing_timer.stop()
            self.current_suggestion = self.suggestion_pool[self.suggestion_index]
            self.suggestion_index = (self.suggestion_index + 1) % len(self.suggestion_pool)
            self.typing_index = 0
            self.search_bar.setPlaceholderText("")
            # 40ms per character makes it very smooth
            self.typing_timer.start(40)

    def type_next_char(self):
        if self.typing_index < len(self.current_suggestion):
            self.typing_index += 1
            self.search_bar.setPlaceholderText(self.current_suggestion[:self.typing_index])
        else:
            self.typing_timer.stop()

    def eventFilter(self, watched, event):
        if watched == self.search_bar and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Tab:
                if self.search_bar.text() == "":
                    placeholder = self.search_bar.placeholderText()
                    if placeholder and placeholder != "Search ShellSense Features...":
                        self.search_bar.setText(placeholder)
                    return True

        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                logger.info("Global Escape key intercepted. Hiding search bar window.")
                self.hide_and_clear()
                return True
                
        return super().eventFilter(watched, event)

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
        
        # Check registration
        from shellsense.core.config import USER_DIR
        user_info_path = os.path.join(USER_DIR, "user_info.json")
        if not os.path.exists(user_info_path):
            logger.info("First startup: Showing registration dialog.")
            dialog = RegistrationDialog()
            if dialog.exec() != QDialog.DialogCode.Accepted:
                logger.info("Registration cancelled. Exiting.")
                sys.exit(0)
                
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