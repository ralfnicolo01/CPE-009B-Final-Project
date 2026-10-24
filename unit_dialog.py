"""Dialog opened by double-clicking a unit (dashboard or edit layout), or an empty cell to add one."""
import config as cfg
from data_manager import today
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QGridLayout, QFormLayout, QGroupBox, QLabel,
                             QComboBox, QPushButton, QHBoxLayout, QMessageBox, QLineEdit, QSpinBox)


class UnitDialog(QDialog):
    def __init__(self, dm, uid=None, parent=None, pos=None, can_delete=False):
        super().__init__(parent)
        self.dm, self.uid, self.pos = dm, uid, pos
        self.is_new = uid is None
        self.setWindowTitle("Add unit" if self.is_new else f"Edit unit {uid}")
        self.setMinimumWidth(560)
        root = QVBoxLayout(self); root.setSpacing(12)

        # ---- unit details (always editable, even when vacant) ----
        dbox = QGroupBox("Unit details")
        f = QFormLayout(dbox)
        self.location = QLineEdit(); self.location.setPlaceholderText("e.g. Gymnasium – Row A / Room 204")
        self.modality = QComboBox(); self.modality.addItems(cfg.MODALITIES)
        self.capacity = QSpinBox(); self.capacity.setRange(1, 1000); self.capacity.setValue(10)
        self.family = QLineEdit(); self.family.setPlaceholderText("Family / group name")
        self.headcount = QSpinBox(); self.headcount.setRange(0, 1000)
        f.addRow("Unit / Location", self.location)
        f.addRow("Setup modality", self.modality)
        f.addRow("Maximum capacity", self.capacity)
        f.addRow("Family name", self.family)
        f.addRow("Headcount (people)", self.headcount)
        root.addWidget(dbox)

        # ---- food status (existing units only) ----
        self.meal_widgets = {}
        if not self.is_new:
            self.meal_box = QGroupBox(f"Today's Meals – {today()}  (resets every day)")
            g = QGridLayout(self.meal_box); g.setVerticalSpacing(10)
            for i, meal in enumerate(cfg.MEALS):
                status = QComboBox(); status.addItems(["Pending", "Received"])
                ration = QComboBox()
                for key, label in cfg.RATIONS.items():
                    ration.addItem(label, key)
                g.addWidget(QLabel(meal), i, 0); g.addWidget(status, i, 1); g.addWidget(ration, i, 2)
                self.meal_widgets[meal] = (status, ration)
            self.meal_hint = QLabel(); self.meal_hint.setStyleSheet("color:#6b7280;font-size:12px;")
            g.addWidget(self.meal_hint, len(cfg.MEALS), 0, 1, 3)
            root.addWidget(self.meal_box)

            self.dswd_box = QGroupBox()
            d = QGridLayout(self.dswd_box)
            self.dswd = QComboBox(); self.dswd.addItems(["Not received", "Received"])
            self.dswd_info = QLabel(); self.dswd_info.setStyleSheet("color:#6b7280;")
            d.addWidget(QLabel("DSWD relief pack"), 0, 0); d.addWidget(self.dswd, 0, 1)
            d.addWidget(self.dswd_info, 1, 0, 1, 2)
            root.addWidget(self.dswd_box)
            self.headcount.valueChanged.connect(self._sync_food)

        # ---- buttons ----
        row = QHBoxLayout()
        if can_delete and not self.is_new:
            delete = QPushButton("Delete unit"); delete.setProperty("variant", "danger")
            delete.clicked.connect(self.delete)
            row.addWidget(delete)
        row.addStretch()
        cancel = QPushButton("Cancel"); cancel.setProperty("variant", "secondary")
        self.save_btn = QPushButton("Add unit" if self.is_new else "Save")
        row.addWidget(cancel); row.addWidget(self.save_btn)
        root.addLayout(row)
        cancel.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self.save)

        if not self.is_new:
            self._load()

    # ---------- loading ----------
    def _load(self):
        unit = next((u for u in self.dm.units() if u["id"] == self.uid), None)
        if not unit:
            self.reject(); return
        self.location.setText(unit["location"])
        self.modality.setCurrentText(unit["modality"])
        self.capacity.setValue(unit["capacity"])
        self.family.setText(unit["family_name"])
        self.headcount.setValue(unit["headcount"])

        st = self.dm.today_state()[self.uid]
        for meal, (sc, rc) in self.meal_widgets.items():
            m = st["meals"][meal]
            sc.setCurrentText(m["status"]); rc.setCurrentIndex(rc.findData(m["ration"]))
        dw = st["dswd"]
        self.dswd.setCurrentIndex(1 if dw["received"] else 0)
        self.dswd_box.setTitle(f"DSWD Relief Pack  (resupplied every {self.dm.cycle_days()} days)")
        self.dswd_info.setText(f"Last received: {dw['date']}  ·  Next due: {dw['next_due']}"
                               if dw["date"] else "No relief pack received in the current cycle.")
        self._sync_food()

    def _sync_food(self):
        n = self.headcount.value()
        for w in (self.meal_box, self.dswd_box):
            w.setEnabled(n > 0)
        self.meal_hint.setText(
            f"Marking a meal as Received deducts {n} pack(s) (one per person) from stock."
            if n > 0 else "Set a headcount above 0 to record food distribution.")

    # ---------- saving ----------
    def save(self):
        data = {"location": self.location.text().strip(),
                "modality": self.modality.currentText(),
                "capacity": self.capacity.value(),
                "family_name": self.family.text().strip(),
                "headcount": self.headcount.value()}
        problem = None
        if not data["location"]:
            problem = "Please enter the unit / location"
        elif data["headcount"] > data["capacity"]:
            problem = "Headcount is higher than capacity"
        elif data["headcount"] > 0 and not data["family_name"]:
            problem = "A family name is needed when people are registered"
        if problem:
            QMessageBox.warning(self, "Cannot save", problem + "."); return

        if self.is_new:
            col, row = self.pos
            self.dm.add_unit(data["location"], data["modality"], data["capacity"],
                             col, row, data["family_name"], data["headcount"])
            self.accept(); return

        self.dm.update_unit(self.uid, data)      # details first: meals use the saved headcount
        errors = []
        if data["headcount"] > 0:
            for meal, (sc, rc) in self.meal_widgets.items():
                ok, msg = self.dm.set_meal(self.uid, meal, sc.currentText(), rc.currentData())
                if not ok:
                    errors.append(f"{meal}: {msg}")
            ok, msg = self.dm.set_dswd(self.uid, self.dswd.currentIndex() == 1)
            if not ok:
                errors.append(f"DSWD: {msg}")
        if errors:
            QMessageBox.warning(self, "Unit saved, but some food changes were not",
                                "\n".join(errors))
            self._load()
        else:
            self.accept()

    def delete(self):
        if QMessageBox.question(self, "Delete unit", f"Delete {self.uid} and its records?"
                                ) == QMessageBox.StandardButton.Yes:
            self.dm.delete_unit(self.uid)
            self.accept()
