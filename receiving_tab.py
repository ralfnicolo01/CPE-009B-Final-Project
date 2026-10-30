"""Fast meal handout page with searchable evacuees and per-person stock accounting."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QCheckBox)
import config as cfg


class ReceivingTab(QWidget):
    def __init__(self, dm):
        super().__init__()
        self.dm = dm
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.addWidget(QLabel("Search for an evacuee, select the meal, then record the handout."))

        controls = QGroupBox("Meal handout")
        row = QHBoxLayout(controls)
        self.search = QLineEdit(); self.search.setPlaceholderText("Search name, family, barangay, or unit…")
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.refresh)
        self.search.returnPressed.connect(self.refresh)
        self.meal = QComboBox(); self.meal.addItems(cfg.MEALS)
        self.meal.currentTextChanged.connect(self.refresh)
        self.status_filter = QComboBox(); self.status_filter.addItems(("All", "Waiting", "Served"))
        self.status_filter.currentTextChanged.connect(self.refresh)
        self.ration = QComboBox()
        for key, label in cfg.RATIONS.items(): self.ration.addItem(label, key)
        row.addWidget(self.search, 1); row.addWidget(self.search_button)
        row.addWidget(QLabel("Status")); row.addWidget(self.status_filter)
        row.addWidget(QLabel("Meal")); row.addWidget(self.meal)
        row.addWidget(QLabel("Food")); row.addWidget(self.ration, 1)
        root.addWidget(controls)

        self.count = QLabel(); root.addWidget(self.count)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Unit", "Family", "Evacuee", "Age", "Status", "Food received", "Received?"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().hide(); self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        root.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.family_button = QPushButton("Serve selected family")
        self.family_button.setProperty("variant", "secondary")
        self.family_button.clicked.connect(self.serve_family)
        self.dswd_button = QPushButton("Record DSWD pack for family")
        self.dswd_button.setProperty("variant", "secondary")
        self.dswd_button.clicked.connect(self.serve_dswd_family)
        actions.addWidget(self.family_button)
        actions.addWidget(self.dswd_button); actions.addStretch()
        root.addLayout(actions)
        self.refresh()

    def _records(self):
        records = []
        for unit in self.dm.units():
            uid = unit["id"]
            for family in self.dm.families(uid):
                for member in family.get("members", []):
                    meals = self.dm.member_meals_today(uid, member["id"])
                    meal = meals.get(self.meal.currentText(), {})
                    records.append({"uid": uid, "family": family, "member": member,
                                    "status": meal.get("status", "Pending"),
                                    "ration": meal.get("ration", "")})
        return records

    def refresh(self, *_):
        query = self.search.text().strip().casefold()
        status_filter = self.status_filter.currentText()
        visible = []
        for rec in self._records():
            unit = rec["uid"]
            family, member = rec["family"], rec["member"]
            haystack = " ".join((unit, family.get("family_name", ""), family.get("barangay", ""),
                                 member.get("name", ""), str(member.get("age", "")))).casefold()
            status_matches = (status_filter == "All" or
                              (status_filter == "Waiting" and rec["status"] != "Received") or
                              (status_filter == "Served" and rec["status"] == "Received"))
            if query in haystack and status_matches: visible.append(rec)
        self.table.setRowCount(len(visible))
        for r, rec in enumerate(visible):
            meal_label = cfg.RATIONS.get(rec["ration"], "")
            values = (rec["uid"], rec["family"].get("family_name", ""),
                      rec["member"].get("name", ""), str(rec["member"].get("age", "")),
                      rec["status"], meal_label)
            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                if c != 2: item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if c == 0: item.setData(Qt.ItemDataRole.UserRole, (rec["uid"], rec["family"]["id"], rec["member"]["id"]))
                self.table.setItem(r, c, item)
            received = QCheckBox()
            received.setChecked(rec["status"] == "Received")
            received.setToolTip("Check when this member receives the selected meal")
            received.toggled.connect(lambda checked, row=r, uid=rec["uid"], mid=rec["member"]["id"],
                                     meal=self.meal.currentText(), box=received:
                                     self._set_member_received(row, uid, mid, meal, box, checked))
            cell = QWidget(); cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0); cell_layout.addWidget(received, alignment=Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(r, 6, cell)
        self.count.setText(f"{len(visible)} evacuee(s) shown · {self.meal.currentText()} · Remaining RTEF stock: {self.dm.stock().get('RTEF', {}).get('qty', 0)}")
        self.family_button.setEnabled(bool(visible))
        self.dswd_button.setEnabled(bool(visible))

    def _selected(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _record(self, family_only=False):
        selected = self._selected()
        if not selected:
            QMessageBox.information(self, "Select an evacuee", "Choose a person from the list first.")
            return
        uid, family_id, member_id = selected
        mids = [member_id]
        if family_only:
            family = next((f for f in self.dm.families(uid) if f["id"] == family_id), None)
            mids = [m["id"] for m in family.get("members", [])] if family else []
        ok, msg = self.dm.set_members_meal(uid, mids, self.meal.currentText(), "Received", self.ration.currentData())
        if not ok:
            QMessageBox.warning(self, "Could not record handout", msg)
            return
        self.refresh()

    def serve_family(self): self._record(family_only=True)

    def _set_member_received(self, row, uid, member_id, meal, checkbox, received):
        self.table.selectRow(row)
        ration = self.ration.currentData()
        ok, msg = self.dm.set_member_meal(uid, member_id, meal,
                                          "Received" if received else "Pending", ration)
        if not ok:
            checkbox.blockSignals(True); checkbox.setChecked(not received); checkbox.blockSignals(False)
            QMessageBox.warning(self, "Could not record handout", msg)
            return
        self.refresh()

    def serve_dswd_family(self):
        selected = self._selected()
        if not selected:
            QMessageBox.information(self, "Select a family", "Choose a family member from the list first.")
            return
        uid, family_id, _member_id = selected
        state = self.dm.dswd_family_state(uid, family_id)
        if state["received"]:
            QMessageBox.information(self, "Already recorded",
                                    f"This family received a DSWD pack on {state['date']}. "
                                    f"The next pack is due {state['next_due']}.")
            return
        ok, msg = self.dm.set_dswd_family(uid, family_id, True)
        if not ok:
            QMessageBox.warning(self, "Could not record pack", msg)
            return
        QMessageBox.information(self, "Pack recorded", "The DSWD relief pack was recorded for this family.")
        self.refresh()
