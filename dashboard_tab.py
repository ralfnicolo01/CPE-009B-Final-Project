"""Dashboard: summary, food stock, daily logs, and the shelter layout grid (same layout as Edit tab)."""
import config as cfg
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel,
                             QComboBox, QTableWidget, QTableWidgetItem, QScrollArea,
                             QHeaderView, QAbstractItemView)
from widgets import SummaryCard, StockBar, GridBoard, VACANT, PARTIAL, FULL
from unit_dialog import UnitDialog


class DashboardTab(QWidget):
    def __init__(self, dm):
        super().__init__()
        self.dm = dm
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        page = QWidget(); page.setObjectName("page"); scroll.setWidget(page)
        outer.addWidget(scroll)
        root = QVBoxLayout(page); root.setContentsMargins(20, 12, 20, 20); root.setSpacing(14)

        # 1. summary cards
        row = QHBoxLayout(); row.setSpacing(12)
        self.c_total, self.c_occ, self.c_vac = (SummaryCard("Total Evacuees"),
                                                SummaryCard("Occupied Units"),
                                                SummaryCard("Vacant Units"))
        for c in (self.c_total, self.c_occ, self.c_vac):
            row.addWidget(c)
        root.addLayout(row)

        # 2. food stock
        box = QGroupBox("Food Stock Left")
        g = QGridLayout(box); g.setHorizontalSpacing(30); g.setVerticalSpacing(14)
        self.bars = {}
        for i, (key, label) in enumerate(cfg.STOCK_ITEMS.items()):
            self.bars[key] = StockBar(label)
            g.addWidget(self.bars[key], i // 2, i % 2)
        root.addWidget(box)

        # 3. activity log (dropdown of dates)
        lbox = QGroupBox("Activity Log")
        ll = QVBoxLayout(lbox)
        top = QHBoxLayout()
        top.addWidget(QLabel("Date:"))
        self.dates = QComboBox(); self.dates.setMinimumWidth(160)
        self.dates.currentTextChanged.connect(self.load_logs)
        top.addWidget(self.dates); top.addStretch()
        ll.addLayout(top)
        self.log_table = QTableWidget(0, 4)
        self.log_table.setHorizontalHeaderLabels(["Time", "Unit", "Activity", "Details"])
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.log_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        h = self.log_table.horizontalHeader()
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        for c in (0, 1, 2):
            h.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.log_table.setFixedHeight(150)
        ll.addWidget(self.log_table)
        root.addWidget(lbox)

        # 4. shelter layout (same grid as the Edit tab)
        sbox = QGroupBox("Shelter Unit Status  (double-click a unit to edit it / update food status)")
        sl = QVBoxLayout(sbox)
        legend = QLabel(f'<span style="color:{VACANT}">●</span> Vacant &nbsp; '
                        f'<span style="color:{PARTIAL}">●</span> Partly occupied &nbsp; '
                        f'<span style="color:{FULL}">●</span> Full &nbsp;&nbsp;|&nbsp;&nbsp; '
                        'B / L / D = Breakfast / Lunch / Dinner received')
        legend.setStyleSheet("color:#6b7280;font-size:12px;")
        sl.addWidget(legend)
        self.board = GridBoard(editable=False)
        self.board.unit_activated.connect(self.open_unit)
        sl.addWidget(self.board)
        root.addWidget(sbox)
        root.addStretch()
        self.refresh()

    def refresh(self):
        units, state, stock = self.dm.units(), self.dm.today_state(), self.dm.stock()

        def by_mod(pred):
            return " · ".join(f"{m} {sum(1 for u in units if u['modality'] == m and pred(u))}"
                              for m in cfg.MODALITIES)
        total = sum(u["headcount"] for u in units)
        n_occ = sum(1 for u in units if u["headcount"] > 0)
        self.c_total.set(total, f"{len(units)} units · capacity {sum(u['capacity'] for u in units)}")
        self.c_occ.set(n_occ, by_mod(lambda u: u["headcount"] > 0))
        self.c_vac.set(len(units) - n_occ, by_mod(lambda u: u["headcount"] == 0))

        for k, bar in self.bars.items():
            if k in stock:
                bar.set_values(stock[k]["qty"], stock[k]["max"])

        cols, rows = self.dm.grid_size()
        self.board.set_layout(units, state, cols, rows)

        current = self.dates.currentText()
        self.dates.blockSignals(True)
        self.dates.clear(); self.dates.addItems(self.dm.log_dates())
        if current:
            self.dates.setCurrentText(current)
        self.dates.blockSignals(False)
        self.load_logs()

    def load_logs(self, *_):
        rows = self.dm.logs_for(self.dates.currentText())
        t = self.log_table
        t.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate((row["timestamp"][11:19], row["unit_id"],
                                     row["action"], row["details"])):
                t.setItem(r, c, QTableWidgetItem(val))

    def open_unit(self, uid):
        UnitDialog(self.dm, uid, self).exec()
        self.refresh()
