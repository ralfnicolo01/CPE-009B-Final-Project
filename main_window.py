"""Main window with Dashboard and Edit tabs."""
from datetime import datetime
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTabWidget)
from dashboard_tab import DashboardTab
from edit_tab import EditTab
from data_manager import today


class MainWindow(QMainWindow):
    logout_requested = pyqtSignal()

    def __init__(self, dm):
        super().__init__()
        self.dm = dm
        self._day = today()
        self.setWindowTitle("Evacuation Center Relief Pack Tracker")
        self.resize(1180, 840)

        central = QWidget(); self.setCentralWidget(central)
        lay = QVBoxLayout(central); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)

        header = QHBoxLayout(); header.setContentsMargins(20, 14, 20, 4)
        title = QLabel("Relief Pack Tracker"); title.setStyleSheet("font-size:18px;font-weight:700;")
        self.date_lbl = QLabel(); self.date_lbl.setStyleSheet("color:#6b7280;")
        logout = QPushButton("Logout"); logout.setProperty("variant", "secondary")
        logout.clicked.connect(self.logout_requested.emit)
        header.addWidget(title); header.addStretch(); header.addWidget(self.date_lbl); header.addWidget(logout)
        lay.addLayout(header)

        self.dashboard, self.edit = DashboardTab(dm), EditTab(dm)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.dashboard, "Dashboard")
        self.tabs.addTab(self.edit, "Edit")
        lay.addWidget(self.tabs)

        self.edit.data_changed.connect(self.dashboard.refresh)
        self.tabs.currentChanged.connect(self._tab_changed)

        self._update_date()
        self.timer = QTimer(self); self.timer.timeout.connect(self._tick); self.timer.start(30_000)

    def _update_date(self):
        self.date_lbl.setText(datetime.now().strftime("%A, %B %d, %Y"))

    def _tab_changed(self, i):
        (self.dashboard.refresh if i == 0 else self.edit.reload)()

    def _tick(self):
        """Detect midnight rollover -> daily reset (meals) / DSWD cycle check."""
        if today() != self._day:
            self._day = today()
            self.dm.daily_reset()
            self._update_date()
            self.dashboard.refresh()
