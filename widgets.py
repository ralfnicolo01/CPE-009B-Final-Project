"""Reusable UI pieces: label helper, icons, unit cards, layout grid board, stock bars, summary cards."""
import config as cfg
from PyQt6.QtCore import Qt, QRectF, QPointF, QMimeData, QSize, QTimer, QPropertyAnimation, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QPolygonF, QFontMetrics, QDrag
from PyQt6.QtWidgets import (QAbstractButton, QApplication, QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
                             QProgressBar, QGridLayout, QScrollArea)

VACANT, PARTIAL, FULL = "#7bc496", "#f2b441", "#e56b5d"
CENTER = Qt.AlignmentFlag.AlignCenter


def occupancy_color(head, cap):
    return VACANT if head <= 0 else FULL if head >= cap else PARTIAL


def label(text="", role="", center=False, rich=False):
    """QLabel styled by the theme through its `role` property (see styles.py)."""
    lb = QLabel(text)
    if role:
        lb.setProperty("role", role)
    if center:
        lb.setAlignment(CENTER)
    if rich:
        lb.setTextFormat(Qt.TextFormat.RichText)
    return lb


def scroll_page(owner):
    """Make `owner` a scrollable page and return the layout to fill."""
    outer = QVBoxLayout(owner); outer.setContentsMargins(0, 0, 0, 0)
    scroll, page = QScrollArea(), QWidget()
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)  # stable width for grid fitting
    scroll.setWidgetResizable(True); page.setObjectName("page"); scroll.setWidget(page)
    outer.addWidget(scroll)
    root = QVBoxLayout(page); root.setContentsMargins(24, 8, 24, 24); root.setSpacing(16)
    return root


class ToggleSwitch(QAbstractButton):
    """Slide switch: gray when off, blue when on, with a white knob that glides across."""
    OFF, ON = QColor("#cfd6e0"), QColor("#1a82f7")

    def __init__(self, checked=False):
        super().__init__()
        self.setCheckable(True); self.setChecked(checked)
        self.setFixedSize(54, 30); self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._t = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"knob", self); self._anim.setDuration(160)
        self.toggled.connect(self._slide)

    def _slide(self, on):
        self._anim.stop(); self._anim.setStartValue(self._t); self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    knob = pyqtProperty(float, lambda self: self._t, lambda self, v: (setattr(self, "_t", v), self.update()))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setPen(Qt.PenStyle.NoPen)
        r, t = QRectF(self.rect()).adjusted(1, 1, -1, -1), self._t
        mix = lambda a, b: round(a + (b - a) * t)
        p.setBrush(QColor(mix(self.OFF.red(), self.ON.red()), mix(self.OFF.green(), self.ON.green()),
                          mix(self.OFF.blue(), self.ON.blue())))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = r.height() - 6
        x = r.left() + 3 + (r.width() - d - 6) * t
        p.setBrush(QColor(0, 0, 0, 45)); p.drawEllipse(QRectF(x, r.top() + 4, d, d))     # soft shadow
        p.setBrush(QColor("white")); p.drawEllipse(QRectF(x, r.top() + 3, d, d))


class UnitIcon(QWidget):
    """Tent / classroom icon drawn with QPainter (no image files needed)."""
    def __init__(self, modality, color, size=64):
        super().__init__()
        self.modality, self.color = modality, QColor(color)
        self.setFixedSize(size, size)

    def paintEvent(self, _):
        p, w, h = QPainter(self), self.width(), self.height()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        poly = lambda *pts: QPolygonF([QPointF(w * x, h * y) for x, y in pts])
        box = lambda x, y, bw, bh: QRectF(w * x, h * y, w * bw, h * bh)
        p.setPen(QPen(self.color.darker(130), 2)); p.setBrush(self.color)
        if self.modality == "Tent":
            p.drawPolygon(poly((.5, .12), (.93, .88), (.07, .88)))
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor("white"))
            p.drawPolygon(poly((.5, .45), (.65, .88), (.35, .88)))
        else:
            p.drawRoundedRect(box(.12, .38, .76, .5), 3, 3)
            p.drawPolygon(poly((.05, .4), (.5, .12), (.95, .4)))
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor("white"))
            for r in (box(.2, .5, .16, .14), box(.64, .5, .16, .14), box(.42, .62, .16, .26)):
                p.drawRect(r)


BASE_W, BASE_H = 164, 182      # design size of one grid cell; cards scale from this


class UnitCard(QFrame):
    activated = pyqtSignal(str)

    def __init__(self, unit, state, w=BASE_W, h=BASE_H, draggable=False):
        super().__init__()
        self.setObjectName("unitCard"); self.setFixedSize(w, h)
        self.uid, self.draggable, self._press = unit["id"], draggable, None
        s = w / BASE_W
        occupied = unit["headcount"] > 0
        name = unit["family_name"] if occupied and unit["family_name"] else "Vacant"
        hint = ("Drag to move  ·  Double-click to edit" if draggable
                else "Double-click to edit unit / update food status")
        self.setToolTip(f"{name}\n{unit['location']}\n{hint}")

        dpx = max(9, round(15 * s))     # status dots are drawn larger than the letters
        dot = lambda ok: f'<span style="color:{"#22a06b" if ok else "#9aa0ad"};font-size:{dpx}px">●</span>'
        txt = " ".join(f"{m[0]}{dot(state['meals'][m]['status'] == 'Received')}" for m in cfg.MEALS)
        txt += f" · DSWD{dot(state['dswd']['received'])}"
        elided = QFontMetrics(self.font()).elidedText(name, Qt.TextElideMode.ElideRight, int(w - 24 * s))

        lay = QVBoxLayout(self); lay.setContentsMargins(*[round(8 * s)] * 4); lay.setSpacing(round(3 * s))
        parts = [(label(elided, "name" if occupied else "nameoff", True), 13),
                 (label(f"{unit['headcount']}/{unit['capacity']}", "count", True), 13),
                 (label(unit["id"], "id", True), 11), (label(txt, "tiny", True, True), 12)]
        for lb, size in parts:                      # scale fonts with the cell
            lb.setStyleSheet(f"font-size:{max(7, round(size * s))}px;")
        icon = UnitIcon(unit["modality"], occupancy_color(unit["headcount"], unit["capacity"]), max(24, round(64 * s)))
        lay.addWidget(parts[0][0]); lay.addWidget(icon, alignment=CENTER)
        for lb, _ in parts[1:]:
            lay.addWidget(lb)
            lb.setVisible(s >= .7 or lb is parts[1][0])   # tiny cells keep only the headcount

    # --- mouse: double-click = open dialog, drag = move (edit layout only) ---
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press = e.position().toPoint()
        e.accept()

    def mouseMoveEvent(self, e):
        if (self.draggable and self._press is not None and e.buttons() & Qt.MouseButton.LeftButton
                and (e.position().toPoint() - self._press).manhattanLength() >= QApplication.startDragDistance()):
            drag, mime = QDrag(self), QMimeData()
            mime.setText(self.uid)
            drag.setMimeData(mime); drag.setPixmap(self.grab()); drag.setHotSpot(self._press)
            self._press = None
            drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, e):
        self._press = None
        e.accept()

    def mouseDoubleClickEvent(self, e):
        self._press = None
        self.activated.emit(self.uid)


class Slot(QFrame):
    """One grid cell: placeholder when empty, holds a UnitCard when occupied."""
    clicked = pyqtSignal(int, int)          # empty cell clicked (edit mode)
    dropped = pyqtSignal(str, int, int)     # unit id dropped here (edit mode)

    def __init__(self, col, row, editable, w=BASE_W, h=BASE_H):
        super().__init__()
        self.setObjectName("slot"); self.setFixedSize(w, h)
        self.col, self.row, self.editable, self.card, self.plus = col, row, editable, None, None
        self.lay = QVBoxLayout(self); self.lay.setContentsMargins(0, 0, 0, 0)
        self.setAcceptDrops(editable)
        if editable:
            self.plus = label("+", "plus", True)
            self.plus.setStyleSheet(f"font-size:{round(30 * w / BASE_W)}px;")
            self.setToolTip("Click to add a unit here")
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.lay.addWidget(self.plus)

    def set_card(self, card):
        self.card = card
        if self.plus:
            self.plus.hide()
        self.setCursor(Qt.CursorShape.ArrowCursor); self.setToolTip(""); self.setProperty("filled", True)
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
    """cols x rows grid, centered. Cells grow or shrink so the whole grid fits the window
    (width and height). Same widget is used in the Edit tab (editable) and Dashboard (view)."""
    MIN_W, SP, PAD = 56, 12, 6          # smallest cell width, cell spacing, outer padding
    unit_activated = pyqtSignal(str)
    slot_clicked = pyqtSignal(int, int)
    unit_moved = pyqtSignal(str, int, int)

    def __init__(self, editable=False):
        super().__init__()
        self.editable = editable
        self._data = self._cell = None
        self.grid = QGridLayout(self)
        self.grid.setSpacing(self.SP); self.grid.setContentsMargins(*[self.PAD] * 4)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self._timer = QTimer(self); self._timer.setSingleShot(True); self._timer.setInterval(40)
        self._timer.timeout.connect(self._refit)

    def set_layout(self, units, state, cols, rows):
        self._data = (units, state, cols, rows)
        self._build()

    def _cell_size(self):
        """Cells fill the full width of the board; the page scrolls vertically."""
        cols = self._data[2]
        cw = max(self.MIN_W, int((self.width() - 2 * self.PAD - self.SP * (cols - 1)) / cols))
        return cw, round(cw * BASE_H / BASE_W)

    def _build(self):
        units, state, cols, rows = self._data
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.setParent(None); w.deleteLater()
        self._cell = cw, ch = self._cell_size()
        at = {(u["col"], u["row"]): u for u in units}
        for r in range(rows):
            for c in range(cols):
                slot = Slot(c, r, self.editable, cw, ch)
                slot.clicked.connect(self.slot_clicked); slot.dropped.connect(self.unit_moved)
                if (u := at.get((c, r))):
                    card = UnitCard(u, state[u["id"]], cw, ch, draggable=self.editable)
                    card.activated.connect(self.unit_activated)
                    slot.set_card(card)
                self.grid.addWidget(slot, r, c)

    def _refit(self):
        if self._data and self._cell_size() != self._cell:
            self._build()

    def minimumSizeHint(self):      # let the board shrink so cells can shrink with the window
        cols = self._data[2] if self._data else 1
        return QSize(cols * self.MIN_W + (cols - 1) * self.SP + 2 * self.PAD, self.grid.minimumSize().height())

    def resizeEvent(self, e):
        super().resizeEvent(e); self._timer.start()

    def showEvent(self, e):
        super().showEvent(e); self._timer.start()


class StockBar(QWidget):
    def __init__(self, text):
        super().__init__()
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(4)
        self.value, self.bar = label(role="muted"), QProgressBar()
        self.bar.setTextVisible(False); self.bar.setFixedHeight(10)
        for w in (label(text, "bold"), self.bar, self.value):
            lay.addWidget(w)

    def set_values(self, qty, mx):
        mx = max(mx, 1)
        pct = qty / mx
        color = "#22a06b" if pct > .5 else "#f2b441" if pct > .2 else "#e56b5d"
        self.value.setText(f"{qty:,} / {mx:,} left  ({pct:.0%})")
        self.bar.setRange(0, mx); self.bar.setValue(min(qty, mx))
        self.bar.setStyleSheet(f"QProgressBar::chunk{{background:{color};border-radius:5px;}}")


class CardIcon(QWidget):
    """Summary-card icon ('people', 'house', 'house_empty') painted in the theme accent color."""
    def __init__(self, kind, size=46):
        super().__init__()
        self.kind = kind
        self.setObjectName("cardIcon"); self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

    def paintEvent(self, e):
        super().paintEvent(e)
        p, w, h = QPainter(self), self.width(), self.height()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self.palette().windowText().color()
        poly = lambda *pts: QPolygonF([QPointF(w * x, h * y) for x, y in pts])
        box = lambda x, y, bw, bh: QRectF(w * x, h * y, w * bw, h * bh)
        if self.kind == "people":
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(c)
            for cx, top, r in ((.5, .24, .11), (.27, .36, .08), (.73, .36, .08)):   # heads
                p.drawEllipse(QPointF(w * cx, h * (top + r)), w * r, w * r)
            p.drawRoundedRect(box(.3, .56, .4, .26), 6, 6)                         # shoulders
            p.drawRoundedRect(box(.12, .62, .2, .2), 4, 4)
            p.drawRoundedRect(box(.68, .62, .2, .2), 4, 4)
        else:
            filled = self.kind == "house"
            p.setPen(QPen(c, 2.4) if not filled else Qt.PenStyle.NoPen)
            p.setBrush(c if filled else Qt.BrushStyle.NoBrush)
            p.drawPolygon(poly((.22, .5), (.5, .24), (.78, .5)))
            p.drawRect(box(.28, .5, .44, .3))
            p.setPen(Qt.PenStyle.NoPen if filled else QPen(c, 2.4))
            p.setBrush(c.lighter(185) if filled else Qt.BrushStyle.NoBrush)
            p.drawRect(box(.44, .6, .12, .2))                                         # door


class SummaryCard(QFrame):
    def __init__(self, title, kind):
        super().__init__()
        self.setObjectName("card")
        self.big, self.sub = label("0", "big"), label(role="muted")
        text = QVBoxLayout(); text.setSpacing(2)
        for w in (label(title, "muted"), self.big, self.sub):
            text.addWidget(w)
        lay = QHBoxLayout(self); lay.setContentsMargins(16, 14, 16, 14); lay.setSpacing(14)
        lay.addWidget(CardIcon(kind), alignment=Qt.AlignmentFlag.AlignTop); lay.addLayout(text, 1)

    def set(self, big, sub):
        self.big.setText(str(big)); self.sub.setText(sub)
