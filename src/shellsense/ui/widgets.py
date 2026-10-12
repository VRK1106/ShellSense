from PyQt6.QtWidgets import (
    QScrollArea, QLabel, QFrame, QLineEdit, QHBoxLayout, 
    QListWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, QPoint, QEvent, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QKeyEvent

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
    Renders with high-precision padding and no layout jitter.
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


class TokenizedBar(QFrame):
    """
    Composite input frame hosting dynamic TokenBadge tags on the left
    and an expanding frameless QLineEdit on the right.
    Margin clicks automatically route focus to the input field.
    """
    token_added = pyqtSignal(str)
    token_removed = pyqtSignal(str)
    text_changed = pyqtSignal(str)
    return_pressed = pyqtSignal()
    backspace_on_empty = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tokens = []
        self._dropdown = None
        self.initUI()

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
        self.input_field = QLineEdit(self)
        self.input_field.setFrame(False)
        self.input_field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.input_field.setPlaceholderText("Search or type a natural language command...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #f8fafc;
                font-size: 14px;
                font-family: 'Segoe UI', 'Inter', sans-serif;
                padding: 4px 2px;
                selection-background-color: #3b82f6;
            }
            QLineEdit:focus {
                outline: none;
            }
        """)
        self.main_layout.addWidget(self.input_field)

        # Forward core QLineEdit signals
        self.input_field.textChanged.connect(self.text_changed)
        self.input_field.returnPressed.connect(self.return_pressed)

        # Event filter to intercept Backspace on empty input and arrow navigation
        self.input_field.installEventFilter(self)

        # Default glassmorphism container styling
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
        """Binds a SuggestionsDropdown to handle key navigation."""
        self._dropdown = dropdown

    def mousePressEvent(self, event: QMouseEvent):
        """Ensures clicking any margin or empty space within the frame routes focus to the input."""
        super().mousePressEvent(event)
        self.input_field.setFocus()

    def eventFilter(self, obj, event):
        """Intercepts keyboard events on the text field for dropdown navigation and backspace removal."""
        if obj == self.input_field and event.type() == QEvent.Type.KeyPress:
            key_event: QKeyEvent = event
            
            # If user hits Backspace while text field is empty, pop the last token
            if key_event.key() == Qt.Key.Key_Backspace and not self.input_field.text():
                if self._tokens:
                    self.remove_last_token()
                    self.backspace_on_empty.emit()
                    return True

            # If dropdown is bound and active, route Up/Down/Enter/Escape navigation
            if self._dropdown and self._dropdown.isVisible():
                if key_event.key() == Qt.Key.Key_Down:
                    self._dropdown.navigate_down()
                    return True
                elif key_event.key() == Qt.Key.Key_Up:
                    self._dropdown.navigate_up()
                    return True
                elif key_event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    if self._dropdown.current_text():
                        self._dropdown.select_current()
                        return True
                elif key_event.key() == Qt.Key.Key_Escape:
                    self._dropdown.hide()
                    return True

        return super().eventFilter(obj, event)

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

    def __init__(self, target_bar: TokenizedBar, parent=None):
        super().__init__(parent)
        self.target_bar = target_bar
        if self.target_bar:
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

    def show_suggestions(self, items: list[str]):
        """Populates suggestions and displays floating dropdown without stealing focus."""
        if not items:
            self.hide()
            return

        self.clear()
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
        text = self.current_text()
        if text:
            self.suggestion_selected.emit(text)
            self.hide()
            if self.target_bar:
                self.target_bar.input_field.setFocus()

    def _on_item_clicked(self, item):
        if item:
            self.suggestion_selected.emit(item.text())
            self.hide()
            if self.target_bar:
                self.target_bar.input_field.setFocus()
