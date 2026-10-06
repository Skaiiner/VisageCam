# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

from collections.abc import Callable

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
)

from visagecam.capture import RESOLUTIONS, list_cameras
from visagecam.ui.components import Card, Segmented, SliderRow, SwitchRow, button, muted
from visagecam.ui.context import Context
from visagecam.ui.pages.base import Page, header


class CameraPage(Page):
    def __init__(self, ctx: Context, on_camera_changed: Callable[[], None]) -> None:
        super().__init__(ctx)
        self._changed = on_camera_changed
        self.on_mirror: Callable[[str], None] | None = None
        self.column.addLayout(header("Camara y salida"))
        cam = Card("Camara")
        row = QHBoxLayout()
        self.camera_combo = QComboBox()
        self.camera_combo.activated.connect(lambda _i: self._apply())
        refresh = button("", "ghost", "refresh")
        refresh.setToolTip("Buscar camaras")
        refresh.clicked.connect(self.reload_cameras)
        row.addWidget(self.camera_combo, 1)
        row.addWidget(refresh)
        cam.add(layout=row)
        self.res_combo = QComboBox()
        for width, height in RESOLUTIONS:
            self.res_combo.addItem(f"{width} x {height}")
        self.res_combo.activated.connect(lambda _i: self._apply())
        cam.add(self.res_combo)
        self.sw_hq = SwitchRow(
            "Captura en alta calidad", "Captura a 1080p y reescala a 720p para una imagen mas nitida."
        )
        self.mirror = Segmented(
            [("off", "Sin espejo"), ("preview", "Solo vista previa"), ("both", "Vista previa y salida")]
        )
        self.mirror.changed.connect(lambda v: self._on_mirror(str(v)))
        self.sw_hq.toggled.connect(self._hq)
        cam.add(self.sw_hq)
        cam.add(self.mirror)
        cam.add(
            muted(
                "Solo vista previa te muestra como en un espejo sin invertir lo que ven los demas. Vista previa y salida tambien invierte la camara virtual."
            )
        )
        self.sl_enhance = SliderRow("Mejora de imagen", 0, 100, 50, 1, " %")
        self.sl_enhance.changed.connect(lambda v: ctx.set("enhance", v / 100.0))
        cam.add(self.sl_enhance)
        self.column.addWidget(cam)

        out = Card("Salida", "Donde aparece tu camara en otras aplicaciones.")
        self.backend = Segmented(
            [("auto", "Automatica"), ("unitycapture", "VisageCam"), ("obs", "OBS Virtual Camera")]
        )
        self.backend.changed.connect(lambda v: ctx.set("virtual_backend", str(v)))
        out.add(self.backend)
        out.add(
            muted(
                "VisageCam aparece como fuente de video en OBS (requiere el controlador Unity Capture). OBS Virtual Camera funciona en Discord, Zoom, Skype y Teams."
            )
        )
        self.column.addWidget(out)

        stream = Card(
            "Fuente para OBS sin controladores",
            "En OBS anade una Fuente multimedia, desmarca Archivo local y pega esta direccion.",
        )
        url_row = QHBoxLayout()
        self.url = QLineEdit(ctx.engine.stream.url)
        self.url.setReadOnly(True)
        copy = button("Copiar", "ghost", "link")
        copy.clicked.connect(self._copy)
        url_row.addWidget(self.url, 1)
        url_row.addWidget(copy)
        stream.add(layout=url_row)
        self.column.addWidget(stream)
        self.finish()
        self.reload_cameras()
        self.refresh()

    def reload_cameras(self) -> None:
        self.camera_combo.blockSignals(True)
        self.camera_combo.clear()
        for device in list_cameras():
            self.camera_combo.addItem(device.name, device.index)
        index = self.camera_combo.findData(self.ctx.settings.camera_index)
        if index >= 0:
            self.camera_combo.setCurrentIndex(index)
        elif self.camera_combo.count():
            self.ctx.settings.camera_index = int(self.camera_combo.itemData(0))
        self.camera_combo.blockSignals(False)
        if not self.camera_combo.count():
            self.camera_combo.addItem("No se encontraron camaras", -1)

    def refresh(self) -> None:
        s = self.ctx.settings
        self.sw_hq.setChecked(s.hq_capture)
        self.mirror.set_value(s.mirror_mode)
        self.sl_enhance.set_value(s.enhance * 100)
        self.backend.set_value(
            s.virtual_backend if s.virtual_backend in ("auto", "unitycapture", "obs") else "auto"
        )
        for index, (width, height) in enumerate(RESOLUTIONS):
            if (width, height) == (s.width, s.height):
                self.res_combo.setCurrentIndex(index)

    def tick(self) -> None:
        url = self.ctx.engine.stream.url
        if self.url.text() != url:
            self.url.setText(url)

    def _apply(self) -> None:
        data = self.camera_combo.currentData()
        if data is not None and int(data) >= 0:
            self.ctx.settings.camera_index = int(data)
        width, height = RESOLUTIONS[self.res_combo.currentIndex()]
        self.ctx.settings.width, self.ctx.settings.height = width, height
        self.ctx.save()
        self._changed()

    def _on_mirror(self, mode: str) -> None:
        self.ctx.set("mirror_mode", mode)
        if self.on_mirror is not None:
            self.on_mirror(mode)

    def _hq(self, checked: bool) -> None:
        if self.ctx.settings.hq_capture != bool(checked):
            self.ctx.set("hq_capture", bool(checked))
            self._changed()

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self.url.text())
        self.ctx.notify("Direccion copiada", "ok")
