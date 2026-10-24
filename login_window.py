"""Admin login screen."""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QWidget, QFrame, QVBoxLayout, QLabel, QLineEdit,
                             QCheckBox, QPushButton)


class LoginWindow(QWidget):
    authenticated = pyqtSignal()

    def __init__(self, dm):
        super().__init__()
        self.dm = dm
        self.setObjectName("login")
        self.setWindowTitle("Relief Tracker – Admin Login")
        self.resize(460, 460)

        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card = QFrame(); card.setObjectName("loginCard"); card.setFixedWidth(340)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(28, 28, 28, 28); lay.setSpacing(10)

        title = QLabel("Evacuation Center\nRelief Pack Tracker")
        title.setStyleSheet("font-size:18px;font-weight:700;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel("Administrator sign in")
        sub.setStyleSheet("color:#6b7280;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.user = QLineEdit(); self.user.setPlaceholderText("Username")
        self.pw = QLineEdit(); self.pw.setPlaceholderText("Password")
        self.pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.show_pw = QCheckBox("Show password")
        self.show_pw.toggled.connect(
            lambda on: self.pw.setEchoMode(QLineEdit.EchoMode.Normal if on
                                           else QLineEdit.EchoMode.Password))
        self.error = QLabel(""); self.error.setStyleSheet("color:#dc2626;")
        self.error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn = QPushButton("Login")

        for w in (title, sub, self.user, self.pw, self.show_pw, self.error, btn):
            lay.addWidget(w)
        outer.addWidget(card)

        btn.clicked.connect(self.attempt)
        self.user.returnPressed.connect(self.attempt)
        self.pw.returnPressed.connect(self.attempt)

    def attempt(self):
        if self.dm.verify_login(self.user.text().strip(), self.pw.text()):
            self.dm.log("SYSTEM", "Admin login", self.user.text().strip())
            self.authenticated.emit()
        else:
            self.error.setText("Invalid username or password.")
            self.pw.clear(); self.pw.setFocus()
