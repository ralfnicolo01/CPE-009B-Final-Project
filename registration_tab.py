"""Registration page for shelter units, families, and household members."""
import config as cfg
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QSpinBox,
    QPushButton, QMessageBox, QLineEdit, QInputDialog, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from widgets import GridBoard, label, scroll_page
from unit_dialog import UnitDialog


class RegistrationTab(QWidget):
    data_changed = pyqtSignal()

    def __init__(self, dm):
        super().__init__()
        self.dm = dm
        root = scroll_page(self)

        box = QGroupBox("Shelter and family registration")
        layout = QVBoxLayout(box)
        layout.addWidget(QLabel(
            "Select an empty cell to choose the setup modality and register a family. "
            "Double-click an existing unit to add or update its family members."
        ))

        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "Find a unit, family, barangay, or member name…"
        )
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_registration)
        self.search.returnPressed.connect(self.search_registration)
        search_row.addWidget(self.search, 1)
        search_row.addWidget(self.search_button)
        layout.addLayout(search_row)

        controls = QHBoxLayout()
        self.cols, self.rows = QSpinBox(), QSpinBox()
        for spin in (self.cols, self.rows):
            spin.setRange(1, 12)

        apply_button = QPushButton("Apply layout size")
        apply_button.setProperty("variant", "secondary")
        apply_button.clicked.connect(self.apply_grid)

        for widget in (
            QLabel("Columns"), self.cols,
            QLabel("Rows"), self.rows,
            apply_button,
        ):
            controls.addWidget(widget)
        controls.addStretch()
        layout.addLayout(controls)

        layout.addWidget(label(
            "Click an empty cell to register a shelter unit · Drag a unit to move it · "
            "Double-click a unit to register families and members · "
            "B / L / D and DSWD dots show receipt status",
            "hint",
        ))

        self.board = GridBoard(editable=True, show_distribution=True)
        self.board.slot_clicked.connect(self.add_at)
        self.board.unit_activated.connect(self.edit_unit)
        self.board.unit_moved.connect(self.move_unit)
        layout.addWidget(self.board)
        root.addWidget(box)

        history = QGroupBox("Activity History")
        history_layout = QVBoxLayout(history)
        date_row = QHBoxLayout()

        self.dates = QComboBox()
        self.dates.setMinimumWidth(160)
        self.dates.currentTextChanged.connect(self.load_logs)

        self.log_filter = QComboBox()
        self.log_filter.addItems(("All activity", "Distribution history"))
        self.log_filter.currentTextChanged.connect(self.load_logs)

        date_row.addWidget(QLabel("Date:"))
        date_row.addWidget(self.dates)
        date_row.addWidget(QLabel("Show:"))
        date_row.addWidget(self.log_filter)
        date_row.addStretch()
        history_layout.addLayout(date_row)

        self.log_table = QTableWidget(0, 4)
        self.log_table.setHorizontalHeaderLabels(
            ["Time", "Unit", "Activity", "Details"]
        )
        self.log_table.verticalHeader().hide()
        self.log_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.log_table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self.log_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        for col in (0, 1, 2):
            self.log_table.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.ResizeMode.ResizeToContents
            )
        self.log_table.setMinimumHeight(150)
        history_layout.addWidget(self.log_table)
        root.addWidget(history)
        root.addStretch()

        self.refresh()

    def refresh(self):
        cols, rows = self.dm.grid_size()
        self.cols.setValue(cols)
        self.rows.setValue(rows)
        self.board.set_layout(
            self.dm.units(),
            self.dm.today_state(),
            cols,
            rows,
        )

        current_date = self.dates.currentText()
        self.dates.blockSignals(True)
        self.dates.clear()
        self.dates.addItems(self.dm.log_dates())
        if current_date:
            self.dates.setCurrentText(current_date)
        self.dates.blockSignals(False)
        self.load_logs()

    def load_logs(self, *_):
        rows = (
            self.dm.logs_for(self.dates.currentText())
            if self.dates.currentText()
            else []
        )

        if self.log_filter.currentText() == "Distribution history":
            distribution_actions = {
                "Meal update",
                "DSWD family pack",
                "DSWD pack",
            }
            rows = [
                record for record in rows
                if record["action"] in distribution_actions
            ]

        self.log_table.setRowCount(len(rows))
        for row_index, record in enumerate(rows):
            values = (
                record["timestamp"][11:19],
                record["unit_id"],
                record["action"],
                record["details"],
            )
            for col, value in enumerate(values):
                self.log_table.setItem(
                    row_index, col, QTableWidgetItem(value)
                )

    def _changed(self):
        self.refresh()
        self.data_changed.emit()

    def apply_grid(self):
        ok, msg = self.dm.set_grid(
            self.cols.value(),
            self.rows.value(),
        )
        if not ok:
            QMessageBox.warning(self, "Cannot resize", msg)
        self._changed()

    def add_at(self, col, row):
        UnitDialog(
            self.dm,
            None,
            self,
            pos=(col, row),
        ).exec()
        self._changed()

    def edit_unit(self, uid):
        UnitDialog(
            self.dm,
            uid,
            self,
            can_delete=True,
        ).exec()
        self._changed()

    def search_registration(self):
        query = self.search.text().strip().casefold()
        if not query:
            QMessageBox.information(
                self,
                "Search",
                "Enter a unit, family, barangay, or member name.",
            )
            return

        matches = []
        for unit in self.dm.units():
            if (
                query in unit["id"].casefold()
                or query in unit["location"].casefold()
            ):
                matches.append((unit, None))

            for family in self.dm.families(unit["id"]):
                family_text = (
                    f"{family.get('family_name', '')} "
                    f"{family.get('barangay', '')}"
                ).casefold()
                matching_members = [
                    member
                    for member in family.get("members", [])
                    if (
                        query in member.get("name", "").casefold()
                        or query in str(member.get("age", ""))
                    )
                ]
                if query in family_text or matching_members:
                    matches.append((unit, family["id"]))

        unique_matches = {}
        for unit, family_id in matches:
            unique_matches[(unit["id"], family_id)] = (unit, family_id)
        matches = list(unique_matches.values())

        if not matches:
            QMessageBox.information(
                self,
                "No matches",
                "No matching unit, family, barangay, or member was found.",
            )
            return

        choices = []
        for unit, family_id in matches:
            family = (
                next(
                    (
                        item for item in self.dm.families(unit["id"])
                        if item["id"] == family_id
                    ),
                    None,
                )
                if family_id
                else None
            )
            if family:
                choices.append(f"{unit['id']} — {family['family_name']}")
            else:
                choices.append(f"{unit['id']} — {unit['location']}")

        selected = choices[0]
        if len(choices) > 1:
            selected, ok = QInputDialog.getItem(
                self,
                "Choose a match",
                "Matching registration:",
                choices,
                0,
                False,
            )
            if not ok:
                return

        unit, family_id = matches[choices.index(selected)]
        UnitDialog(
            self.dm,
            unit["id"],
            self,
            can_delete=True,
            initial_family_id=family_id,
        ).exec()
        self._changed()

    def move_unit(self, uid, col, row):
        self.dm.move_unit(uid, col, row)
        QTimer.singleShot(0, self._changed)
