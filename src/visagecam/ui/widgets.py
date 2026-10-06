# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

import logging
import threading
from collections.abc import Callable

import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage, QPixmap

log = logging.getLogger(__name__)


def bgra_to_qimage(bgra: np.ndarray) -> QImage:
    rgba = np.ascontiguousarray(cv2.cvtColor(bgra, cv2.COLOR_BGRA2RGBA))
    height, width = rgba.shape[:2]
    return QImage(rgba.data, width, height, 4 * width, QImage.Format_RGBA8888).copy()


def bgra_to_pixmap(bgra: np.ndarray) -> QPixmap:
    return QPixmap.fromImage(bgra_to_qimage(bgra))


def over_checker(bgra: np.ndarray, size: int, cell: int = 14) -> QPixmap:
    height, width = bgra.shape[:2]
    scale = size / max(height, width)
    small = cv2.resize(
        bgra, (max(1, int(width * scale)), max(1, int(height * scale))), interpolation=cv2.INTER_AREA
    )
    h, w = small.shape[:2]
    yy, xx = np.mgrid[:h, :w]
    board = (((xx // cell) + (yy // cell)) % 2) * 16 + 34
    alpha = small[:, :, 3:4].astype(np.float32) / 255.0
    out = small[:, :, :3].astype(np.float32) * alpha + board[..., None].astype(np.float32) * (1.0 - alpha)
    rgb = np.ascontiguousarray(out.astype(np.uint8)[:, :, ::-1])
    return QPixmap.fromImage(QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy())


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
                log.exception("Tarea en segundo plano fallida")
                self._finished.emit((on_fail, str(exc) or exc.__class__.__name__))
                return
            self._finished.emit((on_done, result))

        threading.Thread(target=target, daemon=True).start()

    def _dispatch(self, payload) -> None:
        callback, argument = payload
        if callback is None:
            return
        try:
            callback(argument)
        except Exception:
            log.exception("Error en el callback de una tarea")
