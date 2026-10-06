# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

from collections.abc import Callable

from PySide6.QtWidgets import (
    QHBoxLayout,
)

from visagecam.config import Settings
from visagecam.ui.components import Card, Gallery, SliderRow, SwitchRow, button, muted
from visagecam.ui.context import Context
from visagecam.ui.pages.base import THUMB, Page, empty_pixmap, header
from visagecam.ui.widgets import bgra_to_pixmap


class FiltersPage(Page):
    def __init__(self, ctx: Context, open_studio: Callable[[str], None]) -> None:
        super().__init__(ctx)
        add = button("Anadir imagen", "primary", "plus", "#0b0d12")
        add.clicked.connect(lambda: open_studio("mask"))
        self.column.addLayout(header("Filtros de cara", add))

        gallery_card = Card("Galeria", "Elige un filtro o anade cualquier imagen con el boton de arriba.")
        self.gallery = Gallery()
        self.gallery.selected.connect(self._selected)
        gallery_card.add(self.gallery)
        row = QHBoxLayout()
        self.info = muted("")
        self.delete = button("Eliminar", "danger", "trash", "#ff5d73")
        self.delete.clicked.connect(self._delete)
        row.addWidget(self.info, 1)
        row.addWidget(self.delete)
        gallery_card.add(layout=row)
        self.column.addWidget(gallery_card)

        pos = Card("Posicion")
        self.sl_scale = SliderRow("Escala", 20, 300, 100, 1, " %")
        self.sl_rotation = SliderRow("Rotacion", -180, 180, 0, 1, " grados")
        self.sl_x = SliderRow("Desplazamiento horizontal", -100, 100, 0, 1)
        self.sl_y = SliderRow("Desplazamiento vertical", -100, 100, 0, 1)
        for slider in (self.sl_scale, self.sl_rotation, self.sl_x, self.sl_y):
            pos.add(slider)
        reset = button("Restablecer ajustes", "ghost", "refresh")
        reset.clicked.connect(self._reset)
        pos.add(reset)
        self.column.addWidget(pos)

        real = Card("Realismo")
        self.sl_opacity = SliderRow("Opacidad", 0, 100, 100, 1, " %")
        self.sl_color = SliderRow("Ajuste de color a tu piel", 0, 100, 85, 1, " %")
        self.sl_light = SliderRow("Ajuste de luz", 0, 100, 60, 1, " %")
        self.sl_soft = SliderRow("Bordes suaves", 0, 100, 30, 1, " %")
        for slider in (self.sl_opacity, self.sl_color, self.sl_light, self.sl_soft):
            real.add(slider)
        self.column.addWidget(real)

        behave = Card("Comportamiento")
        self.sw_expr = SwitchRow("Seguir mis gestos", "La mascara se deforma con tu boca, mejillas y cejas.")
        self.sw_warp = SwitchRow(
            "Deformar sobre mi rostro", "Para imagenes con cara: se adaptan punto a punto."
        )
        self.sw_eyes = SwitchRow(
            "Conservar mis ojos y mi boca", "Se ven tus ojos y tu boca real a traves del filtro."
        )
        for sw in (self.sw_expr, self.sw_warp, self.sw_eyes):
            behave.add(sw)
        calib = QHBoxLayout()
        self.calib_status = muted("")
        recal = button("Recalibrar mi rostro", "ghost", "face")
        recal.setToolTip("Mira de frente con la boca cerrada durante un segundo")
        recal.clicked.connect(self._recalibrate)
        calib.addWidget(self.calib_status, 1)
        calib.addWidget(recal)
        behave.add(layout=calib)
        self.column.addWidget(behave)
        self.finish()

        c = ctx
        self.sl_scale.changed.connect(lambda v: c.set("mask_scale", v / 100.0))
        self.sl_rotation.changed.connect(lambda v: c.set("mask_rotation", v))
        self.sl_x.changed.connect(lambda v: c.set("mask_offset_x", v / 100.0))
        self.sl_y.changed.connect(lambda v: c.set("mask_offset_y", v / 100.0))
        self.sl_opacity.changed.connect(lambda v: c.set("mask_opacity", v / 100.0))
        self.sl_color.changed.connect(lambda v: c.set("color_match", v / 100.0))
        self.sl_light.changed.connect(lambda v: c.set("light_match", v / 100.0))
        self.sl_soft.changed.connect(lambda v: c.set("edge_softness", v / 100.0))
        self.sw_expr.toggled.connect(lambda v: c.set("expression", bool(v)))
        self.sw_warp.toggled.connect(lambda v: c.set("face_warp", bool(v)))
        self.sw_eyes.toggled.connect(lambda v: c.set("keep_eyes_mouth", bool(v)))
        self.populate()
        self.refresh()

    def populate(self) -> None:
        entries = [("", "Ninguno", empty_pixmap("mask"), False)]
        for mask in self.ctx.library.all():
            entries.append((mask.mask_id, mask.name, bgra_to_pixmap(mask.thumbnail(THUMB)), not mask.builtin))
        self.gallery.set_items(entries)
        self.gallery.select(self.ctx.settings.active_mask)
        self._describe(self.ctx.settings.active_mask)

    def select(self, mask_id: str) -> None:
        self.ctx.set("active_mask", mask_id)
        self.gallery.select(mask_id)
        self._describe(mask_id)

    def refresh(self) -> None:
        s = self.ctx.settings
        self.sl_scale.set_value(s.mask_scale * 100)
        self.sl_rotation.set_value(s.mask_rotation)
        self.sl_x.set_value(s.mask_offset_x * 100)
        self.sl_y.set_value(s.mask_offset_y * 100)
        self.sl_opacity.set_value(s.mask_opacity * 100)
        self.sl_color.set_value(s.color_match * 100)
        self.sl_light.set_value(s.light_match * 100)
        self.sl_soft.set_value(s.edge_softness * 100)
        self.sw_expr.setChecked(s.expression)
        self.sw_warp.setChecked(s.face_warp)
        self.sw_eyes.setChecked(s.keep_eyes_mouth)

    def _selected(self, mask_id: str) -> None:
        self.ctx.set("active_mask", mask_id)
        self._describe(mask_id)

    def _describe(self, mask_id: str) -> None:
        mask = self.ctx.library.get(mask_id) if mask_id else None
        self.delete.setVisible(mask is not None and not mask.builtin)
        if mask is None:
            self.info.setText("Sin filtro: se envia tu imagen tal cual.")
        elif mask.is_face:
            self.info.setText("Imagen con cara: se deforma sobre tu rostro.")
        elif mask.anchors:
            self.info.setText("Mascara anclada a los puntos del rostro.")
        else:
            self.info.setText("Imagen superpuesta y centrada en tu cara.")

    def _delete(self) -> None:
        mask_id = self.gallery.current_id()
        if mask_id and self.ctx.library.remove(mask_id):
            self.ctx.set("active_mask", "")
            self.populate()
            self.ctx.notify("Filtro eliminado", "info")

    def _reset(self) -> None:
        defaults = Settings()
        for key in (
            "mask_scale",
            "mask_rotation",
            "mask_offset_x",
            "mask_offset_y",
            "mask_opacity",
            "color_match",
            "light_match",
            "edge_softness",
        ):
            setattr(self.ctx.settings, key, getattr(defaults, key))
        self.ctx.save()
        self.refresh()

    def _recalibrate(self) -> None:
        self.ctx.engine.recalibrate()
        self.ctx.notify("Mira de frente con la boca cerrada un segundo", "info")

    def tick(self) -> None:
        ready, progress = self.ctx.engine.calibration(1)
        if ready:
            self.calib_status.setText("Rostro calibrado")
        elif self.ctx.engine.face_found:
            self.calib_status.setText(
                f"Calibrando... {int(progress * 100)} %  (mira de frente, boca cerrada)"
            )
        else:
            self.calib_status.setText("Sin calibrar: colocate frente a la camara")
