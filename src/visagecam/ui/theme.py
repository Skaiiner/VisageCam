# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

import sys

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QWidget

COLORS = {
    "bg": "#0e1014",
    "surface": "#151820",
    "card": "#1a1e28",
    "card_hi": "#222734",
    "border": "#2a3040",
    "text": "#eceff6",
    "muted": "#8b93a7",
    "accent": "#7c6cff",
    "accent2": "#35c7f0",
    "ok": "#3ddc97",
    "warn": "#ffb454",
    "danger": "#ff5d73",
}


def qcolor(name: str) -> QColor:
    return QColor(COLORS[name])


def stylesheet() -> str:
    c = COLORS
    return f"""
    * {{ font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif; font-size: 13px; color: {c["text"]}; }}
    QMainWindow, QDialog {{ background: {c["bg"]}; }}
    QWidget#root, QWidget#page {{ background: transparent; }}
    QToolTip {{ background: {c["card_hi"]}; color: {c["text"]}; border: 1px solid {c["border"]}; padding: 6px 8px; border-radius: 6px; }}

    QFrame#card {{ background: {c["card"]}; border: 1px solid {c["border"]}; border-radius: 14px; }}
    QFrame#sidebar {{ background: {c["surface"]}; border-right: 1px solid {c["border"]}; }}
    QFrame#topbar {{ background: transparent; }}
    QLabel#h1 {{ font-size: 20px; font-weight: 700; }}
    QLabel#h2 {{ font-size: 14px; font-weight: 600; }}
    QLabel#muted {{ color: {c["muted"]}; }}
    QLabel#pill {{ background: {c["card"]}; border: 1px solid {c["border"]}; border-radius: 11px; padding: 3px 10px; color: {c["muted"]}; font-size: 12px; }}
    QLabel#pill[tone="ok"] {{ color: {c["ok"]}; border-color: #245a45; background: #12261f; }}
    QLabel#pill[tone="warn"] {{ color: {c["warn"]}; border-color: #5a4424; background: #2a2114; }}
    QLabel#pill[tone="danger"] {{ color: {c["danger"]}; border-color: #5a2430; background: #2a141a; }}
    QLabel#chip {{ background: {c["card_hi"]}; border-radius: 10px; padding: 3px 10px; font-size: 12px; }}
    QLabel#chip[tone="ok"] {{ background: #14342a; color: {c["ok"]}; }}
    QLabel#chip[tone="info"] {{ background: #1c2a44; color: {c["accent2"]}; }}
    QLabel#chip[tone="warn"] {{ background: #36290f; color: {c["warn"]}; }}

    QPushButton {{ background: {c["card_hi"]}; border: 1px solid {c["border"]}; border-radius: 9px; padding: 8px 14px; font-weight: 500; }}
    QPushButton:hover {{ background: #2b3142; border-color: #3a4258; }}
    QPushButton:pressed {{ background: #1f2431; }}
    QPushButton:disabled {{ color: #5d6478; background: {c["card"]}; }}
    QPushButton[variant="primary"] {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {c["accent"]}, stop:1 {c["accent2"]}); border: none; color: #0b0d12; font-weight: 700; padding: 11px 18px; }}
    QPushButton[variant="primary"]:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #8d7fff, stop:1 #55d3f5); }}
    QPushButton[variant="primary"]:checked {{ background: {c["danger"]}; color: white; }}
    QPushButton[variant="primary"]:disabled {{ background: #2a3040; color: #6b7288; }}
    QPushButton[variant="ghost"] {{ background: transparent; border: 1px solid {c["border"]}; }}
    QPushButton[variant="ghost"]:hover {{ background: {c["card_hi"]}; }}
    QPushButton[variant="danger"] {{ color: {c["danger"]}; background: transparent; border: 1px solid #5a2430; }}
    QPushButton[variant="danger"]:hover {{ background: #2a141a; }}
    QPushButton[segment="true"] {{ border-radius: 8px; background: transparent; border: none; padding: 7px 14px; color: {c["muted"]}; }}
    QPushButton[segment="true"]:checked {{ background: {c["card_hi"]}; color: {c["text"]}; border: 1px solid {c["border"]}; }}
    QPushButton[slot="true"] {{ background: {c["card"]}; border: 1px solid {c["border"]}; border-radius: 12px; padding: 10px 6px; color: {c["muted"]}; }}
    QPushButton[slot="true"]:checked {{ border: 1px solid {c["accent"]}; background: #1d2040; color: {c["text"]}; }}

    QToolButton#nav {{ background: transparent; border: none; border-radius: 12px; padding: 10px 6px 8px 6px; color: {c["muted"]}; font-size: 11px; font-weight: 500; }}
    QToolButton#nav:hover {{ background: {c["card"]}; color: {c["text"]}; }}
    QToolButton#nav:checked {{ background: #1d2040; color: {c["text"]}; }}

    QLineEdit, QSpinBox, QComboBox {{ background: {c["surface"]}; border: 1px solid {c["border"]}; border-radius: 9px; padding: 7px 10px; selection-background-color: {c["accent"]}; }}
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {c["accent"]}; }}
    QComboBox::drop-down {{ border: none; width: 26px; }}
    QComboBox QAbstractItemView {{ background: {c["card"]}; border: 1px solid {c["border"]}; selection-background-color: {c["accent"]}; selection-color: #0b0d12; outline: none; padding: 4px; }}

    QSlider::groove:horizontal {{ height: 5px; background: #262c3a; border-radius: 2px; }}
    QSlider::add-page:horizontal {{ background: #262c3a; border-radius: 2px; }}
    QSlider::sub-page:horizontal {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {c["accent"]}, stop:1 {c["accent2"]}); border-radius: 2px; }}
    QSlider::handle:horizontal {{ background: #ffffff; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px; border: 3px solid {c["accent"]}; }}
    QSlider::handle:horizontal:hover {{ border-color: {c["accent2"]}; }}
    QSlider:disabled::sub-page:horizontal {{ background: #343b4d; }}
    QSlider:disabled::handle:horizontal {{ border-color: #4a5268; background: #8a91a3; }}

    QScrollArea {{ background: transparent; border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: #2f3648; border-radius: 4px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: #3d4660; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
    QScrollBar:horizontal {{ height: 0; }}

    QListWidget {{ background: transparent; border: none; outline: none; }}
    QListWidget#plain {{ background: {c["surface"]}; border: 1px solid {c["border"]}; border-radius: 10px; padding: 4px; }}
    QListWidget#plain::item {{ padding: 8px 10px; border-radius: 8px; }}
    QListWidget#plain::item:selected, QListWidget#plain::item:hover {{ background: {c["card_hi"]}; color: {c["text"]}; }}
    QLabel#drop {{ background: {c["surface"]}; border: 2px dashed #39415a; border-radius: 16px; color: {c["muted"]}; }}
    QLabel#drop[hover="true"] {{ border-color: {c["accent"]}; background: #181a30; color: {c["text"]}; }}
    QLabel#previewbox {{ background: #0a0c10; border-radius: 12px; }}
    QMessageBox {{ background: {c["card"]}; }}
    """


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    palette = QPalette()
    palette.setColor(QPalette.Window, qcolor("bg"))
    palette.setColor(QPalette.WindowText, qcolor("text"))
    palette.setColor(QPalette.Base, qcolor("surface"))
    palette.setColor(QPalette.AlternateBase, qcolor("card"))
    palette.setColor(QPalette.Text, qcolor("text"))
    palette.setColor(QPalette.Button, qcolor("card_hi"))
    palette.setColor(QPalette.ButtonText, qcolor("text"))
    palette.setColor(QPalette.Highlight, qcolor("accent"))
    palette.setColor(QPalette.HighlightedText, QColor("#0b0d12"))
    palette.setColor(QPalette.ToolTipBase, qcolor("card_hi"))
    palette.setColor(QPalette.ToolTipText, qcolor("text"))
    palette.setColor(QPalette.PlaceholderText, qcolor("muted"))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#5d6478"))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#5d6478"))
    app.setPalette(palette)
    app.setStyleSheet(stylesheet())


def enable_dark_titlebar(widget: QWidget) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = int(widget.winId())
        value = ctypes.c_int(1)
        for attribute in (20, 19):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)
            )
    except Exception:
        pass
