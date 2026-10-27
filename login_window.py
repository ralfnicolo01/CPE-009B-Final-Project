"""Admin login screen."""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QFrame, QVBoxLayout, QLineEdit, QCheckBox, QPushButton
from widgets import label


class LoginWindow(QWidget):
    authenticated = pyqtSignal(str)     # username

    def __init__(self, dm):
        super().__init__()
        self.dm = dm
        self.setObjectName("login")
        self.setWindowTitle("Relief Tracker – Admin Login")
        self.resize(460, 460)

        outer = QVBoxLayout(self); outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card = QFrame(); card.setObjectName("loginCard"); card.setFixedWidth(340)
        lay = QVBoxLayout(card); lay.setContentsMargins(28, 28, 28, 28); lay.setSpacing(10)

        self.user = QLineEdit(); self.user.setPlaceholderText("Username")
        self.pw = QLineEdit(); self.pw.setPlaceholderText("Password")
        self.pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.show_pw = QCheckBox("Show password")
        self.show_pw.toggled.connect(lambda on: self.pw.setEchoMode(
            QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password))
        self.error = label(role="err", center=True)
        btn = QPushButton("Login")

        for w in (label("Evacuation Center\nRelief Pack Tracker", "h2", True),
                  label("Administrator sign in", "muted", True),
                  self.user, self.pw, self.show_pw, self.error, btn):
            lay.addWidget(w)
        outer.addWidget(card)

        for s in (btn.clicked, self.user.returnPressed, self.pw.returnPressed):
            s.connect(self.attempt)

    def attempt(self):
        name = self.user.text().strip()
        if self.dm.verify_login(name, self.pw.text()):
            self.dm.log("SYSTEM", "Admin login", name)
            self.authenticated.emit(name)
        else:
            self.error.setText("Invalid username or password.")
            self.pw.clear(); self.pw.setFocus()
