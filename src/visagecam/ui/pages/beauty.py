# Copyright (c) 2026 Skain. Todos los derechos reservados.

from visagecam.ui.components import Card, SliderRow, button
from visagecam.ui.context import Context
from visagecam.ui.pages.base import Page, header


class BeautyPage(Page):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        self.column.addLayout(header("Belleza"))
        card = Card("Retoque en vivo", "Se aplica solo a tu rostro y funciona con o sin filtro.")
        self.sliders = {
            "beauty_smooth": SliderRow("Piel suave", 0, 100, 0, 1, " %"),
            "beauty_bright": SliderRow("Luminosidad", 0, 100, 0, 1, " %"),
            "beauty_lips": SliderRow("Color de labios", 0, 100, 0, 1, " %"),
            "beauty_teeth": SliderRow("Dientes mas blancos", 0, 100, 0, 1, " %"),
        }
        for key, slider in self.sliders.items():
            slider.changed.connect(lambda v, k=key: ctx.set(k, v / 100.0))
            card.add(slider)
        reset = button("Quitar retoques", "ghost", "refresh")
        reset.clicked.connect(self._reset)
        card.add(reset)
        self.column.addWidget(card)
        self.finish()
        self.refresh()

    def refresh(self) -> None:
        for key, slider in self.sliders.items():
            slider.set_value(getattr(self.ctx.settings, key) * 100)

    def _reset(self) -> None:
        for key in self.sliders:
            setattr(self.ctx.settings, key, 0.0)
        self.ctx.save()
        self.refresh()
