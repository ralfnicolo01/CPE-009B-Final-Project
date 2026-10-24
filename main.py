"""Entry point:  python main.py   (default login: admin / admin123)"""
import sys
from PyQt6.QtWidgets import QApplication
from data_manager import DataManager
from login_window import LoginWindow
from main_window import MainWindow
from styles import STYLE


class Controller:
    def __init__(self):
        self.dm = DataManager()
        self.login = self.main = None

    def show_login(self):
        self.login = LoginWindow(self.dm)
        self.login.authenticated.connect(self.show_main)
        self.login.show()

    def show_main(self):
        self.main = MainWindow(self.dm)
        self.main.logout_requested.connect(self.logout)
        self.main.show()
        self.login.close()

    def logout(self):
        old = self.main
        self.show_login()
        old.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    ctrl = Controller()
    ctrl.show_login()
    sys.exit(app.exec())
