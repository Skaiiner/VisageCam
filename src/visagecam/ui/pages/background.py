# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
)

from visagecam.ui.components import Card, Gallery, Segmented, SliderRow, button, muted
from visagecam.ui.context import Context
from visagecam.ui.pages.base import THUMB, Page, header
from visagecam.ui.studio import IMAGE_FILTER
from visagecam.ui.widgets import bgra_to_pixmap

log = logging.getLogger(__name__)


class BackgroundPage(Page):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        self.column.addLayout(header("Fondo"))
        mode = Card("Modo", "Separa tu silueta del fondo en tiempo real.")
        self.segment = Segmented([("none", "Sin cambios"), ("blur", "Desenfoque"), ("image", "Imagen")])
        self.segment.changed.connect(self._mode)
        mode.add(self.segment)
        self.sl_blur = SliderRow("Intensidad del desenfoque", 5, 100, 40, 1)
        self.sl_blur.changed.connect(lambda v: ctx.set("blur_strength", int(v)))
        mode.add(self.sl_blur)
        self.column.addWidget(mode)

        images = Card("Imagenes de fondo", "Tus fondos se guardan aqui para reutilizarlos.")
        self.gallery = Gallery()
        self.gallery.selected.connect(self._picked)
        self.empty = muted("Todavia no has anadido fondos. Pulsa Anadir fondo para empezar.")
        images.add(self.empty)
        images.add(self.gallery)
        row = QHBoxLayout()
        add = button("Anadir fondo", "ghost", "plus")
        add.clicked.connect(self._add)
        self.delete = button("Eliminar", "danger", "trash", "#ff5d73")
        self.delete.clicked.connect(self._delete)
        row.addWidget(add)
        row.addStretch(1)
        row.addWidget(self.delete)
        images.add(layout=row)
        self.column.addWidget(images)
        self.finish()
        self.populate()
        self.refresh()

    def populate(self) -> None:
        import cv2
        import numpy as np

        entries = []
        for path in self.ctx.backgrounds.list():
            data = cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_COLOR)
            if data is None:
                continue
            h, w = data.shape[:2]
            scale = THUMB / max(h, w)
            small = cv2.resize(
                data, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA
            )
            bgra = cv2.cvtColor(small, cv2.COLOR_BGR2BGRA)
            entries.append((str(path), "Fondo", bgra_to_pixmap(bgra), True))
        self.gallery.set_items(entries)
        self.empty.setVisible(not entries)
        self.gallery.select(self.ctx.settings.background_image)
        self.delete.setVisible(self.gallery.current_id() is not None)

    def refresh(self) -> None:
        s = self.ctx.settings
        self.segment.set_value(
            s.background_mode if s.background_mode in ("none", "blur", "image") else "none"
        )
        self.sl_blur.set_value(s.blur_strength)

    def _mode(self, value: object) -> None:
        mode = str(value)
        if mode == "image" and not (
            self.ctx.settings.background_image and Path(self.ctx.settings.background_image).is_file()
        ):
            if not self._add():
                self.segment.set_value(self.ctx.settings.background_mode)
                return
        self.ctx.set("background_mode", mode)

    def _picked(self, path: str) -> None:
        self.ctx.set("background_image", path)
        self.ctx.set("background_mode", "image")
        self.segment.set_value("image")
        self.delete.setVisible(True)

    def _add(self) -> bool:
        path, _ = QFileDialog.getOpenFileName(self, "Elegir fondo", "", IMAGE_FILTER)
        if not path:
            return False
        try:
            stored = self.ctx.backgrounds.add(Path(path))
        except ValueError as exc:
            self.ctx.notify(str(exc), "error")
            return False
        self.ctx.set("background_image", str(stored))
        self.ctx.set("background_mode", "image")
        self.populate()
        self.segment.set_value("image")
        return True

    def _delete(self) -> None:
        path = self.gallery.current_id()
        if not path:
            return
        self.ctx.backgrounds.remove(Path(path))
        if self.ctx.settings.background_image == path:
            self.ctx.set("background_image", "")
            if self.ctx.settings.background_mode == "image":
                self.ctx.set("background_mode", "none")
                self.segment.set_value("none")
        self.populate()
