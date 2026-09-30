import logging
import sys

from PySide6.QtWidgets import QApplication

from visagecam import __version__
from visagecam.config import Settings, data_dir
from visagecam.logging_setup import configure
from visagecam.masks.library import MaskLibrary
from visagecam.processing.engine import Engine
from visagecam.ui.main_window import MainWindow
from visagecam.ui.widgets import apply_dark_theme

log = logging.getLogger(__name__)


def main() -> int:
    configure()
    log.info("VisageCam %s", __version__)
    settings = Settings.load()
    library = MaskLibrary(data_dir() / "masks")
    library.load()
    app = QApplication(sys.argv)
    app.setApplicationName("VisageCam")
    apply_dark_theme(app)
    engine = Engine(settings, library)
    window = MainWindow(settings, library, engine)
    window.show()
    return app.exec()
