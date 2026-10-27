"""Main window: sidebar (navigation, signed-in user, logout) + Dashboard / Edit / Users pages."""
from datetime import datetime
import config as cfg
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (QMainWindow, QWidget, QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
                             QStackedWidget, QButtonGroup)
from dashboard_tab import DashboardTab
from edit_tab import EditTab
from users_tab import UsersTab
from data_manager import today
from widgets import label, ToggleSwitch


class MainWindow(QMainWindow):
    logout_requested = pyqtSignal()
    theme_toggled = pyqtSignal(bool)

    def __init__(self, dm, user="admin"):
        super().__init__()
        self.dm, self.user, self._day = dm, user, today()
        self.role = dm.role_of(user)
        self.setWindowTitle("Evacuation Center Relief Pack Tracker")
        self.resize(1380, 860)
        central = QWidget(); self.setCentralWidget(central)
        root = QHBoxLayout(central); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # ---- pages: (name, widget, refresh); Users is for Administrators only ----
        self.dashboard, self.edit = DashboardTab(dm), EditTab(dm)
        self.pages = [("Dashboard", self.dashboard, self.dashboard.refresh), ("Edit", self.edit, self.edit.reload)]
        if self.role == cfg.ROLES[0]:
            self.users = UsersTab(dm, user)
            self.pages.append(("Users", self.users, self.users.reload))

        # ---- sidebar ----
        side = QFrame(); side.setObjectName("sidebar"); side.setFixedWidth(220)
        sl = QVBoxLayout(side); sl.setContentsMargins(14, 22, 14, 18); sl.setSpacing(6)
        sl.addWidget(label("Relief Tracker", "logo")); sl.addSpacing(18); sl.addWidget(label("MENU"))
        self.stack, group = QStackedWidget(), QButtonGroup(self)
        for i, (name, page, _) in enumerate(self.pages):
            b = QPushButton(name); b.setCheckable(True); b.setChecked(i == 0)
            group.addButton(b, i); sl.addWidget(b); self.stack.addWidget(page)
        group.idClicked.connect(self._page_changed)
        sl.addStretch()
        sl.addWidget(label(f"{user}\n{self.role}"))
        logout = QPushButton("Logout"); logout.clicked.connect(self.logout_requested.emit)
        sl.addWidget(logout)

        # ---- header (greeting, dark mode switch, date) + pages ----
        titles = QVBoxLayout(); titles.setSpacing(2)
        self.greet = label(role="h1")
        titles.addWidget(self.greet)
        titles.addWidget(label("Here's your evacuation center overview for today.", "muted"))
        self.date_lbl = label(role="pill")
        self.dark = ToggleSwitch(dm.dark()); self.dark.setToolTip("Dark mode")
        self.dark.toggled.connect(self.theme_toggled.emit)
        head = QHBoxLayout(); head.setContentsMargins(24, 20, 24, 8)
        vc = Qt.AlignmentFlag.AlignVCenter
        head.addLayout(titles); head.addStretch()
        head.addWidget(label("Dark mode", "muted"), alignment=vc); head.addSpacing(8)
        head.addWidget(self.dark, alignment=vc); head.addSpacing(18)
        head.addWidget(self.date_lbl, alignment=vc)
        right = QVBoxLayout(); right.setSpacing(0)
        right.addLayout(head); right.addWidget(self.stack)
        root.addWidget(side); root.addLayout(right, 1)

        self.edit.data_changed.connect(self.dashboard.refresh)
        self._update_header()
        self.timer = QTimer(self); self.timer.timeout.connect(self._tick); self.timer.start(30_000)

    def _update_header(self):
        now = datetime.now()
        part = "morning" if now.hour < 12 else "afternoon" if now.hour < 18 else "evening"
        self.greet.setText(f"Good {part}, {self.user.title()}!")
        self.date_lbl.setText(now.strftime("%A, %B %d, %Y"))

    def _page_changed(self, i):
        self.stack.setCurrentIndex(i)
        self.pages[i][2]()

    def _tick(self):
        """Keep greeting/date current; on midnight rollover run the daily reset (meals / DSWD cycle)."""
        self._update_header()
        if today() != self._day:
            self._day = today()
            self.dm.daily_reset()
            self.dashboard.refresh()
