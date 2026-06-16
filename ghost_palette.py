import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QFrame, QLineEdit, QListWidget, QListWidgetItem, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QSize
from PyQt6.QtGui import QFont, QColor

class ScrollableListWidget(QListWidget):
    """Custom QListWidget with hidden scrollbars and keyboard navigation safety."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Premium dark-mode styling for command items
        self.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
                padding: 10px 16px;
            }
            QListWidget::item {
                color: rgba(255, 255, 255, 180);
                font-size: 15px;
                font-family: 'Segoe UI', 'Inter', sans-serif;
                padding: 12px 16px;
                border-radius: 8px;
                margin-bottom: 6px;
                background-color: transparent;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 15);
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: rgba(255, 255, 255, 25);
                color: #ffffff;
                outline: none;
            }
        """)

class GhostCommandPalette(QWidget):
    def __init__(self):
        super().__init__()
        
        # 1. Core Window Mechanics
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(650, 420)
        
        # 2. Window Layout and Container Setup
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Frosted glass-like main container frame
        self.container = QFrame(self)
        self.container.setObjectName("CentralContainer")
        self.container.setStyleSheet("""
            QFrame#CentralContainer {
                background-color: rgba(20, 20, 25, 220);
                border: 1px solid rgba(255, 255, 255, 35);
                border-radius: 12px;
            }
        """)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 3. Search Bar Widget
        self.search_bar = QLineEdit(self.container)
        self.search_bar.setPlaceholderText("Type a command...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #ffffff;
                font-size: 22px;
                font-family: 'Segoe UI', 'Inter', sans-serif;
                padding: 18px 20px;
                font-weight: 300;
            }
        """)
        self.search_bar.returnPressed.connect(self.execute_command)
        container_layout.addWidget(self.search_bar)
        
        # 4. Divider Line
        self.divider = QFrame(self.container)
        self.divider.setFrameShape(QFrame.Shape.HLine)
        self.divider.setStyleSheet("background-color: rgba(255, 255, 255, 25); max-height: 1px; border: none; margin: 0px 16px;")
        container_layout.addWidget(self.divider)
        
        # 5. Results List Widget
        self.results_list = ScrollableListWidget(self.container)
        self.results_list.itemDoubleClicked.connect(self.execute_command)
        container_layout.addWidget(self.results_list)
        
        main_layout.addWidget(self.container)
        
        # 6. Populate Mock Command Items
        self.populate_commands()
        
        # 7. Animation & Polish Mechanics
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(150)
        
        # Center perfectly on main screen
        self.center_on_screen()
        
    def populate_commands(self):
        commands = [
            "🖥️  Open System Terminal",
            "🚀  Launch Brave Web Browser",
            "⚙️  Open Windows Settings",
            "🧹  Clean System Temporary Files",
            "📊  Show Active Boot Applications",
            "🔐  Lock Local User Session",
            "🌐  Check Network Connectivity (Ping)"
        ]
        for cmd in commands:
            item = QListWidgetItem(cmd)
            self.results_list.addItem(item)
        # Select first item by default
        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)

    def center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            x = (geom.width() - self.width()) // 2
            y = (geom.height() - self.height()) // 2
            self.move(x, y)

    def showEvent(self, event):
        """Play smooth fade-in animation on widget show."""
        self.fade_animation.stop()
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()
        super().showEvent(event)
        self.search_bar.setFocus()

    def keyPressEvent(self, event):
        """Close immediately on Escape, route arrows to list navigation."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            # Pass navigation keys to list widget for seamless UX
            self.results_list.keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def execute_command(self):
        """Triggers action from current input or highlighted list item."""
        selected_item = self.results_list.currentItem()
        query = self.search_bar.text().strip()
        
        print("\n--- Executing Command ---")
        if query:
            print(f"User Query Entered: '{query}'")
        if selected_item:
            print(f"Highlighted Item Chosen: '{selected_item.text()}'")
        print("-------------------------\n")
        
        # Close palette after execution
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    palette = GhostCommandPalette()
    palette.show()
    sys.exit(app.exec())
