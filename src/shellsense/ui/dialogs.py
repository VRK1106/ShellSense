from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFrame, QLabel, QLineEdit, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from shellsense.services.vault_service import VaultService

class VaultPasswordDialog(QDialog):
    def __init__(self, key_name: str, enc_val: str, parent=None):
        super().__init__(parent)
        self.key_name = key_name
        self.enc_val = enc_val
        self.decrypted_text = None
        
        self.setWindowTitle("ShellSense Vault - Password Required")
        self.setFixedSize(380, 180)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        frame = QFrame(self)
        frame.setStyleSheet("""
            QFrame {
                background-color: #121826;
                border: 1px solid #3b82f6;
                border-radius: 12px;
            }
        """)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(16, 16, 16, 16)
        frame_layout.setSpacing(10)

        title_lbl = QLabel(f"🔒 <b>Protected Snippet:</b> {key_name}", frame)
        title_lbl.setStyleSheet("color: #60a5fa; font-size: 14px; border: none;")
        frame_layout.addWidget(title_lbl)

        self.pass_input = QLineEdit(frame)
        self.pass_input.setPlaceholderText("Enter Master Password...")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setStyleSheet("""
            QLineEdit {
                background: #1e293b;
                color: #ffffff;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
            }
        """)
        self.pass_input.returnPressed.connect(self.attempt_unlock)
        frame_layout.addWidget(self.pass_input)

        self.error_lbl = QLabel("", frame)
        self.error_lbl.setStyleSheet("color: #ef4444; font-size: 11px; border: none;")
        self.error_lbl.hide()
        frame_layout.addWidget(self.error_lbl)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)
        
        cancel_btn = QPushButton("Cancel", frame)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #334155;
                color: #e2e8f0;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #475569;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        unlock_btn = QPushButton("Unlock & Copy", frame)
        unlock_btn.setStyleSheet("""
            QPushButton {
                background: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1d4ed8;
            }
        """)
        unlock_btn.clicked.connect(self.attempt_unlock)

        btn_box.addStretch()
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(unlock_btn)
        frame_layout.addLayout(btn_box)

        layout.addWidget(frame)
        self.pass_input.setFocus()

    def attempt_unlock(self):
        password = self.pass_input.text().strip()
        if not password:
            self.error_lbl.setText("Password cannot be empty.")
            self.error_lbl.show()
            return
            
        decrypted = VaultService.decrypt_value(self.enc_val, password)
        if decrypted is not None:
            self.decrypted_text = decrypted
            self.accept()
        else:
            self.error_lbl.setText("Incorrect master password.")
            self.error_lbl.show()
            self.pass_input.selectAll()

class DestructiveConfirmDialog(QDialog):
    """Confirmation modal for safety-critical and destructive operations (POWER_OFF, RESTART, PROCESS_KILL)."""
    def __init__(self, action_title: str, action_desc: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.action_title = action_title
        self.action_desc = action_desc
        self.initUI()

    def center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def initUI(self):
        self.setFixedSize(420, 210)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        frame = QFrame(self)
        frame.setStyleSheet("""
            QFrame {
                background: #0f172a;
                border: 2px solid #ef4444;
                border-radius: 12px;
            }
        """)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(22, 18, 22, 18)
        frame_layout.setSpacing(12)

        header = QLabel("⚠️ Confirm System Action", frame)
        header.setStyleSheet("color: #ef4444; font-size: 15px; font-weight: bold; border: none;")
        frame_layout.addWidget(header)

        desc = QLabel(frame)
        desc.setTextFormat(Qt.TextFormat.RichText)
        desc.setText(f"Are you sure you want to execute:<br><b style='color: #f8fafc; font-size: 14px;'>{self.action_desc}</b>?")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #cbd5e1; font-size: 13px; border: none; line-height: 1.4;")
        frame_layout.addWidget(desc)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)

        cancel_btn = QPushButton("Cancel (Esc)", frame)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #334155;
                color: #e2e8f0;
                border: none;
                border-radius: 6px;
                padding: 7px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #475569;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        confirm_btn = QPushButton("Yes, Execute", frame)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background: #dc2626;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #b91c1c;
            }
        """)
        confirm_btn.clicked.connect(self.accept)
        btn_box.addStretch()
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(confirm_btn)
        frame_layout.addLayout(btn_box)

        layout.addWidget(frame)
        self.center_on_screen()
        confirm_btn.setFocus()

class RegistrationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.initUI()
        
    def initUI(self):
        self.setFixedSize(360, 240)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        container = QFrame(self)
        container.setObjectName("Container")
        container.setStyleSheet("""
            QFrame#Container {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a1a2e, stop:1 #11111e);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Segoe UI', 'Inter', sans-serif;
                border: none;
                background: transparent;
            }
            QLineEdit {
                background-color: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                color: white;
                font-size: 13px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
            }
            QLineEdit:focus {
                border-color: rgba(0, 122, 255, 180);
            }
            QPushButton {
                background-color: rgba(0, 122, 255, 180);
                border: 1px solid rgba(0, 122, 255, 255);
                border-radius: 6px;
                color: white;
                font-size: 13px;
                font-weight: bold;
                padding: 8px;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(0, 122, 255, 230);
            }
        """)
        
        inner_layout = QVBoxLayout(container)
        inner_layout.setContentsMargins(20, 20, 20, 20)
        inner_layout.setSpacing(10)
        
        header = QLabel("ShellSense Setup", container)
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #007aff;")
        inner_layout.addWidget(header)
        
        subtext = QLabel("Please enter your details to personalize your experience.", container)
        subtext.setStyleSheet("font-size: 11px; color: rgba(255, 255, 255, 160);")
        subtext.setWordWrap(True)
        inner_layout.addWidget(subtext)
        
        self.name_input = QLineEdit(container)
        self.name_input.setPlaceholderText("Full Name")
        inner_layout.addWidget(self.name_input)
        
        self.email_input = QLineEdit(container)
        self.email_input.setPlaceholderText("Email Address")
        inner_layout.addWidget(self.email_input)
        
        self.error_label = QLabel("", container)
        self.error_label.setStyleSheet("color: #ff5252; font-size: 11px; font-weight: 500;")
        self.error_label.setVisible(False)
        inner_layout.addWidget(self.error_label)
        
        submit_btn = QPushButton("Submit", container)
        submit_btn.clicked.connect(self.validate_and_submit)
        inner_layout.addWidget(submit_btn)
        
        layout.addWidget(container)
        self.center_on_screen()
        
    def center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
    def validate_and_submit(self):
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        
        if not name:
            self.error_label.setText("Name field cannot be empty.")
            self.error_label.setVisible(True)
            return
            
        if not email:
            self.error_label.setText("Email field cannot be empty.")
            self.error_label.setVisible(True)
            return
            
        if "@" not in email or "." not in email:
            self.error_label.setText("Please enter a valid email address.")
            self.error_label.setVisible(True)
            return
            
        import os
        import json
        from shellsense.core.config import USER_DIR
        user_info_path = os.path.join(USER_DIR, "user_info.json")
        try:
            with open(user_info_path, "w") as f:
                json.dump({"name": name, "email": email}, f)
            self.accept()
        except Exception as e:
            self.error_label.setText(f"Save error: {e}")
            self.error_label.setVisible(True)
