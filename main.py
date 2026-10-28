"""Entry point:  python main.py   (default login: admin / admin123)"""
import sys
from PyQt6.QtWidgets import QApplication
from data_manager import DataManager
from login_window import LoginWindow
from main_window import MainWindow
from styles import style

class Controller:
    def __init__(self, app):
        self.app, self.dm = app, DataManager()
        self.login = self.main = None
        app.setStyleSheet(style(self.dm.dark()))

    def set_dark(self, on):
        self.dm.set_dark(on)
        self.app.setStyleSheet(style(on))

    def show_login(self):
        self.login = LoginWindow(self.dm)
        self.login.authenticated.connect(self.show_main)
        self.login.show()

    def show_main(self, user):
        self.main = MainWindow(self.dm, user)
        self.main.logout_requested.connect(self.logout)
        self.main.theme_toggled.connect(self.set_dark)
        self.main.show()
        self.login.close()

    def logout(self):
        old = self.main
        self.show_login()
        old.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ctrl = Controller(app)
    ctrl.show_login()
    sys.exit(app.exec())