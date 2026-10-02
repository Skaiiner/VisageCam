# Copyright (c) 2026 Skain. Todos los derechos reservados.

from PySide6.QtGui import QPixmap

from visagecam.processing.distortion import CATEGORIES as DISTORTION_CATEGORIES
from visagecam.processing.distortion import PRESETS as DISTORTION_PRESETS
from visagecam.processing.distortion import presets_in
from visagecam.ui.components import Card, Gallery, Segmented, SliderRow, button, muted
from visagecam.ui.context import Context
from visagecam.ui.pages.base import Page, empty_pixmap, header

CATEGORY_ICONS = {"eyes": "eye", "mouth": "mouth", "face": "face", "fun": "sparkle"}


def distortion_entries(category: str = "all") -> list[tuple[str, str, QPixmap, bool]]:
    entries = [("", "Ninguna", empty_pixmap("sliders"), False)]
    for preset_id in presets_in(category):
        preset = DISTORTION_PRESETS[preset_id]
        icon_name = CATEGORY_ICONS.get(preset.category, "sliders")
        entries.append((preset_id, preset.name, empty_pixmap(icon_name), False))
    return entries


class DistortionPage(Page):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        self.column.addLayout(header("Deformaciones"))
        card = Card(
            "Deforma tu cara en directo",
            "Agranda, encoge, estira o retuerce partes de tu rostro en tiempo real, en vez de superponer una imagen. Se puede combinar con una mascara o accesorio.",
        )
        self.categories = Segmented([(key, label) for key, label in DISTORTION_CATEGORIES])
        self.categories.set_value("all")
        self.categories.changed.connect(lambda value: self._show_category(str(value)))
        card.add(self.categories)
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
        clear = button("Quitar deformacion", "ghost", "refresh")
        clear.clicked.connect(self._clear)
        strength.add(clear)
        self.column.addWidget(strength)
        self.finish()

        self.gallery.select(ctx.settings.distortion)
        self._describe(ctx.settings.distortion)
        self.refresh()

    def refresh(self) -> None:
        self.gallery.select(self.ctx.settings.distortion)
        self.sl_strength.set_value(self.ctx.settings.distortion_strength * 100)
        self._describe(self.ctx.settings.distortion)

    def _show_category(self, category: str) -> None:
        self.gallery.set_items(distortion_entries(category))
        self.gallery.select(self.ctx.settings.distortion)

    def _selected(self, preset_id: str) -> None:
        self.ctx.set("distortion", preset_id)
        self._describe(preset_id)

    def _clear(self) -> None:
        self.ctx.set("distortion", "")
        self.gallery.select("")
        self._describe("")

    def _describe(self, preset_id: str) -> None:
        preset = DISTORTION_PRESETS.get(preset_id)
        if preset is None:
            self.info.setText(
                f"Sin deformacion: tu cara se ve tal cual. Hay {len(DISTORTION_PRESETS)} efectos."
            )
        else:
            self.info.setText(f'"{preset.name}" activo. Ajusta la intensidad abajo.')
