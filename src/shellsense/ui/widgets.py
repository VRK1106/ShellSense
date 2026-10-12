from PyQt6.QtWidgets import QScrollArea, QLabel
from PyQt6.QtCore import Qt

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
