# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

import logging
import sys
import traceback

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from visagecam import __version__
from visagecam.config import Settings, data_dir
from visagecam.logging_setup import configure
from visagecam.masks.library import MaskLibrary
from visagecam.processing.engine import Engine
from visagecam.shortcuts import ASSETS
from visagecam.ui.main_window import MainWindow
from visagecam.ui.theme import apply_theme

log = logging.getLogger(__name__)


def _install_excepthook() -> None:
    def hook(exc_type, exc, tb) -> None:
        log.error("Excepcion no controlada\n%s", "".join(traceback.format_exception(exc_type, exc, tb)))

    sys.excepthook = hook


def _set_app_identity() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("VisageCam.App")
    except Exception:
        log.debug("No se pudo fijar la identidad de la aplicacion", exc_info=True)


def main() -> int:
    configure()
    _set_app_identity()
    _install_excepthook()
    log.info("VisageCam %s", __version__)
    settings = Settings.load()
    library = MaskLibrary(data_dir() / "masks")
    library.load()
    app = QApplication(sys.argv)
    app.setApplicationName("VisageCam")
    app.setWindowIcon(QIcon(str(ASSETS / "visagecam.png")))
    apply_theme(app)
    engine = Engine(settings, library)
    window = MainWindow(settings, library, engine)
    window.show()
    try:
        return app.exec()
    except Exception:
        log.exception("Error fatal en la aplicacion")
        QMessageBox.critical(
            None,
            "VisageCam",
            "Se produjo un error inesperado. Revisa el registro en %APPDATA%\\VisageCam\\logs.",
        )
        return 1
