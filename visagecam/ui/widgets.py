import threading
from typing import Callable

import cv2
import numpy as np
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPalette
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QSlider, QWidget


def bgra_to_qimage(bgra: np.ndarray) -> QImage:
    rgba = np.ascontiguousarray(cv2.cvtColor(bgra, cv2.COLOR_BGRA2RGBA))
    height, width = rgba.shape[:2]
    return QImage(rgba.data, width, height, 4 * width, QImage.Format_RGBA8888).copy()


def bgr_to_qimage(bgr: np.ndarray) -> QImage:
    height, width = bgr.shape[:2]
    return QImage(bgr.data, width, height, 3 * width, QImage.Format_BGR888)


class AsyncRunner(QObject):
    _finished = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._finished.connect(self._dispatch)

    def run(self, work: Callable, on_done: Callable | None = None, on_fail: Callable | None = None) -> None:
        def target() -> None:
            try:
                result = work()
            except Exception as exc:
                self._finished.emit((on_fail, str(exc)))
                return
            self._finished.emit((on_done, result))

        threading.Thread(target=target, daemon=True).start()

    def _dispatch(self, payload) -> None:
        callback, argument = payload
        if callback is not None:
            callback(argument)


class SliderRow(QWidget):
    changed = Signal(float)

    def __init__(self, label: str, minimum: float, maximum: float, value: float,
                 step: float = 1.0, suffix: str = "", decimals: int = 0) -> None:
        super().__init__()
        self._step = step
        self._suffix = suffix
        self._decimals = decimals
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._label = QLabel(label)
        self._label.setFixedWidth(104)
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(round(minimum / step), round(maximum / step))
        self._value_label = QLabel()
        self._value_label.setFixedWidth(72)
        self._value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self._label)
        layout.addWidget(self._slider, 1)
        layout.addWidget(self._value_label)
        self.set_value(value)
        self._slider.valueChanged.connect(self._on_change)

    def value(self) -> float:
        return self._slider.value() * self._step

    def set_value(self, value: float) -> None:
        self._slider.blockSignals(True)
        self._slider.setValue(round(value / self._step))
        self._slider.blockSignals(False)
        self._refresh_label()

    def _refresh_label(self) -> None:
        self._value_label.setText(f"{self.value():.{self._decimals}f}{self._suffix}")

    def _on_change(self) -> None:
        self._refresh_label()
        self.changed.emit(self.value())


def apply_dark_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(30, 32, 38))
    palette.setColor(QPalette.WindowText, QColor(228, 230, 235))
    palette.setColor(QPalette.Base, QColor(22, 24, 29))
    palette.setColor(QPalette.AlternateBase, QColor(36, 38, 45))
    palette.setColor(QPalette.Text, QColor(228, 230, 235))
    palette.setColor(QPalette.Button, QColor(46, 49, 58))
    palette.setColor(QPalette.ButtonText, QColor(228, 230, 235))
    palette.setColor(QPalette.Highlight, QColor(255, 122, 43))
    palette.setColor(QPalette.HighlightedText, QColor(20, 20, 20))
    palette.setColor(QPalette.ToolTipBase, QColor(46, 49, 58))
    palette.setColor(QPalette.ToolTipText, QColor(228, 230, 235))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(120, 122, 130))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(120, 122, 130))
    app.setPalette(palette)
    app.setStyleSheet(
        """
        QPushButton { padding: 6px 12px; border-radius: 5px; }
        QPushButton#primary { background: #ff7a2b; color: #141414; font-weight: bold; padding: 10px; }
        QPushButton#primary:checked { background: #d9433b; color: white; }
        QListWidget { border: 1px solid #2f323a; border-radius: 6px; }
        QListWidget::item:selected { color: #ffffff; background: #3a2a20; border: 1px solid #ff7a2b; border-radius: 6px; }
        QTabWidget::pane { border: 1px solid #2f323a; border-radius: 6px; }
        QLabel#preview { background: #101216; border-radius: 8px; }
        QLabel#hint { color: #9aa0ad; }
        """
    )
