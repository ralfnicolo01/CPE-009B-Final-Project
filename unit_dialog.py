"""Unit editor for shelter and family/member registration."""
import uuid

import config as cfg
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIntValidator
from PyQt6.QtWidgets import (QComboBox, QDialog, QFormLayout, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QTextEdit)


class UnitDialog(QDialog):
    def __init__(self, dm, uid=None, parent=None, pos=None, can_delete=False, initial_family_id=None):
        super().__init__(parent)
        self.dm, self.uid, self.pos = dm, uid, pos
        self.is_new = uid is None
        self.families_list = []
        self.selected_family_id = None
        self.setWindowTitle("Add unit" if self.is_new else f"Edit unit {uid}")
        self.resize(900, 760); self.setMinimumSize(760, 600)
        outer = QVBoxLayout(self)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        content = QWidget(); root = QVBoxLayout(content); root.setSpacing(12)
        scroll.setWidget(content); outer.addWidget(scroll)

        details = QGroupBox("Unit details"); form = QFormLayout(details)
        self.location = QLineEdit(); self.location.setPlaceholderText("e.g. Gymnasium – Row A / Room 204")
        self.modality = QComboBox(); self.modality.addItems(cfg.MODALITIES)
        self.capacity = QSpinBox(); self.capacity.setRange(1, 1000); self.capacity.setValue(10)
        self.capacity.setSuffix(" people")  # added
        self.capacity_label = QLabel("Maximum capacity")  # added
        form.addRow("Unit / Location", self.location); form.addRow("Setup modality", self.modality)
        form.addRow(self.capacity_label, self.capacity); root.addWidget(details)
        self.modality.currentTextChanged.connect(self._modality_changed)

        self.family_box = QGroupBox("Sheltered families")
        fam = QVBoxLayout(self.family_box)
        self.occupancy_label = QLabel("Occupants: 0")
        fam.addWidget(self.occupancy_label)
        self.family_search = QLineEdit(); self.family_search.setPlaceholderText("Find a family…")
        self.family_search.textChanged.connect(self._refresh_family_table)
        fam.addWidget(self.family_search)
        self.family_table = QTableWidget(0, 4); self.family_table.setHorizontalHeaderLabels(["Family", "Barangay", "Members", "Action"])  # added: show one barangay per family
        self.family_table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)  # added: center table headings
        self.family_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.family_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.family_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.family_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.family_table.verticalHeader().hide()
        self.family_table.verticalHeader().setDefaultSectionSize(34)  # added: make family rows easier to read
        self.family_table.setMinimumHeight(175)  # added: fit at least three family rows at once
        self.family_table.setMaximumHeight(250)
        self.capacity.valueChanged.connect(self._refresh_family_table)  # added: keep the occupant summary in sync
        self.family_table.cellClicked.connect(self._select_family_row); fam.addWidget(self.family_table)
        addrow = QHBoxLayout(); self.new_family = QLineEdit(); self.new_family.setPlaceholderText("Family name")
        self.add_family_button = QPushButton("Add family"); self.add_family_button.clicked.connect(self._add_family)
        addrow.addWidget(self.new_family, 1); addrow.addWidget(self.add_family_button); fam.addLayout(addrow)
        root.addWidget(self.family_box)

        self.member_box = QGroupBox("Selected family — registration")
        mb = QVBoxLayout(self.member_box)
        self.family_name = QLineEdit(); self.family_name.setPlaceholderText("Family name")
        mb.addWidget(self.family_name)
        self.family_barangay = QLineEdit(); self.family_barangay.setPlaceholderText("Family barangay")  # added: barangay belongs to the family
        mb.addWidget(self.family_barangay)
        self.member_table = QTableWidget(0, 2)
        self.member_table.setHorizontalHeaderLabels(["Full name", "Age"])
        self.member_table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)  # added: center table headings
        for c in range(2): self.member_table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        self.member_table.verticalHeader().hide(); self.member_table.setMinimumHeight(150)
        mb.addWidget(self.member_table)
        controls = QGridLayout()
        self.member_name = QLineEdit(); self.member_name.setPlaceholderText("Member full name")
        self.member_age = QLineEdit(); self.member_age.setPlaceholderText("Age"); self.member_age.setValidator(QIntValidator(0, 120, self))
        self.add_member_button = QPushButton("Add member"); self.add_member_button.clicked.connect(self._add_member)
        controls.addWidget(self.member_name, 0, 0); controls.addWidget(self.member_age, 0, 1)
        controls.addWidget(self.add_member_button, 0, 2)
        mb.addLayout(controls)
        batch = QHBoxLayout()
        self.member_batch = QTextEdit(); self.member_batch.setPlaceholderText(
            "Quick add: paste one person per line as Full Name, Age\nExample: Maria Santos, 34")
        self.member_batch.setMaximumHeight(82)
        self.add_batch_button = QPushButton("Add list")
        self.add_batch_button.setProperty("variant", "secondary")
        self.add_batch_button.clicked.connect(self._add_member_batch)
        batch.addWidget(self.member_batch, 1); batch.addWidget(self.add_batch_button)
        mb.addLayout(batch)
        self.remove_member_button = QPushButton("Remove selected member")
        self.remove_member_button.clicked.connect(self._remove_member); mb.addWidget(self.remove_member_button)
        root.addWidget(self.member_box)

        buttons = QHBoxLayout()
        if can_delete and not self.is_new:
            delete = QPushButton("Delete unit"); delete.clicked.connect(self.delete); buttons.addWidget(delete)
        buttons.addStretch(); cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        self.save_button = QPushButton("Add unit" if self.is_new else "Save"); self.save_button.clicked.connect(self.save)
        buttons.addWidget(cancel); buttons.addWidget(self.save_button); outer.addLayout(buttons)

        if not self.is_new:
            self._load()
        self._refresh_family_table()
        self._modality_changed(self.modality.currentText())  # added: apply tent limits on initial open too
        if self.families_list:
            family_id = initial_family_id if any(f["id"] == initial_family_id for f in self.families_list) else self.families_list[0]["id"]
            self._select_family(family_id)
        else:
            self.member_box.setEnabled(False)

    def _modality_changed(self, modality):
        tent = modality == "Tent"
        if tent:
            self.capacity.setRange(5, 6)  # added: tents hold only five or six people
            self.capacity_label.setText("Maximum capacity (5–6 people for a tent)")  # added
        else:
            self.capacity.setRange(1, 1000)
            self.capacity_label.setText("Maximum capacity")
        self.family_search.setVisible(not tent)
        can_add_family = not tent or len(self.families_list) == 0  # added: allow the tent's first family only
        self.add_family_button.setVisible(can_add_family)
        self.new_family.setVisible(can_add_family)
        self.family_search.clear()
        if tent and len(self.families_list) > 1:
            self.occupancy_label.setText("Tent setup allows one family. Remove extra families before saving.")

    def _load(self):
        unit = next((u for u in self.dm.units() if u["id"] == self.uid), None)
        if not unit: self.reject(); return
        self.location.setText(unit["location"]); self.modality.setCurrentText(unit["modality"])
        self.capacity.setValue(unit["capacity"])
        self.families_list = self.dm.families(self.uid)

    def _refresh_family_table(self, *_):
        query = self.family_search.text().strip().casefold()
        visible = [f for f in self.families_list if query in f.get("family_name", "").casefold()
                   or query in f.get("barangay", "").casefold()]
        self.family_table.setRowCount(len(visible))
        total = sum(len(f.get("members", [])) for f in self.families_list)
        self.occupancy_label.setText(f"Total occupants: {total} / {self.capacity.value()} capacity · {len(self.families_list)} families")
        for row, family in enumerate(visible):
            name = QTableWidgetItem(family.get("family_name", "")); name.setData(Qt.ItemDataRole.UserRole, family["id"])
            name.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  # added: center family names
            self.family_table.setItem(row, 0, name)
            barangay = QTableWidgetItem(family.get("barangay", "")); barangay.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.family_table.setItem(row, 1, barangay)  # added: family-level barangay
            members = QTableWidgetItem(str(len(family.get("members", []))))
            members.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.family_table.setItem(row, 2, members)
            remove = QPushButton("Remove"); remove.clicked.connect(lambda _, fid=family["id"]: self._remove_family(fid))
            self.family_table.setCellWidget(row, 3, remove)

    def _select_family_row(self, row, _column):
        item = self.family_table.item(row, 0)
        if item: self._select_family(item.data(Qt.ItemDataRole.UserRole))

    def _select_family(self, family_id):
        if self.selected_family_id and self.selected_family_id != family_id:
            self._sync_selected_family()
        self.selected_family_id = family_id
        family = next((f for f in self.families_list if f["id"] == family_id), None)
        if not family: self.member_box.setEnabled(False); return
        self.member_box.setEnabled(True); self.family_name.setText(family.get("family_name", ""))
        inherited_barangay = next((m.get("barangay", "") for m in family.get("members", []) if m.get("barangay")), "")
        self.family_barangay.setText(family.get("barangay", inherited_barangay))  # added: migrate an existing shared barangay
        self._refresh_member_table()

    def _refresh_member_table(self):
        family = next((f for f in self.families_list if f["id"] == self.selected_family_id), None)
        members = family.get("members", []) if family else []
        self.member_table.setRowCount(len(members))
        for row, member in enumerate(members):
            for col, value in enumerate((member.get("name", ""), member.get("age", ""))):
                item = QTableWidgetItem(str(value)); item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.member_table.setItem(row, col, item)
    

    def _sync_selected_family(self):
        family = next((f for f in self.families_list if f["id"] == self.selected_family_id), None)
        if not family: return
        family["family_name"] = self.family_name.text().strip()
        family["barangay"] = self.family_barangay.text().strip()  # added: save barangay once on the family
        for row, member in enumerate(family.get("members", [])):
            member["name"] = self.member_table.item(row, 0).text().strip() if self.member_table.item(row, 0) else ""
            member["age"] = self.member_table.item(row, 1).text().strip() if self.member_table.item(row, 1) else ""

    def _add_family(self):
        name = self.new_family.text().strip()
        if not name: QMessageBox.warning(self, "Family name required", "Enter a family name first."); return
        if self.modality.currentText() == "Tent" and self.families_list:
            QMessageBox.warning(self, "Tent limit", "A tent can contain only one family."); return
        self._sync_selected_family()
        family = {"id": uuid.uuid4().hex[:12], "family_name": name, "barangay": "", "members": []}  # added
        self.families_list.append(family); self.new_family.clear()
        self.family_search.clear(); self._refresh_family_table()
        self._modality_changed(self.modality.currentText())  # added: hide add controls after the tent's first family
        self._select_family(family["id"])

    def _remove_family(self, family_id):
        if family_id == self.selected_family_id:
            self._sync_selected_family()
        self.families_list = [f for f in self.families_list if f["id"] != family_id]
        self.selected_family_id = None; self._refresh_family_table()
        self._modality_changed(self.modality.currentText())  # added: allow one replacement family in an empty tent
        if self.families_list: self._select_family(self.families_list[0]["id"])
        else: self.member_box.setEnabled(False)

    def _add_member(self):
        self._sync_selected_family()
        name = self.member_name.text().strip()
        if not name: QMessageBox.warning(self, "Name required", "Enter the member's full name."); return
        family = next(f for f in self.families_list if f["id"] == self.selected_family_id)
        if sum(len(f.get("members", [])) for f in self.families_list) >= self.capacity.value():
            QMessageBox.warning(self, "Capacity exceeded", "This unit has reached its maximum capacity."); return
        age = self.member_age.text().strip()
        if not age:
            QMessageBox.warning(self, "Member details required", "Enter the member's age."); return
        family["members"].append({"id": uuid.uuid4().hex[:12], "name": name, "age": age})
        self.member_name.clear(); self.member_age.clear()
        self._refresh_member_table(); self._refresh_family_table()

    def _add_member_batch(self):
        family = next((f for f in self.families_list if f["id"] == self.selected_family_id), None)
        if not family:
            QMessageBox.information(self, "Select a family", "Select or add a family before adding members.")
            return
        lines = [line.strip() for line in self.member_batch.toPlainText().splitlines() if line.strip()]
        if not lines:
            QMessageBox.information(self, "List is empty", "Enter one person per line as Full Name, Age.")
            return
        parsed, invalid = [], []
        for line_no, line in enumerate(lines, start=1):
            parts = line.rsplit(",", 1)
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip().isdigit():
                invalid.append(str(line_no)); continue
            age = int(parts[1].strip())
            if age > 120:
                invalid.append(str(line_no)); continue
            parsed.append({"id": uuid.uuid4().hex[:12], "name": parts[0].strip(), "age": str(age)})
        remaining = self.capacity.value() - sum(len(f.get("members", [])) for f in self.families_list)
        if len(parsed) > remaining:
            QMessageBox.warning(self, "Capacity exceeded", f"Only {remaining} more member(s) fit in this unit.")
            return
        if not parsed:
            QMessageBox.warning(self, "Check the list", "Each line must be Full Name, Age (0–120).")
            return
        self._sync_selected_family()
        family["members"].extend(parsed)
        self.member_batch.clear()
        self._refresh_member_table(); self._refresh_family_table()
        if invalid:
            QMessageBox.warning(self, "Some lines were skipped",
                                "Added valid entries. Check line(s): " + ", ".join(invalid))

    def _remove_member(self):
        row = self.member_table.currentRow()
        family = next((f for f in self.families_list if f["id"] == self.selected_family_id), None)
        if family and 0 <= row < len(family["members"]):
            self._sync_selected_family()
            removed = family["members"].pop(row)
            self._refresh_member_table(); self._refresh_family_table()

    def save(self):
        self._sync_selected_family()
        if not self.location.text().strip(): QMessageBox.warning(self, "Cannot save", "Enter the unit location."); return
        if self.modality.currentText() == "Tent" and len(self.families_list) > 1:
            QMessageBox.warning(self, "Tent limit", "A tent can contain one family. Remove the extra families first."); return
        if any(not f.get("family_name", "").strip() for f in self.families_list):
            QMessageBox.warning(self, "Family name required", "Every family needs a name."); return
        selected_family = next((f for f in self.families_list if f["id"] == self.selected_family_id), None)
        if self.families_list and not selected_family:
            QMessageBox.warning(self, "Select a family", "Select the family you want to save."); return
        if selected_family and not selected_family.get("barangay", "").strip():
            QMessageBox.warning(self, "Barangay required", "Enter the barangay for this family."); return  # added
        if selected_family and (not selected_family.get("members") or any(
                not m.get("name", "").strip() or not str(m.get("age", "")).strip()
                for m in selected_family.get("members", []))):
            QMessageBox.warning(self, "Member details required", "This family needs at least one member, and each member needs a full name and age."); return  # added: validate only the family being saved
        total = sum(len(f.get("members", [])) for f in self.families_list)
        if total > self.capacity.value(): QMessageBox.warning(self, "Capacity exceeded", "Member count is higher than unit capacity."); return
        fields = {"location": self.location.text().strip(), "modality": self.modality.currentText(),
                  "capacity": self.capacity.value(), "families": self.families_list, "headcount": total,
                  "family_name": ", ".join(f["family_name"] for f in self.families_list)}
        if self.is_new:
            self.uid = self.dm.add_unit(fields["location"], fields["modality"], fields["capacity"], *self.pos, "", 0)
            self.dm.update_unit(self.uid, fields)
        else:
            self.dm.update_unit(self.uid, fields)
        self.accept()

    def delete(self):
        if QMessageBox.question(self, "Delete unit", f"Delete {self.uid} and its records?") == QMessageBox.StandardButton.Yes:
            self.dm.delete_unit(self.uid); self.accept()
            self.dm.delete_unit(self.uid); self.accept()
