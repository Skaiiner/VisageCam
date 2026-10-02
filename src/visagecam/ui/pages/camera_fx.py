# Copyright (c) 2026 Skain. Todos los derechos reservados.

from PySide6.QtGui import QPixmap

from visagecam.processing.camera_effects import CATEGORIES as FX_CATEGORIES
from visagecam.processing.camera_effects import EFFECTS, effects_in
from visagecam.ui.components import Card, Gallery, Segmented, SliderRow, button, muted
from visagecam.ui.context import Context
from visagecam.ui.pages.base import Page, empty_pixmap, header

CATEGORY_ICONS = {"warp": "sliders", "style": "wand"}

GRADE_SLIDERS = (
    ("grade_brightness", "Brillo"),
    ("grade_contrast", "Contraste"),
    ("grade_saturation", "Saturacion"),
    ("grade_temperature", "Temperatura (frio / calido)"),
)


def effect_entries(category: str = "all") -> list[tuple[str, str, QPixmap, bool]]:
    entries = [("", "Ninguno", empty_pixmap("wand"), False)]
    for effect_id in effects_in(category):
        effect = EFFECTS[effect_id]
        entries.append(
            (effect_id, effect.name, empty_pixmap(CATEGORY_ICONS.get(effect.category, "wand")), False)
        )
    return entries


class CameraFxPage(Page):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        self.column.addLayout(header("Efectos de camara"))
        card = Card(
            "Efecto sobre toda la imagen",
            "Deforma o colorea el video entero, no solo tu cara. Se aplica al final, asi que tambien afecta a mascaras, accesorios y fondo.",
        )
        self.categories = Segmented([(key, label) for key, label in FX_CATEGORIES])
        self.categories.set_value("all")
        self.categories.changed.connect(lambda value: self._show_category(str(value)))
        card.add(self.categories)
        self.gallery = Gallery()
        self.gallery.selected.connect(self._selected)
        self.gallery.set_items(effect_entries())
        card.add(self.gallery)
        self.info = muted("")
        card.add(self.info)
        self.sl_strength = SliderRow("Intensidad", 30, 200, 100, 1, " %")
        self.sl_strength.changed.connect(lambda v: ctx.set("camera_effect_strength", v / 100.0))
        card.add(self.sl_strength)
        clear = button("Quitar efecto", "ghost", "refresh")
        clear.clicked.connect(self._clear)
        card.add(clear)
        self.column.addWidget(card)

        grade = Card("Ajustes de imagen", "Corrige el color de tu camara. Funciona con o sin efecto.")
        self.grade_sliders = {}
        for key, label in GRADE_SLIDERS:
            slider = SliderRow(label, -100, 100, 0, 1, " %")
            slider.changed.connect(lambda v, k=key: ctx.set(k, v / 100.0))
            grade.add(slider)
            self.grade_sliders[key] = slider
        reset = button("Restablecer color", "ghost", "refresh")
        reset.clicked.connect(self._reset_grade)
        grade.add(reset)
        self.column.addWidget(grade)
        self.finish()
        self.refresh()

    def refresh(self) -> None:
        settings = self.ctx.settings
        self.gallery.select(settings.camera_effect)
        self.sl_strength.set_value(settings.camera_effect_strength * 100)
        for key, slider in self.grade_sliders.items():
            slider.set_value(getattr(settings, key) * 100)
        self._describe(settings.camera_effect)

    def _show_category(self, category: str) -> None:
        self.gallery.set_items(effect_entries(category))
        self.gallery.select(self.ctx.settings.camera_effect)

    def _selected(self, effect_id: str) -> None:
        self.ctx.set("camera_effect", effect_id)
        self._describe(effect_id)

    def _clear(self) -> None:
        self.ctx.set("camera_effect", "")
        self.gallery.select("")
        self._describe("")

    def _reset_grade(self) -> None:
        for key, slider in self.grade_sliders.items():
            self.ctx.set(key, 0.0)
            slider.set_value(0)

    def _describe(self, effect_id: str) -> None:
        effect = EFFECTS.get(effect_id)
        if effect is None:
            self.info.setText(f"Sin efecto: la imagen sale tal cual. Hay {len(EFFECTS)} efectos.")
        else:
            self.info.setText(f'"{effect.name}" aplicado a toda la camara.')
