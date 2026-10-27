"""Light / dark theme: one QSS template filled with a color palette."""
from string import Template

LIGHT = dict(bg="#eef5fd", card="#ffffff", border="#dbe7f5", text="#1e293b", muted="#64748b",
             faint="#94a3b8", field="#ffffff", fieldborder="#c9daee", track="#dbe7f5",
             slot="#dde9f7", slothover="#bcd6f5", accent="#2f80ed", accenthover="#1d6fdc",
             soft="#e1edfb", softhover="#cfe2f8", softtext="#1e4f9c", hover="#f3f8ff",
             head="#eef5fd", tint="#e0eeff", side="#d9e9fb", sidetext="#35567f",
             sidehover="#c6ddf7", sidelabel="#6b8bb3", logo="#12335f")
DARK = dict(bg="#0b1220", card="#111c30", border="#1e2d47", text="#e5edf8", muted="#94a3b8",
            faint="#64748b", field="#0c1526", fieldborder="#2a3d5e", track="#1e2d47",
            slot="#16233b", slothover="#23406e", accent="#3b8cf5", accenthover="#2f80ed",
            soft="#1e2d47", softhover="#29406a", softtext="#cfe2ff", hover="#15243d",
            head="#15243d", tint="#18325c", side="#080d17", sidetext="#9db3d1",
            sidehover="#16233b", sidelabel="#5f7799", logo="#ffffff")

_QSS = Template("""
QWidget { font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; font-size: 13px; color: $text; }
QMainWindow, QDialog, QMessageBox, #page, #login { background: $bg; }
QToolTip { background: $card; color: $text; border: 1px solid $border; }
QScrollArea, #gridInner { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 10px; }
QScrollBar:horizontal { background: transparent; height: 10px; }
QScrollBar::handle { background: $border; border-radius: 5px; min-height: 30px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QGroupBox { background: $card; border: 1px solid $border; border-radius: 14px;
            margin-top: 14px; padding: 18px 14px 14px 14px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; }
QFrame#card, QFrame#loginCard, QFrame#unitCard { background: $card; border: 1px solid $border; border-radius: 14px; }
QFrame#unitCard:hover { border: 1px solid $accent; background: $hover; }
QFrame#slot { background: $slot; border-radius: 10px; }
QFrame#slot[filled="true"] { background: transparent; }
QFrame#slot[hover="true"] { background: $slothover; }

QLabel { background: transparent; }
QLabel[role="muted"], QLabel[role="hint"], QLabel[role="head"], QLabel[role="tiny"] { color: $muted; }
QLabel[role="hint"] { font-size: 12px; }
QLabel[role="tiny"] { font-size: 10px; }
QLabel[role="head"], QLabel[role="bold"], QLabel[role="count"] { font-weight: 600; }
QLabel[role="name"], QLabel[role="nameoff"] { font-weight: 700; }
QLabel[role="nameoff"], QLabel[role="id"], QLabel[role="plus"] { color: $faint; }
QLabel[role="id"] { font-size: 11px; }
QLabel[role="plus"] { font-size: 30px; }
QLabel[role="h1"] { font-size: 22px; font-weight: 700; }
QLabel[role="h2"] { font-size: 18px; font-weight: 700; }
QLabel[role="big"] { font-size: 30px; font-weight: 700; }
QLabel[role="err"] { color: #ef4444; }
QLabel[role="pill"] { background: $card; border: 1px solid $border; border-radius: 13px; padding: 6px 14px; font-weight: 600; }

QPushButton { background: $accent; color: white; border: none; border-radius: 8px; padding: 8px 18px; font-weight: 600; }
QPushButton:hover { background: $accenthover; }
QPushButton:disabled { background: $border; color: $faint; }
QPushButton[variant="secondary"] { background: $soft; color: $softtext; }
QPushButton[variant="secondary"]:hover { background: $softhover; }
#cardIcon { background: $tint; color: $accent; border-radius: 12px; }
QPushButton[variant="danger"] { background: #ef4444; color: white; padding: 5px 14px; }
QPushButton[variant="danger"]:hover { background: #dc2626; }

#sidebar { background: $side; }
#sidebar QLabel { color: $sidelabel; font-size: 11px; font-weight: 700; }
#sidebar QLabel[role="logo"] { color: $logo; font-size: 17px; }
#sidebar QPushButton { background: transparent; color: $sidetext; text-align: left; padding: 11px 14px; border-radius: 10px; }
#sidebar QPushButton:hover { background: $sidehover; }
#sidebar QPushButton:checked { background: $accent; color: white; }

QLineEdit, QSpinBox, QComboBox { background: $field; border: 1px solid $fieldborder; border-radius: 8px;
                                 padding: 5px 8px; min-height: 20px; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid $accent; }
QComboBox QAbstractItemView { background: $card; border: 1px solid $border; selection-background-color: $accent; selection-color: white; }
QTableWidget { background: $card; border: 1px solid $border; border-radius: 8px; gridline-color: $border; }
QHeaderView::section { background: $head; border: none; padding: 6px; font-weight: 600; }
QProgressBar { background: $track; border: none; border-radius: 5px; }
""")


def style(dark: bool) -> str:
    return _QSS.substitute(DARK if dark else LIGHT)
