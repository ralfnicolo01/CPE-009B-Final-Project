"""Dashboard: summary, food stock, daily logs, and the shelter layout grid (same layout as Edit tab)."""
import config as cfg
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel,
                             QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView)
from widgets import SummaryCard, StockBar, GridBoard, VACANT, PARTIAL, FULL, label, scroll_page
from unit_dialog import UnitDialog


class DashboardTab(QWidget):
    def __init__(self, dm):
        super().__init__()
        self.dm = dm
        root = scroll_page(self)

        # 1. summary cards
        row = QHBoxLayout(); row.setSpacing(14)
        self.c_total, self.c_occ, self.c_vac = (SummaryCard("Total Evacuees", "people"),
                                                SummaryCard("Occupied Units", "house"),
                                                SummaryCard("Vacant Units", "house_empty"))
        for c in (self.c_total, self.c_occ, self.c_vac):
            row.addWidget(c)
        root.addLayout(row)

        # 2. food stock
        box = QGroupBox("Food Stock Left")
        g = QGridLayout(box); g.setHorizontalSpacing(30); g.setVerticalSpacing(14)
        self.bars = {k: StockBar(text) for k, text in cfg.STOCK_ITEMS.items()}
        for i, bar in enumerate(self.bars.values()):
            g.addWidget(bar, i // 2, i % 2)
        root.addWidget(box)

        # 3. activity log (dropdown of dates)
        lbox = QGroupBox("Activity Log")
        ll = QVBoxLayout(lbox)
        top = QHBoxLayout()
        self.dates = QComboBox(); self.dates.setMinimumWidth(160)
        self.dates.currentTextChanged.connect(self.load_logs)
        top.addWidget(QLabel("Date:")); top.addWidget(self.dates); top.addStretch()
        ll.addLayout(top)
        self.log_table = t = QTableWidget(0, 4)
        t.setHorizontalHeaderLabels(["Time", "Unit", "Activity", "Details"])
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        t.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        for c in (0, 1, 2):
            t.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        t.setFixedHeight(150)
        ll.addWidget(t)
        root.addWidget(lbox)

        # 4. shelter layout (same grid as the Edit tab)
        sbox = QGroupBox("Shelter Unit Status  (double-click a unit to edit it / update food status)")
        sl = QVBoxLayout(sbox)
        sl.addWidget(label(f'<span style="color:{VACANT}">●</span> Vacant &nbsp; '
                           f'<span style="color:{PARTIAL}">●</span> Partly occupied &nbsp; '
                           f'<span style="color:{FULL}">●</span> Full &nbsp;&nbsp;|&nbsp;&nbsp; '
                           'B / L / D = Breakfast / Lunch / Dinner received', "hint", rich=True))
        self.board = GridBoard(editable=False)
        self.board.unit_activated.connect(self.open_unit)
        sl.addWidget(self.board)
        root.addWidget(sbox)
        root.addStretch()
        self.refresh()

    def refresh(self):
        units, state, stock = self.dm.units(), self.dm.today_state(), self.dm.stock()
        by_mod = lambda pred: " · ".join(
            f"{m} {sum(1 for u in units if u['modality'] == m and pred(u))}" for m in cfg.MODALITIES)
        n_occ = sum(1 for u in units if u["headcount"] > 0)
        self.c_total.set(sum(u["headcount"] for u in units),
                         f"{len(units)} units · capacity {sum(u['capacity'] for u in units)}")
        self.c_occ.set(n_occ, by_mod(lambda u: u["headcount"] > 0))
        self.c_vac.set(len(units) - n_occ, by_mod(lambda u: u["headcount"] == 0))
        for k, bar in self.bars.items():
            if k in stock:
                bar.set_values(stock[k]["qty"], stock[k]["max"])
        self.board.set_layout(units, state, *self.dm.grid_size())

        current = self.dates.currentText()
        self.dates.blockSignals(True)
        self.dates.clear(); self.dates.addItems(self.dm.log_dates())
        if current:
            self.dates.setCurrentText(current)
        self.dates.blockSignals(False)
        self.load_logs()

    def load_logs(self, *_):
        rows = self.dm.logs_for(self.dates.currentText())
        self.log_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate((row["timestamp"][11:19], row["unit_id"], row["action"], row["details"])):
                self.log_table.setItem(r, c, QTableWidgetItem(val))

    def open_unit(self, uid):
        UnitDialog(self.dm, uid, self).exec()
        self.refresh()
