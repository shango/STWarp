"""Qt stylesheet + palette for STMesh.

A dark, modern look with a single accent colour. Designed for readability
on high-DPI displays and to feel at home next to modern VFX tools.
"""

from __future__ import annotations


# Palette
BG = "#0f1115"
SURFACE = "#171a21"
SURFACE_HI = "#1e222b"
BORDER = "#262b35"
BORDER_HI = "#313745"
TEXT = "#e7ebf3"
TEXT_DIM = "#8a93a6"
TEXT_MUTED = "#5f6879"
ACCENT = "#6aa8ff"
ACCENT_HI = "#8cbdff"
ACCENT_DOWN = "#4d8fe6"
SUCCESS = "#5ed39a"
WARN = "#ffb56a"
ERROR = "#ff6f7a"


STYLE = f"""
* {{
    color: {TEXT};
    font-family: "Inter", "Segoe UI", "SF Pro Text", "Helvetica Neue",
        Arial, sans-serif;
    font-size: 13px;
}}

QMainWindow, QDialog, QWidget#central {{
    background-color: {BG};
}}

QLabel#title {{
    font-size: 22px;
    font-weight: 600;
    letter-spacing: 0.2px;
    color: {TEXT};
}}

QLabel#subtitle {{
    color: {TEXT_DIM};
    font-size: 13px;
}}

QLabel#sectionTitle {{
    color: {TEXT_DIM};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    padding-bottom: 2px;
}}

QLabel#fieldLabel {{
    color: {TEXT};
    font-size: 12px;
    font-weight: 500;
}}

QLabel#helper {{
    color: {TEXT_MUTED};
    font-size: 11px;
}}

QFrame#card {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}

QLineEdit {{
    background-color: {SURFACE_HI};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 9px 12px;
    selection-background-color: {ACCENT};
    selection-color: {BG};
}}
QLineEdit:focus {{
    border: 1px solid {ACCENT};
}}
QLineEdit:disabled {{
    color: {TEXT_MUTED};
}}
QLineEdit[readOnly="true"] {{
    background-color: {SURFACE};
    color: {TEXT_DIM};
}}

QPushButton {{
    background-color: {SURFACE_HI};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {BORDER};
    border-color: {BORDER_HI};
}}
QPushButton:pressed {{
    background-color: {BORDER_HI};
}}
QPushButton:disabled {{
    color: {TEXT_MUTED};
    background-color: {SURFACE};
}}

QPushButton#primary {{
    background-color: {ACCENT};
    color: {BG};
    border: 1px solid {ACCENT};
    font-weight: 600;
    padding: 10px 20px;
}}
QPushButton#primary:hover {{
    background-color: {ACCENT_HI};
    border-color: {ACCENT_HI};
}}
QPushButton#primary:pressed {{
    background-color: {ACCENT_DOWN};
    border-color: {ACCENT_DOWN};
}}
QPushButton#primary:disabled {{
    background-color: {SURFACE_HI};
    color: {TEXT_MUTED};
    border-color: {BORDER};
}}

QPushButton#ghost {{
    background-color: transparent;
    border: 1px solid {BORDER};
}}
QPushButton#ghost:hover {{
    background-color: {SURFACE_HI};
}}

QComboBox {{
    background-color: {SURFACE_HI};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    min-width: 80px;
}}
QComboBox:hover {{ border-color: {BORDER_HI}; }}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
    selection-color: {BG};
    outline: 0;
    padding: 4px;
}}

QProgressBar {{
    background-color: {SURFACE_HI};
    border: 1px solid {BORDER};
    border-radius: 6px;
    text-align: center;
    height: 8px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 6px;
}}

QPlainTextEdit, QTextEdit {{
    background-color: {SURFACE_HI};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 10px 12px;
    font-family: "JetBrains Mono", "Cascadia Mono", "Consolas",
        "Menlo", monospace;
    font-size: 12px;
    color: {TEXT_DIM};
    selection-background-color: {ACCENT};
    selection-color: {BG};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_HI};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {TEXT_MUTED};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{ height: 0; }}

QToolTip {{
    background-color: {SURFACE_HI};
    color: {TEXT};
    border: 1px solid {BORDER_HI};
    border-radius: 6px;
    padding: 6px 8px;
}}

QStatusBar {{
    background-color: {BG};
    color: {TEXT_DIM};
    border-top: 1px solid {BORDER};
}}
"""
