# Copyright (c) 2026 Skain. Todos los derechos reservados.

from PySide6.QtGui import QPixmap

from visagecam.processing.distortion import PRESETS as DISTORTION_PRESETS
from visagecam.ui.components import Card, Gallery, SliderRow, muted
from visagecam.ui.context import Context
from visagecam.ui.pages.base import Page, empty_pixmap, header

DISTORTION_ICONS = {
    "big_eyes": "eye",
    "tiny_eyes": "eye",
    "big_forehead": "sliders",
    "big_mouth": "mouth",
    "small_nose": "sliders",
    "big_chin": "sliders",
    "slim_face": "face",
    "bobble_head": "face",
    "tiny_face": "face",
    "funhouse": "sparkle",
}


def distortion_entries() -> list[tuple[str, str, QPixmap, bool]]:
    entries = [("", "Ninguna", empty_pixmap("sliders"), False)]
    for preset_id, preset in DISTORTION_PRESETS.items():
        entries.append(
            (preset_id, preset.name, empty_pixmap(DISTORTION_ICONS.get(preset_id, "sliders")), False)
        )
    return entries


class DistortionPage(Page):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        self.column.addLayout(header("Deformaciones"))
        card = Card(
            "Deforma tu cara en directo",
            "Agranda o encoge partes de tu rostro en tiempo real, en vez de superponer una imagen. Se puede combinar con una mascara o accesorio.",
        )
        self.gallery = Gallery()
        self.gallery.selected.connect(self._selected)
        self.gallery.set_items(distortion_entries())
        card.add(self.gallery)
        self.info = muted("")
        card.add(self.info)
        self.column.addWidget(card)

        strength = Card("Intensidad")
        self.sl_strength = SliderRow("Fuerza del efecto", 30, 200, 100, 1, " %")
        self.sl_strength.changed.connect(lambda v: ctx.set("distortion_strength", v / 100.0))
        strength.add(self.sl_strength)
        self.column.addWidget(strength)
        self.finish()

        self.gallery.select(ctx.settings.distortion)
        self._describe(ctx.settings.distortion)
        self.refresh()

    def refresh(self) -> None:
        self.gallery.select(self.ctx.settings.distortion)
        self.sl_strength.set_value(self.ctx.settings.distortion_strength * 100)
        self._describe(self.ctx.settings.distortion)

    def _selected(self, preset_id: str) -> None:
        self.ctx.set("distortion", preset_id)
        self._describe(preset_id)

    def _describe(self, preset_id: str) -> None:
        if not preset_id:
            self.info.setText("Sin deformacion: tu cara se ve tal cual.")
        else:
            self.info.setText(f'"{DISTORTION_PRESETS[preset_id].name}" activo. Ajusta la intensidad abajo.')
