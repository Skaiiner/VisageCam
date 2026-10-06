# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from visagecam.ui.context import Context
from visagecam.ui.icons import icon

THUMB = 112


DEFAULT_ADJUST = [1.0, 0.0, 0.0, 0.0]


class Page(QScrollArea):
    def __init__(self, ctx: Context) -> None:
        super().__init__()
        self.ctx = ctx
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        inner.setObjectName("page")
        self.setWidget(inner)
        self.column = QVBoxLayout(inner)
        self.column.setContentsMargins(4, 4, 12, 16)
        self.column.setSpacing(14)

    def finish(self) -> None:
        self.column.addStretch(1)

    def refresh(self) -> None:
        pass

    def tick(self) -> None:
        pass

    def shutdown(self) -> None:
        pass


def header(title: str, button_widget=None) -> QHBoxLayout:
    row = QHBoxLayout()
    label = QLabel(title)
    label.setObjectName("h1")
    row.addWidget(label)
    row.addStretch(1)
    if button_widget is not None:
        row.addWidget(button_widget)
    return row


def empty_pixmap(icon_name: str) -> QPixmap:
    return icon(icon_name, "#8b93a7", 48).pixmap(48, 48)
