"""Edit section: food stocks + shelter layout grid (add / move / edit / delete units)."""
import config as cfg
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel,
                             QSpinBox, QPushButton, QMessageBox)
from widgets import GridBoard, label, scroll_page
from unit_dialog import UnitDialog

class EditTab(QWidget):
    data_changed = pyqtSignal()

    def __init__(self, dm):
        super().__init__()
        self.dm = dm
        root = scroll_page(self)

        # ---- food stocks ----
        sbox = QGroupBox("Food Stocks")
        g = QGridLayout(sbox); g.setVerticalSpacing(8)
        for c, h in enumerate(("Item", "Current stock", "Maximum (bar scale)")):
            g.addWidget(label(h, "head"), 0, c)
        self.stock_spins = {}
        for r, (key, text) in enumerate(cfg.STOCK_ITEMS.items(), start=1):
            q, m = QSpinBox(), QSpinBox()
            for s in (q, m):
                s.setRange(0, 1_000_000)
            g.addWidget(QLabel(text), r, 0); g.addWidget(q, r, 1); g.addWidget(m, r, 2)
            self.stock_spins[key] = (q, m)
        n = len(cfg.STOCK_ITEMS) + 1
        self.cycle = QSpinBox(); self.cycle.setRange(1, 14); self.cycle.setSuffix(" days")
        save_stock = QPushButton("Save stocks"); save_stock.clicked.connect(self.save_stock)
        g.addWidget(QLabel("DSWD relief pack resupply cycle"), n, 0); g.addWidget(self.cycle, n, 1)
        g.addWidget(save_stock, n + 1, 2)
        for c, s in enumerate((2, 1, 1)):
            g.setColumnStretch(c, s)
        root.addWidget(sbox)

        # ---- layout grid ----
        lbox = QGroupBox("Shelter Layout")
        ll = QVBoxLayout(lbox)
        top = QHBoxLayout()
        self.cols, self.rows = QSpinBox(), QSpinBox()
        for s in (self.cols, self.rows):
            s.setRange(1, 12)
        apply_btn = QPushButton("Apply size"); apply_btn.setProperty("variant", "secondary")
        apply_btn.clicked.connect(self.apply_grid)
        for w in (QLabel("Columns:"), self.cols, QLabel("Rows:"), self.rows, apply_btn):
            top.addWidget(w)
        top.addStretch()
        ll.addLayout(top)
        ll.addWidget(label("Click an empty cell to add a unit  ·  Drag a unit to move it "
                           "(dropping on another unit swaps them)  ·  Double-click a unit to edit or delete it",
                           "hint"))
        self.board = GridBoard(editable=True)
        self.board.slot_clicked.connect(self.add_at)
        self.board.unit_activated.connect(self.edit_unit)
        self.board.unit_moved.connect(self.move_unit)
        ll.addWidget(self.board)
        root.addWidget(lbox)
        root.addStretch()
        self.reload()

    # ---------- loading ----------
    def reload(self):
        stock = self.dm.stock()
        for k, (q, m) in self.stock_spins.items():
            q.setValue(stock[k]["qty"]); m.setValue(stock[k]["max"])
        self.cycle.setValue(self.dm.cycle_days())
        self.load_units()

    def load_units(self):
        cols, rows = self.dm.grid_size()
        self.cols.setValue(cols); self.rows.setValue(rows)
        self.board.set_layout(self.dm.units(), self.dm.today_state(), cols, rows)

    def _changed(self):
        self.load_units()
        self.data_changed.emit()

    # ---------- actions ----------
    def save_stock(self):
        for k, (q, m) in self.stock_spins.items():
            if q.value() > m.value():
                m.setValue(q.value())
            self.dm.set_stock(k, q.value(), m.value())
        self.dm.set_cycle(self.cycle.value())
        self.data_changed.emit()
        QMessageBox.information(self, "Saved", "Food stocks updated.")

    def apply_grid(self):
        ok, msg = self.dm.set_grid(self.cols.value(), self.rows.value())
        if not ok:
            QMessageBox.warning(self, "Cannot resize", msg)
        self._changed()

    def add_at(self, col, row):
        UnitDialog(self.dm, None, self, pos=(col, row)).exec()
        self._changed()

    def edit_unit(self, uid):
        UnitDialog(self.dm, uid, self, can_delete=True).exec()
        self._changed()

    def move_unit(self, uid, col, row):
        self.dm.move_unit(uid, col, row)
        QTimer.singleShot(0, self._changed)   # rebuild after the drag has fully finished