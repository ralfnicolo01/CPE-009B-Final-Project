"""Users page (Administrators only): add users, change their roles, delete them."""
import config as cfg
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QComboBox, QLineEdit,
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QMessageBox)
from widgets import label, scroll_page

def _cell(widget):
    """Wrap a cell widget with a little padding so it does not touch the cell borders."""
    box = QWidget(); lay = QHBoxLayout(box); lay.setContentsMargins(6, 5, 6, 5)
    lay.addWidget(widget)
    return box

class UsersTab(QWidget):
    ROW_H = 44

    def __init__(self, dm, current_user):
        super().__init__()
        self.dm, self.me = dm, current_user
        root = scroll_page(self)

        # ---- add user ----
        box = QGroupBox("Add user")
        f = QFormLayout(box)
        self.name, self.pw, self.pw2, self.role = QLineEdit(), QLineEdit(), QLineEdit(), QComboBox()
        self.name.setPlaceholderText("Username")
        for e, hint in ((self.pw, "At least 6 characters"), (self.pw2, "Repeat the password")):
            e.setPlaceholderText(hint); e.setEchoMode(QLineEdit.EchoMode.Password)
        self.role.addItems(cfg.ROLES)
        add = QPushButton("Add user"); add.clicked.connect(self.add)
        for e in (self.name, self.pw, self.pw2):
            e.returnPressed.connect(self.add)
        row = QHBoxLayout(); row.addStretch(); row.addWidget(add)
        for text, w in (("Username", self.name), ("Password", self.pw),
                        ("Confirm password", self.pw2), ("Role", self.role)):
            f.addRow(text, w)
        f.addRow(row)
        root.addWidget(box)

        # ---- user list ----
        tbox = QGroupBox("Users and roles")
        tl = QVBoxLayout(tbox)
        tl.addWidget(label("Only Administrators can see this page. Change a role from its dropdown.", "hint"))
        self.table = t = QTableWidget(0, 3)
        t.setHorizontalHeaderLabels(["Username", "Role", ""])
        t.verticalHeader().setVisible(False); t.verticalHeader().setDefaultSectionSize(self.ROW_H)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        h = t.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed); t.setColumnWidth(1, 240)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed); t.setColumnWidth(2, 110)
        tl.addWidget(t)
        root.addWidget(tbox)
        root.addStretch()
        self.reload()

    def reload(self):
        users = self.dm.users()
        t = self.table
        t.setRowCount(len(users))
        t.setFixedHeight(t.horizontalHeader().height() + self.ROW_H * len(users) + 4)
        for r, u in enumerate(users):
            name = u["username"]
            t.setItem(r, 0, QTableWidgetItem(name + ("   (you)" if name == self.me else "")))
            combo = QComboBox(); combo.addItems(cfg.ROLES)
            if u["role"] not in cfg.ROLES:
                combo.addItem(u["role"])
            combo.setCurrentText(u["role"])
            combo.currentTextChanged.connect(lambda role, n=name: self.change_role(n, role))
            t.setCellWidget(r, 1, _cell(combo))
            btn = QPushButton("Delete"); btn.setProperty("variant", "danger")
            btn.setEnabled(name != self.me)               # you cannot delete yourself
            btn.clicked.connect(lambda _, n=name: self.delete(n))
            t.setCellWidget(r, 2, _cell(btn))

    def add(self):
        if self.pw.text() != self.pw2.text():
            QMessageBox.warning(self, "Cannot add user", "The passwords do not match."); return
        ok, msg = self.dm.add_user(self.name.text(), self.pw.text(), self.role.currentText())
        if not ok:
            QMessageBox.warning(self, "Cannot add user", msg); return
        for e in (self.name, self.pw, self.pw2):
            e.clear()
        self.reload()

    def change_role(self, name, role):
        ok, msg = self.dm.set_role(name, role)
        if not ok:
            QMessageBox.warning(self, "Cannot change role", msg)
            QTimer.singleShot(0, self.reload)             # put the dropdown back

    def delete(self, name):
        if QMessageBox.question(self, "Delete user", f"Delete user {name}?"
                                ) != QMessageBox.StandardButton.Yes:
            return
        ok, msg = self.dm.delete_user(name)
        if not ok:
            QMessageBox.warning(self, "Cannot delete user", msg)
        QTimer.singleShot(0, self.reload)