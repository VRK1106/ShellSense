from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFrame, QLabel, QLineEdit, QHBoxLayout, 
    QPushButton, QApplication, QFileDialog, QComboBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from shellsense.services.vault_service import VaultService

def center_widget_on_screen(widget):
    """Centers any top-level dialog on the primary desktop screen geometry."""
    screen = QApplication.primaryScreen()
    if screen:
        geom = screen.availableGeometry()
        x = (geom.width() - widget.width()) // 2
        y = (geom.height() - widget.height()) // 2
        widget.move(x, y)

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
        self.center_on_screen()

    def center_on_screen(self):
        center_widget_on_screen(self)

    def showEvent(self, event):
        super().showEvent(event)
        self.center_on_screen()

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


class ConfirmDeleteDialog(QDialog):
    def __init__(self, category_label: str, item_name: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(380, 160)
        self.center_on_screen()

    def center_on_screen(self):
        center_widget_on_screen(self)

    def showEvent(self, event):
        super().showEvent(event)
        self.center_on_screen()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid rgba(239, 68, 68, 0.6);
                border-radius: 12px;
            }
        """)
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(18, 16, 18, 16)
        c_layout.setSpacing(12)
        
        title = QLabel(f"🗑️ Delete {category_label}?", container)
        title.setStyleSheet("color: #ef4444; font-size: 14px; font-weight: bold; border: none;")
        c_layout.addWidget(title)
        
        msg = QLabel(f"Are you sure you want to delete <b>{item_name}</b>? This action cannot be undone.", container)
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #cbd5e1; font-size: 12px; border: none;")
        c_layout.addWidget(msg)
        
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)
        
        cancel_btn = QPushButton("Cancel", container)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #334155;
                color: #e2e8f0;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 500;
            }
            QPushButton:hover { background: #475569; }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        del_btn = QPushButton("Delete", container)
        del_btn.setStyleSheet("""
            QPushButton {
                background: #dc2626;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:hover { background: #b91c1c; }
        """)
        del_btn.clicked.connect(self.accept)
        
        btn_box.addStretch()
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(del_btn)
        c_layout.addLayout(btn_box)
        
        layout.addWidget(container)


class VaultItemEditDialog(QDialog):
    def __init__(self, key_name: str = "", is_edit: bool = False, parent=None):
        super().__init__(parent)
        self.is_edit = is_edit
        self.orig_key_name = key_name
        self.key_name = key_name
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(420, 310)
        self.center_on_screen()

    def center_on_screen(self):
        center_widget_on_screen(self)

    def showEvent(self, event):
        super().showEvent(event)
        self.center_on_screen()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background: #0f172a;
                border: 1px solid rgba(59, 130, 246, 0.6);
                border-radius: 12px;
            }
            QLabel {
                color: #94a3b8;
                font-size: 11px;
                font-weight: 600;
                border: none;
            }
            QLineEdit {
                background: #1e293b;
                color: #ffffff;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 7px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
            }
        """)
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(20, 18, 20, 18)
        c_layout.setSpacing(10)
        
        title_text = "🔒 Edit Credential" if is_edit else "🔒 Add New Vault Credential"
        title = QLabel(title_text, container)
        title.setStyleSheet("color: #60a5fa; font-size: 15px; font-weight: bold; border: none;")
        c_layout.addWidget(title)
        
        c_layout.addWidget(QLabel("CREDENTIAL / KEY NAME", container))
        self.key_input = QLineEdit(container)
        self.key_input.setPlaceholderText("e.g. github_token, wifi_password")
        self.key_input.setText(key_name)
        c_layout.addWidget(self.key_input)
        
        c_layout.addWidget(QLabel("SECRET VALUE TO PROTECT", container))
        self.val_input = QLineEdit(container)
        self.val_input.setPlaceholderText("Enter the password or secret...")
        self.val_input.setEchoMode(QLineEdit.EchoMode.Password)
        c_layout.addWidget(self.val_input)
        
        c_layout.addWidget(QLabel("MASTER PASSWORD (USED TO ENCRYPT)", container))
        self.pwd_input = QLineEdit(container)
        self.pwd_input.setPlaceholderText("Enter your master password...")
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        c_layout.addWidget(self.pwd_input)
        
        self.error_lbl = QLabel("", container)
        self.error_lbl.setStyleSheet("color: #ef4444; font-size: 11px; border: none;")
        self.error_lbl.hide()
        c_layout.addWidget(self.error_lbl)
        
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)
        
        cancel_btn = QPushButton("Cancel", container)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #334155;
                color: #e2e8f0;
                border: none;
                border-radius: 6px;
                padding: 7px 16px;
                font-weight: 500;
            }
            QPushButton:hover { background: #475569; }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Save Credential", container)
        save_btn.setStyleSheet("""
            QPushButton {
                background: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1d4ed8; }
        """)
        save_btn.clicked.connect(self.save)
        
        btn_box.addStretch()
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(save_btn)
        c_layout.addLayout(btn_box)
        
        layout.addWidget(container)

    def save(self):
        k = self.key_input.text().strip()
        v = self.val_input.text().strip()
        pwd = self.pwd_input.text().strip()
        if not k:
            self.error_lbl.setText("Credential name cannot be empty.")
            self.error_lbl.show()
            return
        if not v:
            self.error_lbl.setText("Secret value cannot be empty.")
            self.error_lbl.show()
            return
        if not pwd:
            self.error_lbl.setText("Master password is required for encryption.")
            self.error_lbl.show()
            return
            
        enc_val = VaultService.encrypt_value(v, pwd)
        from shellsense.core.db import DatabaseManager
        db = DatabaseManager.get_instance()
        if self.is_edit and self.orig_key_name and self.orig_key_name != k:
            db.delete_entry("vault", self.orig_key_name)
        db.save_entry("vault", k, enc_val)
        self.accept()


class ShortcutItemEditDialog(QDialog):
    def __init__(self, shortcut_name: str = "", file_path: str = "", is_edit: bool = False, parent=None):
        super().__init__(parent)
        self.is_edit = is_edit
        self.orig_name = shortcut_name
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(460, 250)
        self.center_on_screen()

    def center_on_screen(self):
        center_widget_on_screen(self)

    def showEvent(self, event):
        super().showEvent(event)
        self.center_on_screen()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background: #0f172a;
                border: 1px solid rgba(59, 130, 246, 0.6);
                border-radius: 12px;
            }
            QLabel {
                color: #94a3b8;
                font-size: 11px;
                font-weight: 600;
                border: none;
            }
            QLineEdit {
                background: #1e293b;
                color: #ffffff;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 7px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
            }
        """)
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(20, 18, 20, 18)
        c_layout.setSpacing(10)
        
        title_text = "📁 Edit File Shortcut" if is_edit else "📁 Add New File Shortcut"
        title = QLabel(title_text, container)
        title.setStyleSheet("color: #60a5fa; font-size: 15px; font-weight: bold; border: none;")
        c_layout.addWidget(title)
        
        c_layout.addWidget(QLabel("SHORTCUT ALIAS", container))
        self.name_input = QLineEdit(container)
        self.name_input.setPlaceholderText("e.g. resume, budget, project_dir")
        self.name_input.setText(shortcut_name)
        c_layout.addWidget(self.name_input)
        
        c_layout.addWidget(QLabel("TARGET FILE OR FOLDER PATH", container))
        path_box = QHBoxLayout()
        path_box.setSpacing(8)
        self.path_input = QLineEdit(container)
        self.path_input.setPlaceholderText("C:\\path\\to\\file.pdf")
        self.path_input.setText(file_path)
        path_box.addWidget(self.path_input)
        
        browse_file_btn = QPushButton("📄 File...", container)
        browse_file_btn.setStyleSheet("""
            QPushButton {
                background: #334155;
                color: #e2e8f0;
                border: none;
                border-radius: 6px;
                padding: 7px 12px;
                font-size: 12px;
            }
            QPushButton:hover { background: #475569; }
        """)
        browse_file_btn.clicked.connect(self.browse_file)
        path_box.addWidget(browse_file_btn)
        
        browse_dir_btn = QPushButton("📁 Folder...", container)
        browse_dir_btn.setStyleSheet("""
            QPushButton {
                background: #334155;
                color: #e2e8f0;
                border: none;
                border-radius: 6px;
                padding: 7px 12px;
                font-size: 12px;
            }
            QPushButton:hover { background: #475569; }
        """)
        browse_dir_btn.clicked.connect(self.browse_dir)
        path_box.addWidget(browse_dir_btn)
        
        c_layout.addLayout(path_box)
        
        self.error_lbl = QLabel("", container)
        self.error_lbl.setStyleSheet("color: #ef4444; font-size: 11px; border: none;")
        self.error_lbl.hide()
        c_layout.addWidget(self.error_lbl)
        
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)
        
        cancel_btn = QPushButton("Cancel", container)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #334155;
                color: #e2e8f0;
                border: none;
                border-radius: 6px;
                padding: 7px 16px;
                font-weight: 500;
            }
            QPushButton:hover { background: #475569; }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Save Shortcut", container)
        save_btn.setStyleSheet("""
            QPushButton {
                background: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1d4ed8; }
        """)
        save_btn.clicked.connect(self.save)
        
        btn_box.addStretch()
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(save_btn)
        c_layout.addLayout(btn_box)
        
        layout.addWidget(container)

    def browse_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Shortcut File")
        if f:
            self.path_input.setText(f)

    def browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Shortcut Directory")
        if d:
            self.path_input.setText(d)

    def save(self):
        k = self.name_input.text().strip()
        v = self.path_input.text().strip()
        if not k:
            self.error_lbl.setText("Shortcut name cannot be empty.")
            self.error_lbl.show()
            return
        if not v:
            self.error_lbl.setText("Target file/folder path cannot be empty.")
            self.error_lbl.show()
            return
            
        from shellsense.core.db import DatabaseManager
        db = DatabaseManager.get_instance()
        if self.is_edit and self.orig_name and self.orig_name != k:
            db.delete_entry("file", self.orig_name)
        db.save_entry("file", k, v)
        self.accept()


class CommandAIGeneratorThread(QThread):
    command_generated = pyqtSignal(str, str, str) # (query, syntax, source)

    def __init__(self, query: str, parent=None):
        super().__init__(parent)
        self.query = query

    def run(self):
        try:
            from shellsense.services.local_model_service import LocalModelService
            model_svc = LocalModelService.get_instance()
            syntax = model_svc.generate_shell_syntax(self.query)
            source = "AI Model" if not syntax.startswith("#") and ("Get-" in syntax or "Stop-" in syntax or "wsl" in syntax or "ipconfig" in syntax) else "Verified Template"
            self.command_generated.emit(self.query, syntax, source)
        except Exception as e:
            self.command_generated.emit(self.query, "", f"Error: {e}")


class CommandItemEditDialog(QDialog):
    def __init__(self, command_name: str = "", command_string: str = "", is_edit: bool = False, parent=None):
        super().__init__(parent)
        self.is_edit = is_edit
        self.orig_name = command_name
        self._last_generated_cmd = ""
        self._generator_thread = None
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(540, 420)
        self.center_on_screen()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background: #0f172a;
                border: 1px solid rgba(59, 130, 246, 0.65);
                border-radius: 12px;
            }
            QLabel {
                color: #94a3b8;
                font-size: 11px;
                font-weight: 600;
                border: none;
            }
            QLineEdit {
                background: #1e293b;
                color: #ffffff;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 7px 10px;
                font-size: 13px;
                font-family: 'Consolas', 'Cascadia Code', monospace;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
            }
        """)
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(22, 20, 22, 20)
        c_layout.setSpacing(10)
        
        # 1. Header
        title_text = "⚡ Edit Terminal Command" if is_edit else "⚡ Add New Terminal Command"
        title = QLabel(title_text, container)
        title.setStyleSheet("color: #60a5fa; font-size: 15px; font-weight: bold; border: none;")
        c_layout.addWidget(title)
        
        sub_title = QLabel("Type a command alias or natural language intent — ShellSense AI auto-generates the exact syntax.", container)
        sub_title.setWordWrap(True)
        sub_title.setStyleSheet("color: #64748b; font-size: 11px; font-weight: normal; border: none;")
        c_layout.addWidget(sub_title)
        
        # 2. Command Name / Intent Field with Auto-Generate Button
        name_hdr = QHBoxLayout()
        name_hdr.addWidget(QLabel("COMMAND ALIAS / WHAT YOU WANT TO DO", container))
        name_hdr.addStretch()
        
        self.ai_btn = QPushButton("✨ Auto-Generate with AI", container)
        self.ai_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(59, 130, 246, 0.2);
                border: 1px solid rgba(59, 130, 246, 0.5);
                border-radius: 5px;
                color: #93c5fd;
                font-size: 11px;
                font-weight: 600;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background-color: rgba(59, 130, 246, 0.35);
                color: #ffffff;
            }
        """)
        self.ai_btn.clicked.connect(self._trigger_ai_generation)
        name_hdr.addWidget(self.ai_btn)
        c_layout.addLayout(name_hdr)
        
        self.name_input = QLineEdit(container)
        self.name_input.setPlaceholderText("e.g. restart wsl, kill node, flush dns, clean temp files, check ip")
        self.name_input.setText(command_name)
        self.name_input.textChanged.connect(self._on_name_text_changed)
        c_layout.addWidget(self.name_input)
        
        # 3. Layer of Confirmation & Preview Card
        self.preview_card = QFrame(container)
        self.preview_card.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 41, 59, 0.7);
                border: 1px solid rgba(59, 130, 246, 0.35);
                border-radius: 8px;
            }
        """)
        preview_layout = QVBoxLayout(self.preview_card)
        preview_layout.setContentsMargins(12, 10, 12, 10)
        preview_layout.setSpacing(6)
        
        p_hdr = QHBoxLayout()
        p_title = QLabel("AI GENERATED SYNTAX PREVIEW", self.preview_card)
        p_title.setStyleSheet("color: #93c5fd; font-size: 10px; font-weight: bold; letter-spacing: 0.5px;")
        p_hdr.addWidget(p_title)
        p_hdr.addStretch()
        
        self.source_badge = QLabel("Verified Engine", self.preview_card)
        self.source_badge.setStyleSheet("color: #6ee7b7; font-size: 10px; font-weight: 600; padding: 2px 6px; background: rgba(16, 185, 129, 0.15); border-radius: 4px;")
        p_hdr.addWidget(self.source_badge)
        preview_layout.addLayout(p_hdr)
        
        self.preview_code_lbl = QLabel("Type a command above to see AI-generated syntax...", self.preview_card)
        self.preview_code_lbl.setWordWrap(True)
        self.preview_code_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.preview_code_lbl.setStyleSheet("color: #f1f5f9; font-family: 'Consolas', 'Cascadia Code', monospace; font-size: 12px; background: rgba(15, 23, 42, 0.6); padding: 6px 8px; border-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.05);")
        preview_layout.addWidget(self.preview_code_lbl)
        
        p_actions = QHBoxLayout()
        p_actions.addStretch()
        self.accept_preview_btn = QPushButton("✓ Use This Command", self.preview_card)
        self.accept_preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 5px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        self.accept_preview_btn.clicked.connect(self._accept_preview_syntax)
        p_actions.addWidget(self.accept_preview_btn)
        preview_layout.addLayout(p_actions)
        
        c_layout.addWidget(self.preview_card)
        if not command_string and not command_name:
            self.preview_card.hide()
        
        # 4. Final Shell Command Input
        c_layout.addWidget(QLabel("SHELL COMMAND / SCRIPT (POWERSHELL / CMD)", container))
        self.cmd_input = QLineEdit(container)
        self.cmd_input.setPlaceholderText("e.g. wsl --shutdown, Stop-Process -Name 'node' -Force, ipconfig /flushdns")
        self.cmd_input.setText(command_string)
        c_layout.addWidget(self.cmd_input)
        
        self.error_lbl = QLabel("", container)
        self.error_lbl.setStyleSheet("color: #ef4444; font-size: 11px; border: none;")
        self.error_lbl.hide()
        c_layout.addWidget(self.error_lbl)
        
        # 5. Dialog Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)
        
        cancel_btn = QPushButton("Cancel", container)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #334155;
                color: #e2e8f0;
                border: none;
                border-radius: 6px;
                padding: 7px 16px;
                font-weight: 500;
            }
            QPushButton:hover { background: #475569; }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Save Command", container)
        save_btn.setStyleSheet("""
            QPushButton {
                background: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 18px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1d4ed8; }
        """)
        save_btn.clicked.connect(self.save)
        
        btn_box.addStretch()
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(save_btn)
        c_layout.addLayout(btn_box)
        
        layout.addWidget(container)
        
        # Debounce timer for live inference as user types
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._run_background_inference)

    def center_on_screen(self):
        center_widget_on_screen(self)

    def showEvent(self, event):
        super().showEvent(event)
        self.center_on_screen()
        # If opening with an existing name but empty command, auto generate
        if self.name_input.text().strip() and not self.cmd_input.text().strip():
            self._trigger_ai_generation()

    def _on_name_text_changed(self, text: str):
        # Only auto-trigger if not in edit mode or command input is blank / matched previous auto-gen
        cur_cmd = self.cmd_input.text().strip()
        if not cur_cmd or cur_cmd == self._last_generated_cmd:
            self._debounce_timer.start(450)

    def _trigger_ai_generation(self):
        self._run_background_inference()

    def _run_background_inference(self):
        query = self.name_input.text().strip()
        if len(query) < 2:
            return
        
        self.source_badge.setText("Thinking...")
        self.source_badge.setStyleSheet("color: #93c5fd; font-size: 10px; font-weight: 600; padding: 2px 6px; background: rgba(59, 130, 246, 0.15); border-radius: 4px;")
        self.preview_code_lbl.setText("⚡ Analyzing natural language intent...")
        self.preview_card.show()
        
        if self._generator_thread and self._generator_thread.isRunning():
            self._generator_thread.terminate()
            self._generator_thread.wait(50)
            
        self._generator_thread = CommandAIGeneratorThread(query, self)
        self._generator_thread.command_generated.connect(self._on_command_generated)
        self._generator_thread.start()

    def _on_command_generated(self, query: str, syntax: str, source: str):
        if self.name_input.text().strip() != query:
            return
        
        if syntax:
            self._last_generated_cmd = syntax
            self.preview_code_lbl.setText(syntax)
            self.source_badge.setText(f"✓ {source}")
            self.source_badge.setStyleSheet("color: #6ee7b7; font-size: 10px; font-weight: 600; padding: 2px 6px; background: rgba(16, 185, 129, 0.15); border-radius: 4px;")
            self.preview_card.show()
            
            # Automatically populate command input if currently empty or holding prior auto-gen
            cur_cmd = self.cmd_input.text().strip()
            if not cur_cmd or cur_cmd == self._last_generated_cmd:
                self.cmd_input.setText(syntax)
        else:
            self.preview_code_lbl.setText(f"# Executable syntax for: {query}")
            self.source_badge.setText("Template")

    def _accept_preview_syntax(self):
        code = self.preview_code_lbl.text().strip()
        if code:
            self.cmd_input.setText(code)
            self.cmd_input.setFocus()

    def save(self):
        k = self.name_input.text().strip()
        v = self.cmd_input.text().strip()
        if not k:
            self.error_lbl.setText("Command name/alias cannot be empty.")
            self.error_lbl.show()
            return
        if not v:
            self.error_lbl.setText("Shell command string cannot be empty.")
            self.error_lbl.show()
            return
            
        from shellsense.core.db import DatabaseManager
        db = DatabaseManager.get_instance()
        if self.is_edit and self.orig_name and self.orig_name != k:
            db.delete_entry("command", self.orig_name)
        db.save_entry("command", k, v)
        self.accept()

