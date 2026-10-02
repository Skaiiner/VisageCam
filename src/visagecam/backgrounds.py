# Copyright (c) 2026 Skain. Todos los derechos reservados.

import logging
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from visagecam.config import data_dir

log = logging.getLogger(__name__)

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MAX_SIDE = 1920


class BackgroundLibrary:
    def __init__(self, root: Path | None = None) -> None:
        self.dir = (root or data_dir()) / "backgrounds"
        self.dir.mkdir(parents=True, exist_ok=True)

    def list(self) -> list[Path]:
        files = [p for p in self.dir.iterdir() if p.suffix.lower() in EXTENSIONS]
        return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)

    def add(self, path: Path) -> Path:
        try:
            with Image.open(path) as source:
                source = ImageOps.exif_transpose(source)
                rgb = np.asarray(source.convert("RGB"))
        except Exception as exc:
            raise ValueError("No se pudo leer la imagen de fondo") from exc
        height, width = rgb.shape[:2]
        if min(height, width) < 64:
            raise ValueError("La imagen de fondo es demasiado pequena")
        longest = max(height, width)
        if longest > MAX_SIDE:
            scale = MAX_SIDE / longest
            rgb = cv2.resize(rgb, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
        target = self.dir / f"bg-{int(time.time() * 1000) % 10**10}.jpg"
        ok, encoded = cv2.imencode(
            ".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92]
        )
        if not ok:
            raise ValueError("No se pudo guardar la imagen de fondo")
        encoded.tofile(str(target))
        return target

    def remove(self, path: Path) -> None:
        try:
            Path(path).unlink()
        except FileNotFoundError:
            pass
