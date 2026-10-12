from enum import Enum, auto
from PyQt6.QtWidgets import (
    QScrollArea, QLabel, QFrame, QLineEdit, QHBoxLayout, 
    QListWidget, QListWidgetItem, QSizePolicy, QFileDialog, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QPoint, QEvent, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QMouseEvent, QKeyEvent, QColor
from shellsense.core.logger import logger


class CommandState(Enum):
    """Explicit progressive collection cycle states for TokenizedBar."""
    IDLE = auto()
    PASSWORD_KEY = auto()
    PASSWORD_VAL = auto()
    FILE_NAME = auto()
    COMMAND_PROMPT = auto()


SLASH_ACTIONS = [
    {
        "cmd": "/vault",
        "aliases": ["/password", "/pass", "/secret"],
        "label": "🔒 /vault — Store and protect secret in Vault",
        "action": "password",
        "token": "Vault",
        "target_state": CommandState.PASSWORD_KEY,
        "placeholder": "Enter secret key name (e.g. github_token)..."
    },
    {
        "cmd": "/file",
        "aliases": ["/find", "/shortcut"],
        "label": "📁 /file — Search or inspect file shortcuts",
        "action": "file",
        "token": "File",
        "target_state": CommandState.FILE_NAME,
        "placeholder": "Enter file name or search query (e.g. notes.txt)..."
    },
    {
        "cmd": "/command",
        "aliases": ["/cmd", "/exec", "/run"],
        "label": "⚡ /command — Execute a shell or system command",
        "action": "command",
        "token": "Command",
        "target_state": CommandState.COMMAND_PROMPT,
        "placeholder": "Enter shell command to execute (e.g. ping google.com)..."
    }
]


class PromptInferenceWorker(QThread):
    """
    Dedicated background QThread for local model inference.
    Executes intent classification or shell syntax generation without freezing the PyQt main thread.
    """
    started_inference = pyqtSignal(str)
    intent_candidates_ready = pyqtSignal(str, list)
    command_syntax_ready = pyqtSignal(str, str)
    finished_inference = pyqtSignal()

    def __init__(self, query: str, state: CommandState, parent=None):
        super().__init__(parent)
        self.query = query
        self.state = state

    def run(self):
        self.started_inference.emit(self.query)
        try:
            from shellsense.services.local_model_service import LocalModelService
            svc = LocalModelService.get_instance()

            if self.state == CommandState.IDLE:
                candidates = svc.get_ranked_intent_candidates(self.query)
                self.intent_candidates_ready.emit(self.query, candidates)

            elif self.state == CommandState.COMMAND_PROMPT:
                raw_syntax = svc.generate_shell_syntax(self.query)
                self.command_syntax_ready.emit(self.query, raw_syntax)

        except Exception as e:
            logger.error(f"Inference worker error: {e}")
        finally:
            self.finished_inference.emit()


class ScrollableLabel(QScrollArea):
    """Scrollable label with custom styled scrollbars."""
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


class TokenBadge(QLabel):
    """
    Dynamic visual badge representing command modes, filters, or entity tokens.
    Renders with high-precision padding and zero layout jitter.
    """
    clicked = pyqtSignal(str)

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.token_text = text
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QLabel {
                background-color: rgba(59, 130, 246, 0.22);
                color: #93c5fd;
                border: 1px solid rgba(59, 130, 246, 0.45);
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 12px;
                font-weight: 600;
                font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
            }
            QLabel:hover {
                background-color: rgba(59, 130, 246, 0.35);
                border: 1px solid rgba(59, 130, 246, 0.75);
                color: #ffffff;
            }
        """)

    def mousePressEvent(self, event: QMouseEvent):
        super().mousePressEvent(event)
        self.clicked.emit(self.token_text)


class TokenizedLineEdit(QLineEdit):
    """
    Frameless, transparent line edit that routes arrow keys to SuggestionsDropdown,
    and captures Backspace on empty string and Escape to trigger state transitions.
    """
    def __init__(self, bar: 'TokenizedBar', parent=None):
        super().__init__(parent)
        self.bar = bar
        self.setFrame(False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #f8fafc;
                font-size: 14px;
                font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
                padding: 4px 2px;
                selection-background-color: #3b82f6;
            }
            QLineEdit:focus {
                outline: none;
            }
        """)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        dropdown = self.bar._dropdown

        # 1. Forward Up/Down arrows and Enter navigation to SuggestionsDropdown if open
        if dropdown is not None and dropdown.isVisible():
            if key == Qt.Key.Key_Down:
                dropdown.navigate_down()
                return
            elif key == Qt.Key.Key_Up:
                dropdown.navigate_up()
                return
            elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if dropdown.current_text():
                    dropdown.select_current()
                    return

        # 2. Handle Enter / Return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.bar.handle_enter_pressed()
            return

        # 3. Map Backspace on an empty string to remove most recent TokenBadge & step state backward
        if key == Qt.Key.Key_Backspace and not self.text():
            self.bar.handle_backspace_on_empty()
            return

        # 4. Map Escape to clear tokens and return the state to IDLE
        if key == Qt.Key.Key_Escape:
            self.bar.handle_escape_pressed()
            return

        super().keyPressEvent(event)


class TokenizedBar(QFrame):
    """
    Composite input frame hosting dynamic TokenBadge tags on the left
    and an expanding frameless QLineEdit on the right.
    Maintains progressive collection cycles via CommandState in-memory.
    """
    state_changed = pyqtSignal(object)       # Emits CommandState
    command_collected = pyqtSignal(dict)      # Emits completed in-memory payload
    entry_saved = pyqtSignal(str, str, str)   # (category, key, value) - signals persistence
    intent_selected = pyqtSignal(dict)        # Emits selected natural language intent candidate
    token_added = pyqtSignal(str)
    token_removed = pyqtSignal(str)
    text_changed = pyqtSignal(str)
    return_pressed = pyqtSignal()
    backspace_on_empty = pyqtSignal()

    DEFAULT_PLACEHOLDER = "Search or type a natural language command (or / for modes)..."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = CommandState.IDLE
        self._tokens = []
        self._dropdown = None
        self._collected_data = {}
        self.file_dialog_func = QFileDialog.getOpenFileName
        self.entry_saved.connect(self._persist_to_sqlite)

        # Dedicated QThread worker and debounce timer for model inference
        self._inference_worker = None
        self._inference_timer = QTimer(self)
        self._inference_timer.setSingleShot(True)
        self._inference_timer.setInterval(80)
        self._inference_timer.timeout.connect(self._trigger_background_inference)

        self.initUI()

    def _persist_to_sqlite(self, category: str, key: str, value: str):
        """Auto-persists completed cycles directly to SQLite database."""
        try:
            from shellsense.core.db import DatabaseManager
            db = DatabaseManager.get_instance()
            db.save_entry(category, key, value)
        except Exception:
            pass

    def initUI(self):
        self.setObjectName("TokenizedBar")
        
        # Zero-margin horizontal layout for tight alignment without jitter
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(8, 4, 8, 4)
        self.main_layout.setSpacing(6)

        # Dynamic tokens container on the left
        self.tokens_layout = QHBoxLayout()
        self.tokens_layout.setContentsMargins(0, 0, 0, 0)
        self.tokens_layout.setSpacing(6)
        self.main_layout.addLayout(self.tokens_layout)

        # Frameless, transparent text field stretching across the remaining space
        self.input_field = TokenizedLineEdit(self, self)
        self.input_field.setPlaceholderText(self.DEFAULT_PLACEHOLDER)
        self.main_layout.addWidget(self.input_field)

        # Connect text change to slash-trigger detection
        self.input_field.textChanged.connect(self._on_text_changed)

        # Glassmorphism container styling
        self.setStyleSheet("""
            QFrame#TokenizedBar {
                background-color: rgba(15, 23, 42, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 10px;
                min-height: 38px;
            }
            QFrame#TokenizedBar:focus-within {
                border: 1px solid rgba(59, 130, 246, 0.8);
                background-color: rgba(15, 23, 42, 0.95);
            }
        """)

    def set_dropdown(self, dropdown):
        """Binds a SuggestionsDropdown to handle key navigation and suggestion selection."""
        self._dropdown = dropdown
        if self._dropdown is not None:
            self._dropdown.suggestion_selected.connect(self.handle_suggestion_selected)
            self._dropdown.candidate_selected.connect(self.handle_candidate_selected)

    def mousePressEvent(self, event: QMouseEvent):
        """Ensures clicking any margin or empty space within the frame routes focus to the input."""
        super().mousePressEvent(event)
        self.input_field.setFocus()

    # --- Slash Trigger & Model Inference Pipeline ---

    def _on_text_changed(self, text: str):
        self.text_changed.emit(text)
        trimmed = text.strip()

        # 1. Slash-trigger detection only active in IDLE state with leading '/'
        if self.state == CommandState.IDLE and trimmed.startswith("/"):
            query = trimmed.lower()
            matches = []
            for item in SLASH_ACTIONS:
                all_triggers = [item["cmd"]] + item["aliases"]
                if any(t.startswith(query) or query.startswith(t) for t in all_triggers) or query in item["label"].lower():
                    matches.append(item["label"])

            if matches and self._dropdown is not None:
                self._dropdown._current_candidates = []
                self._dropdown.show_suggestions(matches)
                if self._dropdown.count() > 0 and self._dropdown.currentRow() < 0:
                    self._dropdown.setCurrentRow(0)
            elif self._dropdown is not None:
                self._dropdown.hide()
            return

        # 2. Non-prefixed natural language in IDLE -> Trigger QThread Intent Classifier
        if self.state == CommandState.IDLE:
            if len(trimmed) >= 2 and not self._tokens:
                self._inference_timer.start(80)
            else:
                if self._dropdown is not None:
                    self._dropdown.hide()
            return

        # 3. Free-form command prompt in COMMAND_PROMPT -> Trigger QThread Syntax Generator
        if self.state == CommandState.COMMAND_PROMPT:
            if len(trimmed) >= 3 and not ("=" in trimmed or ":" in trimmed):
                self._inference_timer.start(100)
            else:
                if self._dropdown is not None:
                    self._dropdown.hide()
            return

    def _trigger_background_inference(self):
        text = self.input_field.text().strip()
        if not text:
            return

        # Show non-blocking UI loader in SuggestionsDropdown immediately
        if self._dropdown is not None:
            if self.state == CommandState.IDLE:
                self._dropdown.show_loader("⚡ Analyzing natural language intent...")
            elif self.state == CommandState.COMMAND_PROMPT:
                self._dropdown.show_loader("⚡ Generating verified shell syntax...")

        if self._inference_worker and self._inference_worker.isRunning():
            self._inference_worker.terminate()
            self._inference_worker.wait(50)

        self._inference_worker = PromptInferenceWorker(text, self.state, self)
        self._inference_worker.intent_candidates_ready.connect(self._on_intent_candidates_ready)
        self._inference_worker.command_syntax_ready.connect(self._on_command_syntax_ready)
        self._inference_worker.start()

    def _on_intent_candidates_ready(self, query: str, candidates: list):
        current_text = self.input_field.text().strip()
        if current_text == query and self._dropdown is not None:
            if candidates:
                self._dropdown.show_intent_candidates(candidates)
            else:
                self._dropdown.hide()

    def _on_command_syntax_ready(self, query: str, raw_syntax: str):
        current_text = self.input_field.text().strip()
        if current_text == query and self._dropdown is not None:
            if raw_syntax:
                candidates = [{
                    "label": f"⚡ Shell: {raw_syntax}",
                    "command": raw_syntax,
                    "title": "Generated Shell Command",
                    "type": "shell_syntax"
                }]
                self._dropdown.show_intent_candidates(candidates)
            else:
                self._dropdown.hide()

    def handle_candidate_selected(self, candidate: dict):
        """Processes accepted smart suggestion (intent candidate or shell syntax)."""
        cand_type = candidate.get("type")
        if cand_type == "shell_syntax":
            # Populate line edit with verified shell command
            cmd = candidate.get("command", "")
            self.input_field.setText(cmd)
            self.input_field.setCursorPosition(len(cmd))
            if self._dropdown is not None:
                self._dropdown.hide()
        else:
            # User accepted an intent candidate in IDLE
            self.clear_tokens()
            icon = candidate.get("icon", "⚡")
            title = candidate.get("title", candidate.get("intent", "Action"))
            cmd = candidate.get("command", "")
            self.add_token(f"{icon} {title}")
            self.input_field.setText(cmd)
            self.input_field.setCursorPosition(len(cmd))
            self.intent_selected.emit(candidate)
            if self._dropdown is not None:
                self._dropdown.hide()

    def handle_suggestion_selected(self, label: str):
        """Pushes the corresponding token badge and steps state forward upon suggestion selection."""
        selected_action = None
        for item in SLASH_ACTIONS:
            if item["label"] == label or item["cmd"] in label.lower() or any(alias in label.lower() for alias in item["aliases"]):
                selected_action = item
                break

        if not selected_action:
            for item in SLASH_ACTIONS:
                if item["cmd"] in self.input_field.text().lower():
                    selected_action = item
                    break

        if selected_action:
            self.transition_to(selected_action["target_state"], selected_action)

    # --- State Machine Transitions ---

    def transition_to(self, new_state: CommandState, action_meta: dict = None):
        """Manages state transitions, token badge creation, and input field configuration."""
        self.state = new_state
        if self._dropdown is not None:
            self._dropdown.hide()

        if new_state == CommandState.IDLE:
            self.clear_tokens()
            self.input_field.clear()
            self.input_field.setEchoMode(QLineEdit.EchoMode.Normal)
            self.input_field.setPlaceholderText(self.DEFAULT_PLACEHOLDER)
            self._collected_data = {}

        elif new_state == CommandState.PASSWORD_KEY:
            self.clear_tokens()
            token_name = action_meta.get("token", "Vault") if action_meta else "Vault"
            self.add_token(token_name)
            self.input_field.clear()
            self.input_field.setEchoMode(QLineEdit.EchoMode.Normal)
            placeholder = action_meta.get("placeholder", "Enter secret key name...") if action_meta else "Enter secret key name..."
            self.input_field.setPlaceholderText(placeholder)
            self._collected_data = {"type": "password"}

        elif new_state == CommandState.PASSWORD_VAL:
            key_name = self._collected_data.get("key", "")
            self.add_token(f"Key: {key_name}")
            self.input_field.clear()
            self.input_field.setEchoMode(QLineEdit.EchoMode.Password)
            self.input_field.setPlaceholderText("Enter secret password/value...")

        elif new_state == CommandState.FILE_NAME:
            self.clear_tokens()
            token_name = action_meta.get("token", "File") if action_meta else "File"
            self.add_token(token_name)
            self.input_field.clear()
            self.input_field.setEchoMode(QLineEdit.EchoMode.Normal)
            placeholder = action_meta.get("placeholder", "Enter file name or query...") if action_meta else "Enter file name or query..."
            self.input_field.setPlaceholderText(placeholder)
            self._collected_data = {"type": "file"}

        elif new_state == CommandState.COMMAND_PROMPT:
            self.clear_tokens()
            token_name = action_meta.get("token", "Command") if action_meta else "Command"
            self.add_token(token_name)
            self.input_field.clear()
            self.input_field.setEchoMode(QLineEdit.EchoMode.Normal)
            placeholder = action_meta.get("placeholder", "Enter command to execute...") if action_meta else "Enter command to execute..."
            self.input_field.setPlaceholderText(placeholder)
            self._collected_data = {"type": "command"}

        self.state_changed.emit(self.state)
        self.input_field.setFocus()

    # --- Keyboard Action Handlers ---

    def handle_enter_pressed(self):
        """Advances progressive state collection cycles on Enter."""
        text = self.input_field.text().strip()

        if self.state == CommandState.IDLE:
            # Check if user typed a slash command string directly
            if text.startswith("/"):
                query = text.lower()
                for item in SLASH_ACTIONS:
                    all_triggers = [item["cmd"]] + item["aliases"]
                    if query in all_triggers or any(query.startswith(a) for a in all_triggers):
                        self.transition_to(item["target_state"], item)
                        return
            if self._tokens and text:
                token_title = self._tokens[0].token_text
                self.entry_saved.emit("command", token_title, text)
                self.command_collected.emit({"type": "command", "command": text, "title": token_title})
                self.transition_to(CommandState.IDLE)
                return
            self.return_pressed.emit()

        elif self.state == CommandState.PASSWORD_KEY:
            if not text:
                return
            self._collected_data["key"] = text
            self.transition_to(CommandState.PASSWORD_VAL)

        elif self.state == CommandState.PASSWORD_VAL:
            if not text:
                return
            self._collected_data["value"] = text
            key = self._collected_data.get("key", "")
            payload = dict(self._collected_data)
            self.entry_saved.emit("password", key, text)
            self.command_collected.emit(payload)
            self.transition_to(CommandState.IDLE)

        elif self.state == CommandState.FILE_NAME:
            if not text:
                return
            # Native OS file dialog hook
            file_path = None
            if self.file_dialog_func:
                res = self.file_dialog_func(
                    self.window(),
                    "Select Target File for Shortcut",
                    "",
                    "All Files (*.*)"
                )
                if isinstance(res, tuple):
                    file_path = res[0]
                else:
                    file_path = res

            if not file_path:
                # User cancelled dialog, stay in FILE_NAME state to allow retry/cancellation
                return

            self._collected_data["shortcut_name"] = text
            self._collected_data["file_name"] = text
            self._collected_data["file_path"] = file_path
            self._collected_data["key"] = text
            self._collected_data["value"] = file_path
            payload = dict(self._collected_data)
            self.entry_saved.emit("file", text, file_path)
            self.command_collected.emit(payload)
            self.transition_to(CommandState.IDLE)

        elif self.state == CommandState.COMMAND_PROMPT:
            if not text:
                return
            cmd_text = text
            if "=" in cmd_text:
                k, v = cmd_text.split("=", 1)
                cmd_name = k.strip()
                cmd_str = v.strip()
            elif ":" in cmd_text and not cmd_text.startswith("http") and not ":\\" in cmd_text:
                k, v = cmd_text.split(":", 1)
                cmd_name = k.strip()
                cmd_str = v.strip()
            else:
                cmd_name = cmd_text.strip()
                cmd_str = cmd_text.strip()

            self._collected_data["command_name"] = cmd_name
            self._collected_data["command"] = cmd_str
            self._collected_data["key"] = cmd_name
            self._collected_data["value"] = cmd_str
            payload = dict(self._collected_data)
            self.entry_saved.emit("command", cmd_name, cmd_str)
            self.command_collected.emit(payload)
            self.transition_to(CommandState.IDLE)

    def handle_backspace_on_empty(self):
        """
        Mapped to Backspace on empty input:
        Removes the most recent TokenBadge and steps the state backward.
        """
        self.backspace_on_empty.emit()

        if self.state == CommandState.PASSWORD_VAL:
            # Step backward: remove Key token, restore previous key text, return to PASSWORD_KEY
            self.remove_last_token()
            prev_key = self._collected_data.get("key", "")
            self.state = CommandState.PASSWORD_KEY
            self.input_field.setEchoMode(QLineEdit.EchoMode.Normal)
            self.input_field.setText(prev_key)
            self.input_field.setPlaceholderText("Enter secret key name (e.g. github_token)...")
            self.state_changed.emit(self.state)

        elif self.state == CommandState.PASSWORD_KEY:
            # Step backward to IDLE
            self.remove_last_token()
            self.state = CommandState.IDLE
            self.input_field.setPlaceholderText(self.DEFAULT_PLACEHOLDER)
            self._collected_data = {}
            self.state_changed.emit(self.state)

        elif self.state in (CommandState.FILE_NAME, CommandState.COMMAND_PROMPT):
            # Step backward to IDLE
            self.remove_last_token()
            self.state = CommandState.IDLE
            self.input_field.setPlaceholderText(self.DEFAULT_PLACEHOLDER)
            self._collected_data = {}
            self.state_changed.emit(self.state)

        elif self.state == CommandState.IDLE:
            if self._tokens:
                self.remove_last_token()

    def handle_escape_pressed(self):
        """
        Mapped to Escape:
        Clears tokens, hides suggestions, and returns state to IDLE.
        """
        if self._dropdown is not None and self._dropdown.isVisible():
            self._dropdown.hide()
        self.transition_to(CommandState.IDLE)

    # --- Token Management API ---

    def add_token(self, text: str) -> TokenBadge:
        """Appends a new TokenBadge tag on the left."""
        badge = TokenBadge(text, self)
        self._tokens.append(badge)
        self.tokens_layout.addWidget(badge)
        self.token_added.emit(text)
        return badge

    def remove_token(self, badge: TokenBadge) -> bool:
        """Removes a specific TokenBadge widget."""
        if badge in self._tokens:
            self._tokens.remove(badge)
            self.tokens_layout.removeWidget(badge)
            text = badge.token_text
            badge.deleteLater()
            self.token_removed.emit(text)
            return True
        return False

    def remove_last_token(self) -> bool:
        """Removes the rightmost token."""
        if self._tokens:
            return self.remove_token(self._tokens[-1])
        return False

    def clear_tokens(self):
        """Clears all tokens."""
        for badge in list(self._tokens):
            self.remove_token(badge)

    def tokens(self) -> list[str]:
        """Returns the list of current token strings."""
        return [b.token_text for b in self._tokens]

    # --- Input Field Passthroughs ---

    def text(self) -> str:
        return self.input_field.text()

    def setText(self, text: str):
        self.input_field.setText(text)

    def clear(self):
        self.input_field.clear()
        self.clear_tokens()

    def setFocus(self):
        self.input_field.setFocus()


class SuggestionsDropdown(QListWidget):
    """
    Floating, frameless popup anchored to the bottom edge of TokenizedBar using mapToGlobal.
    Uses Qt.WindowType.ToolTip / WA_ShowWithoutActivating to prevent stealing keyboard focus.
    """
    suggestion_selected = pyqtSignal(str)
    candidate_selected = pyqtSignal(dict)

    def __bool__(self):
        # Override PyQt default len(self) > 0 evaluation so an empty dropdown is never treated as falsy
        return True

    def __init__(self, target_bar: TokenizedBar, parent=None):
        super().__init__(parent)
        self.target_bar = target_bar
        self._current_candidates = []
        if self.target_bar is not None:
            self.target_bar.set_dropdown(self)

        # Configure as a floating, frameless tool window
        self.setWindowFlags(
            Qt.WindowType.ToolTip | 
            Qt.WindowType.FramelessWindowHint
        )
        # Ensure showing does not deactivate or steal focus from TokenizedBar
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.setStyleSheet("""
            QListWidget {
                background-color: rgba(15, 23, 42, 0.96);
                border: 1px solid rgba(59, 130, 246, 0.45);
                border-radius: 8px;
                padding: 4px;
                color: #e2e8f0;
                font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
                font-size: 13px;
                outline: none;
            }
            QListWidget::item {
                padding: 7px 12px;
                border-radius: 6px;
                margin: 1px 0px;
                color: #cbd5e1;
            }
            QListWidget::item:hover, QListWidget::item:selected {
                background-color: rgba(59, 130, 246, 0.28);
                color: #ffffff;
                font-weight: 500;
            }
        """)

        self.itemClicked.connect(self._on_item_clicked)

    def reposition(self):
        """Aligns dropdown directly underneath the TokenizedBar via mapToGlobal."""
        if not self.target_bar or not self.target_bar.isVisible():
            return
        
        # Calculate bottom-left edge coordinates in global screen space
        bottom_left = self.target_bar.mapToGlobal(QPoint(0, self.target_bar.height() + 3))
        self.move(bottom_left)
        self.setFixedWidth(self.target_bar.width())

    def show_loader(self, message: str = "⚡ Analyzing natural language intent..."):
        """Displays a non-blocking UI loader directly inside SuggestionsDropdown."""
        self.clear()
        self._current_candidates = []
        loader_item = QListWidgetItem(message)
        loader_item.setFlags(Qt.ItemFlag.NoItemFlags)
        loader_item.setForeground(QColor("#93c5fd"))
        self.addItem(loader_item)
        self.reposition()
        self.setFixedHeight(48)
        self.show()
        if self.target_bar:
            self.target_bar.input_field.setFocus()

    def show_suggestions(self, items: list[str]):
        """Populates suggestions and displays floating dropdown without stealing focus."""
        if not items:
            self.hide()
            return

        self.clear()
        self._current_candidates = []
        for item in items:
            self.addItem(item)

        self.reposition()

        # Dynamic height calculation capped at 6 rows
        item_count = min(len(items), 6)
        row_height = 34
        self.setFixedHeight(item_count * row_height + 10)

        self.show()
        # Keep keyboard focus firmly on the target text input
        if self.target_bar:
            self.target_bar.input_field.setFocus()

    def show_intent_candidates(self, candidates: list[dict]):
        """Displays ranked intent candidates or generated shell command."""
        if not candidates:
            self.hide()
            return

        self.clear()
        self._current_candidates = list(candidates)
        for c in candidates:
            label = c.get("label") or c.get("title") or str(c)
            self.addItem(label)

        self.reposition()

        item_count = min(len(candidates), 6)
        row_height = 36
        self.setFixedHeight(item_count * row_height + 10)
        self.setCurrentRow(0)

        self.show()
        if self.target_bar:
            self.target_bar.input_field.setFocus()

    def navigate_down(self):
        """Moves selected row down while maintaining focus on input field."""
        count = self.count()
        if count == 0:
            return
        current = self.currentRow()
        next_row = (current + 1) % count
        self.setCurrentRow(next_row)

    def navigate_up(self):
        """Moves selected row up while maintaining focus on input field."""
        count = self.count()
        if count == 0:
            return
        current = self.currentRow()
        prev_row = (current - 1 + count) % count
        self.setCurrentRow(prev_row)

    def current_text(self) -> str:
        item = self.currentItem()
        return item.text() if item else ""

    def select_current(self):
        item = self.currentItem()
        if not item or not (item.flags() & Qt.ItemFlag.ItemIsSelectable):
            return

        idx = self.currentRow()
        if idx >= 0:
            if self._current_candidates and idx < len(self._current_candidates):
                candidate = self._current_candidates[idx]
                self.candidate_selected.emit(candidate)
                self.hide()
                return

        text = item.text()
        if text:
            self.suggestion_selected.emit(text)
            self.hide()
            if self.target_bar:
                self.target_bar.input_field.setFocus()

    def _on_item_clicked(self, item):
        if not item or not (item.flags() & Qt.ItemFlag.ItemIsSelectable):
            return

        idx = self.row(item)
        if idx >= 0:
            if self._current_candidates and idx < len(self._current_candidates):
                candidate = self._current_candidates[idx]
                self.candidate_selected.emit(candidate)
                self.hide()
                return

        text = item.text()
        if text:
            self.suggestion_selected.emit(text)
            self.hide()
            if self.target_bar:
                self.target_bar.input_field.setFocus()


class ViewerTabWidget(QTabWidget):
    """
    Modern glassmorphic tab view widget hosting SQLite table views for:
    1. Vault Passwords (vault_passwords)
    2. File Shortcuts (file_shortcuts)
    3. Terminal Commands (terminal_commands)
    Listens to entry_saved / entry_persisted signals and auto-refreshes tables.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        self.connect_db()
        self.refresh_all()

    def initUI(self):
        self.setObjectName("ViewerTabWidget")
        self.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                background-color: rgba(15, 23, 42, 0.95);
            }
            QTabBar::tab {
                background: rgba(30, 41, 59, 0.8);
                color: #94a3b8;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
                font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
                font-size: 12px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: rgba(59, 130, 246, 0.25);
                color: #60a5fa;
                border: 1px solid rgba(59, 130, 246, 0.5);
                border-bottom: none;
            }
            QTabBar::tab:hover:!selected {
                background: rgba(51, 65, 85, 0.8);
                color: #f1f5f9;
            }
            QTableWidget {
                background-color: transparent;
                gridline-color: rgba(255, 255, 255, 0.08);
                color: #e2e8f0;
                font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
                font-size: 12px;
                border: none;
                selection-background-color: rgba(59, 130, 246, 0.3);
                selection-color: #ffffff;
            }
            QHeaderView::section {
                background-color: rgba(30, 41, 59, 0.9);
                color: #93c5fd;
                padding: 6px 10px;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.15);
                font-weight: 600;
                font-size: 11px;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 50);
                border-radius: 3px;
                min-height: 20px;
            }
        """)

        # Tab 1: Vault Passwords
        self.vault_table = self._create_table(["ID", "Key Name", "Encrypted Secret", "Last Updated"])
        self.addTab(self.vault_table, "🔒 Vault Passwords")

        # Tab 2: File Shortcuts
        self.shortcuts_table = self._create_table(["ID", "Shortcut Name", "File Path", "Last Updated"])
        self.addTab(self.shortcuts_table, "📁 File Shortcuts")

        # Tab 3: Terminal Commands
        self.commands_table = self._create_table(["ID", "Command Name", "Command / Script", "Last Updated"])
        self.addTab(self.commands_table, "⚡ Terminal Commands")

    def _create_table(self, headers: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        return table

    def connect_db(self):
        try:
            from shellsense.core.db import DatabaseManager
            db = DatabaseManager.get_instance()
            db.entry_persisted.connect(self.on_entry_saved)
        except Exception:
            pass

    def wire_to_bar(self, bar: TokenizedBar):
        """Directly wires TokenizedBar entry_saved signal to this tab view."""
        if bar:
            bar.entry_saved.connect(self.on_entry_saved)

    def on_entry_saved(self, category: str, key: str, value: str):
        """Slot triggered whenever an entry is saved to SQLite or emitted by TokenizedBar."""
        self.refresh_tab(category)

    def refresh_tab(self, category: str = None):
        cat = (category or "").lower().strip()
        if cat in ("password", "vault"):
            self.refresh_vault()
        elif cat in ("file", "shortcut"):
            self.refresh_shortcuts()
        elif cat in ("command", "cmd", "terminal"):
            self.refresh_commands()
        else:
            self.refresh_all()

    def refresh_all(self):
        self.refresh_vault()
        self.refresh_shortcuts()
        self.refresh_commands()

    def refresh_vault(self):
        try:
            from shellsense.core.db import DatabaseManager
            db = DatabaseManager.get_instance()
            rows = db.get_vault_passwords()
            self._populate_table(self.vault_table, rows, ["id", "key_name", "encrypted_value", "updated_at"])
        except Exception:
            pass

    def refresh_shortcuts(self):
        try:
            from shellsense.core.db import DatabaseManager
            db = DatabaseManager.get_instance()
            rows = db.get_file_shortcuts()
            self._populate_table(self.shortcuts_table, rows, ["id", "shortcut_name", "file_path", "updated_at"])
        except Exception:
            pass

    def refresh_commands(self):
        try:
            from shellsense.core.db import DatabaseManager
            db = DatabaseManager.get_instance()
            rows = db.get_terminal_commands()
            self._populate_table(self.commands_table, rows, ["id", "command_name", "command_string", "updated_at"])
        except Exception:
            pass

    def _populate_table(self, table: QTableWidget, data: list[dict], keys: list[str]):
        table.setRowCount(0)
        for row_idx, item in enumerate(data):
            table.insertRow(row_idx)
            for col_idx, key in enumerate(keys):
                val = str(item.get(key, ""))
                cell = QTableWidgetItem(val)
                table.setItem(row_idx, col_idx, cell)

