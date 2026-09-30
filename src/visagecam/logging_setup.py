import logging
import sys
from logging.handlers import RotatingFileHandler

from visagecam.config import data_dir

FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def configure(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if getattr(root, "_visagecam_configured", False):
        return
    root.setLevel(level)
    formatter = logging.Formatter(FORMAT)
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    root.addHandler(console)
    log_dir = data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "visagecam.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
    root._visagecam_configured = True
    logging.getLogger("PIL").setLevel(logging.WARNING)
