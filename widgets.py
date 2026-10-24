"""Reusable UI pieces: icons, unit cards, layout grid board, stock bars, summary cards."""
import config as cfg
from PyQt6.QtCore import Qt, QRectF, QPointF, QMimeData, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QPolygonF, QFontMetrics, QDrag
from PyQt6.QtWidgets import (QApplication, QWidget, QFrame, QLabel, QVBoxLayout,
                             QProgressBar, QGridLayout)

VACANT, PARTIAL, FULL = "#7bc496", "#f2b441", "#e56b5d"


def occupancy_color(head, cap):
    if head <= 0:
        return VACANT
    return FULL if head >= cap else PARTIAL


class UnitIcon(QWidget):
    """Tent / classroom icon drawn with QPainter (no image files needed)."""
    def __init__(self, modality, color, size=64):
        super().__init__()
        self.modality, self.color = modality, QColor(color)
        self.setFixedSize(size, size)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(QPen(self.color.darker(130), 2))
        p.setBrush(self.color)
        white = QColor("white")
        if self.modality == "Tent":
            path = QPainterPath()
            path.moveTo(w * .5, h * .12); path.lineTo(w * .93, h * .88)
            path.lineTo(w * .07, h * .88); path.closeSubpath()
            p.drawPath(path)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(white)
            door = QPainterPath()
            door.moveTo(w * .5, h * .45); door.lineTo(w * .65, h * .88)
            door.lineTo(w * .35, h * .88); door.closeSubpath()
            p.drawPath(door)
        else:
            p.drawRoundedRect(QRectF(w * .12, h * .38, w * .76, h * .5), 3, 3)
            p.drawPolygon(QPolygonF([QPointF(w * .05, h * .4), QPointF(w * .5, h * .12),
                                     QPointF(w * .95, h * .4)]))
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(white)
            p.drawRect(QRectF(w * .2, h * .5, w * .16, h * .14))
            p.drawRect(QRectF(w * .64, h * .5, w * .16, h * .14))
            p.drawRect(QRectF(w * .42, h * .62, w * .16, h * .26))


class UnitCard(QFrame):
    W, H = 164, 182
    activated = pyqtSignal(str)

    def __init__(self, unit, state, draggable=False):
        super().__init__()
        self.setObjectName("unitCard")
        self.uid = unit["id"]
        self.draggable = draggable
        self._press = None
        self.setFixedSize(self.W, self.H)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8); lay.setSpacing(3)

        occupied = unit["headcount"] > 0
        name = unit["family_name"] if occupied and unit["family_name"] else "Vacant"
        hint = ("Drag to move  ·  Double-click to edit" if draggable
                else "Double-click to edit unit / update food status")
        self.setToolTip(f"{name}\n{unit['location']}\n{hint}")
        name_lbl = QLabel(QFontMetrics(self.font()).elidedText(
            name, Qt.TextElideMode.ElideRight, self.W - 24))
        name_lbl.setStyleSheet("font-weight:700;" + ("" if occupied else "color:#9ca3af;"))

        icon = UnitIcon(unit["modality"], occupancy_color(unit["headcount"], unit["capacity"]))
        count = QLabel(f"{unit['headcount']}/{unit['capacity']}")
        count.setStyleSheet("font-weight:600;")
        id_lbl = QLabel(unit["id"])
        id_lbl.setStyleSheet("color:#9ca3af;font-size:11px;")

        def dot(ok):
            return f'<span style="color:{"#22a06b" if ok else "#c3c9d1"}">●</span>'
        meals = state["meals"]
        txt = " ".join(f"{m[0]}{dot(meals[m]['status'] == 'Received')}" for m in cfg.MEALS)
        txt += f" · DSWD{dot(state['dswd']['received'])}"
        status = QLabel(txt)
        status.setTextFormat(Qt.TextFormat.RichText)
        status.setStyleSheet("font-size:10px;color:#6b7280;")

        for wdg in (name_lbl, count, id_lbl, status):
            wdg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(name_lbl)
        lay.addWidget(icon, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(count); lay.addWidget(id_lbl); lay.addWidget(status)

    # --- mouse: double-click = open dialog, drag = move (edit layout only) ---
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press = e.position().toPoint()
        e.accept()

    def mouseMoveEvent(self, e):
        if (self.draggable and self._press is not None
                and e.buttons() & Qt.MouseButton.LeftButton
                and (e.position().toPoint() - self._press).manhattanLength()
                >= QApplication.startDragDistance()):
            drag = QDrag(self)
            mime = QMimeData(); mime.setText(self.uid)
            drag.setMimeData(mime)
            drag.setPixmap(self.grab()); drag.setHotSpot(self._press)
            self._press = None
            drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, e):
        self._press = None
        e.accept()

    def mouseDoubleClickEvent(self, e):
        self._press = None
        self.activated.emit(self.uid)


class Slot(QFrame):
    """One grid cell: gray placeholder when empty, holds a UnitCard when occupied."""
    clicked = pyqtSignal(int, int)          # empty cell clicked (edit mode)
    dropped = pyqtSignal(str, int, int)     # unit id dropped here (edit mode)

    def __init__(self, col, row, editable):
        super().__init__()
        self.setObjectName("slot")
        self.col, self.row, self.editable = col, row, editable
        self.card = None
        self.setFixedSize(UnitCard.W, UnitCard.H)
        self.lay = QVBoxLayout(self); self.lay.setContentsMargins(0, 0, 0, 0)
        self.setAcceptDrops(editable)
        self.plus = None
        if editable:
            self.plus = QLabel("+")
            self.plus.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.plus.setStyleSheet("font-size:30px;color:#9ca3af;")
            self.setToolTip("Click to add a unit here")
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.lay.addWidget(self.plus)

    def set_card(self, card):
        self.card = card
        if self.plus:
            self.plus.hide()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setToolTip("")
        self.setProperty("filled", True)
        self.lay.addWidget(card)

    def _hover(self, on):
        self.setProperty("hover", on)
        self.style().unpolish(self); self.style().polish(self)

    def mousePressEvent(self, e):
        if self.editable and self.card is None and e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.col, self.row)

    def dragEnterEvent(self, e):
        if e.mimeData().hasText():
            e.acceptProposedAction(); self._hover(True)

    def dragLeaveEvent(self, e):
        self._hover(False)

    def dropEvent(self, e):
        self._hover(False)
        e.acceptProposedAction()
        self.dropped.emit(e.mimeData().text(), self.col, self.row)


class GridBoard(QWidget):
    """Fixed cols x rows grid. Same widget is used in the Edit tab (editable) and Dashboard (view)."""
    SP = 12
    unit_activated = pyqtSignal(str)
    slot_clicked = pyqtSignal(int, int)
    unit_moved = pyqtSignal(str, int, int)

    def __init__(self, editable=False):
        super().__init__()
        self.editable = editable
        self.grid = QGridLayout(self)
        self.grid.setSpacing(self.SP); self.grid.setContentsMargins(6, 6, 6, 6)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

    def set_layout(self, units, state, cols, rows):
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.setParent(None); w.deleteLater()
        at = {(u["col"], u["row"]): u for u in units}
        for r in range(rows):
            for c in range(cols):
                slot = Slot(c, r, self.editable)
                slot.clicked.connect(self.slot_clicked)
                slot.dropped.connect(self.unit_moved)
                u = at.get((c, r))
                if u:
                    card = UnitCard(u, state[u["id"]], draggable=self.editable)
                    card.activated.connect(self.unit_activated)
                    slot.set_card(card)
                self.grid.addWidget(slot, r, c)


class StockBar(QWidget):
    def __init__(self, label):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(4)
        self.title = QLabel(label)
        self.title.setStyleSheet("font-weight:600;")
        self.value = QLabel()
        self.value.setStyleSheet("color:#6b7280;")
        self.bar = QProgressBar()
        self.bar.setTextVisible(False); self.bar.setFixedHeight(10)
        lay.addWidget(self.title); lay.addWidget(self.bar); lay.addWidget(self.value)

    def set_values(self, qty, mx):
        mx = max(mx, 1)
        pct = qty / mx
        color = "#22a06b" if pct > .5 else "#f2b441" if pct > .2 else "#e56b5d"
        self.value.setText(f"{qty:,} / {mx:,} left  ({pct:.0%})")
        self.bar.setRange(0, mx); self.bar.setValue(min(qty, mx))
        self.bar.setStyleSheet(
            "QProgressBar{background:#eceff3;border:none;border-radius:5px;}"
            f"QProgressBar::chunk{{background:{color};border-radius:5px;}}")


class SummaryCard(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12); lay.setSpacing(2)
        t = QLabel(title); t.setStyleSheet("color:#6b7280;font-weight:600;")
        self.big = QLabel("0"); self.big.setStyleSheet("font-size:30px;font-weight:700;")
        self.sub = QLabel(""); self.sub.setStyleSheet("color:#6b7280;")
        lay.addWidget(t); lay.addWidget(self.big); lay.addWidget(self.sub)

    def set(self, big, sub):
        self.big.setText(str(big)); self.sub.setText(sub)
