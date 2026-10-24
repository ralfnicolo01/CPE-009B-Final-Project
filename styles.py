"""Minimal light theme."""
STYLE = """
QWidget { font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; font-size: 13px; color: #1f2937; }
QMainWindow, QDialog, #page, #login { background: #f5f6f8; }
QScrollArea { background: transparent; border: none; }
#gridInner { background: transparent; }
QGroupBox { background: white; border: 1px solid #e3e6ea; border-radius: 8px;
            margin-top: 14px; padding: 16px 12px 12px 12px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #374151; }
QFrame#card, QFrame#loginCard { background: white; border: 1px solid #e3e6ea; border-radius: 10px; }
QFrame#unitCard { background: white; border: 1px solid #e3e6ea; border-radius: 10px; }
QFrame#unitCard:hover { border: 1px solid #2563eb; background: #f8fbff; }
QFrame#slot { background: #e3e7ee; border-radius: 8px; }
QFrame#slot[filled="true"] { background: transparent; }
QFrame#slot[hover="true"] { background: #c7d7f5; }
QLabel { background: transparent; }
QPushButton { background: #2563eb; color: white; border: none; border-radius: 6px;
              padding: 7px 16px; font-weight: 600; }
QPushButton:hover { background: #1d4ed8; }
QPushButton:disabled { background: #cbd5e1; }
QPushButton[variant="secondary"] { background: #e5e7eb; color: #374151; }
QPushButton[variant="secondary"]:hover { background: #d1d5db; }
QPushButton[variant="danger"] { background: #ef4444; padding: 4px 12px; }
QPushButton[variant="danger"]:hover { background: #dc2626; }
QLineEdit, QSpinBox, QComboBox { background: white; border: 1px solid #d1d5db; border-radius: 6px;
                                 padding: 5px 8px; min-height: 20px; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #2563eb; }
QTabWidget::pane { border: none; }
QTabBar::tab { padding: 8px 20px; background: transparent; color: #6b7280; font-weight: 600;
               border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #2563eb; border-bottom: 2px solid #2563eb; }
QTableWidget { background: white; border: 1px solid #e3e6ea; gridline-color: #eef0f3; }
QHeaderView::section { background: #f3f4f6; border: none; padding: 6px; font-weight: 600; }
"""
