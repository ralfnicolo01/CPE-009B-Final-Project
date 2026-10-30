"""Edit section for food stock levels and the DSWD resupply cycle."""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QGroupBox, QLabel, QSpinBox, QPushButton, QMessageBox
import config as cfg
from widgets import label, scroll_page


class EditTab(QWidget):
    data_changed = pyqtSignal()

    def __init__(self, dm):
        super().__init__()
        self.dm = dm
        root = scroll_page(self)
        box = QGroupBox("Food Stocks")
        grid = QGridLayout(box); grid.setVerticalSpacing(8)
        for col, heading in enumerate(("Item", "Current stock", "Maximum (bar scale)")):
            grid.addWidget(label(heading, "head"), 0, col)
        self.stock_spins = {}
        for row, (key, text) in enumerate(cfg.STOCK_ITEMS.items(), start=1):
            current, maximum = QSpinBox(), QSpinBox()
            for spin in (current, maximum): spin.setRange(0, 1_000_000)
            grid.addWidget(QLabel(text), row, 0); grid.addWidget(current, row, 1); grid.addWidget(maximum, row, 2)
            self.stock_spins[key] = (current, maximum)
        row = len(cfg.STOCK_ITEMS) + 1
        self.cycle = QSpinBox(); self.cycle.setRange(1, 14); self.cycle.setSuffix(" days")
        save = QPushButton("Save stocks"); save.clicked.connect(self.save_stock)
        grid.addWidget(QLabel("DSWD relief pack resupply cycle"), row, 0); grid.addWidget(self.cycle, row, 1)
        grid.addWidget(save, row + 1, 2)
        for col, stretch in enumerate((2, 1, 1)): grid.setColumnStretch(col, stretch)
        root.addWidget(box); root.addStretch()
        self.reload()

    def reload(self):
        stock = self.dm.stock()
        for key, (current, maximum) in self.stock_spins.items():
            current.setValue(stock[key]["qty"]); maximum.setValue(stock[key]["max"])
        self.cycle.setValue(self.dm.cycle_days())

    def save_stock(self):
        for key, (current, maximum) in self.stock_spins.items():
            if current.value() > maximum.value(): maximum.setValue(current.value())
            self.dm.set_stock(key, current.value(), maximum.value())
        self.dm.set_cycle(self.cycle.value())
        self.data_changed.emit()
        QMessageBox.information(self, "Saved", "Food stocks updated.")
