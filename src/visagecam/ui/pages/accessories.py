# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

from collections.abc import Callable

from PySide6.QtWidgets import (
    QHBoxLayout,
)

from visagecam.ui.components import Card, Gallery, SliderRow, button, muted
from visagecam.ui.context import Context
from visagecam.ui.pages.base import DEFAULT_ADJUST, THUMB, Page, header
from visagecam.ui.widgets import bgra_to_pixmap


class AccessoriesPage(Page):
    def __init__(self, ctx: Context, open_studio: Callable[[str], None]) -> None:
        super().__init__(ctx)
        add = button("Anadir imagen", "primary", "plus", "#0b0d12")
        add.clicked.connect(lambda: open_studio("accessory"))
        self.column.addLayout(header("Accesorios", add))

        card = Card("Galeria", "Marca los que quieras llevar puestos. Puedes combinar varios.")
        self.gallery = Gallery(checkable=True)
        self.gallery.toggled.connect(self._toggled)
        self.gallery.selected.connect(self._selected)
        card.add(self.gallery)
        row = QHBoxLayout()
        self.delete = button("Eliminar", "danger", "trash", "#ff5d73")
        self.delete.clicked.connect(self._delete)
        clear = button("Quitar todos", "ghost")
        clear.clicked.connect(self._clear)
        row.addWidget(clear)
        row.addStretch(1)
        row.addWidget(self.delete)
        card.add(layout=row)
        self.column.addWidget(card)

        adjust = Card("Ajuste")
        self.target = muted("Selecciona un accesorio para ajustar su posicion.")
        adjust.add(self.target)
        self.sl_scale = SliderRow("Escala", 20, 300, 100, 1, " %")
        self.sl_rot = SliderRow("Rotacion", -180, 180, 0, 1, " grados")
        self.sl_x = SliderRow("Desplazamiento horizontal", -100, 100, 0, 1)
        self.sl_y = SliderRow("Desplazamiento vertical", -100, 100, 0, 1)
        for slider in (self.sl_scale, self.sl_rot, self.sl_x, self.sl_y):
            slider.changed.connect(self._adjust_changed)
            adjust.add(slider)
        reset = button("Restablecer este accesorio", "ghost", "refresh")
        reset.clicked.connect(self._reset)
        adjust.add(reset)
        self.column.addWidget(adjust)
        self.finish()
        self.populate()

    def populate(self) -> None:
        entries = [
            (m.mask_id, m.name, bgra_to_pixmap(m.thumbnail(THUMB)), not m.builtin)
            for m in self.ctx.library.accessories()
        ]
        self.gallery.set_items(entries, self.ctx.settings.accessories)
        self._selected(self.gallery.current_id() or "")

    def add_and_enable(self, item_id: str) -> None:
        active = [a for a in self.ctx.settings.accessories if a != item_id] + [item_id]
        self.ctx.set("accessories", active)
        self.populate()
        self.gallery.select(item_id)
        self._selected(item_id)

    def _toggled(self, item_id: str, state: bool) -> None:
        active = [a for a in self.ctx.settings.accessories if a != item_id]
        if state:
            active.append(item_id)
        self.ctx.set("accessories", active)

    def _selected(self, item_id: str) -> None:
        item = self.ctx.library.get(item_id) if item_id else None
        for slider in (self.sl_scale, self.sl_rot, self.sl_x, self.sl_y):
            slider.setEnabled(item is not None)
        self.delete.setVisible(item is not None and not item.builtin)
        if item is None:
            self.target.setText("Selecciona un accesorio para ajustar su posicion.")
            return
        self.target.setText(f"Ajustando: {item.name}")
        scale, rotation, dx, dy = self.ctx.settings.accessory_adjust.get(item_id, DEFAULT_ADJUST)
        self.sl_scale.set_value(scale * 100)
        self.sl_rot.set_value(rotation)
        self.sl_x.set_value(dx * 100)
        self.sl_y.set_value(dy * 100)

    def _adjust_changed(self, _value: float = 0.0) -> None:
        item_id = self.gallery.current_id()
        if not item_id:
            return
        adjust = dict(self.ctx.settings.accessory_adjust)
        adjust[item_id] = [
            self.sl_scale.value() / 100.0,
            self.sl_rot.value(),
            self.sl_x.value() / 100.0,
            self.sl_y.value() / 100.0,
        ]
        self.ctx.set("accessory_adjust", adjust)

    def _reset(self) -> None:
        item_id = self.gallery.current_id()
        if not item_id:
            return
        adjust = dict(self.ctx.settings.accessory_adjust)
        adjust.pop(item_id, None)
        self.ctx.set("accessory_adjust", adjust)
        self._selected(item_id)

    def _delete(self) -> None:
        item_id = self.gallery.current_id()
        if item_id and self.ctx.library.remove(item_id):
            self.ctx.set("accessories", [a for a in self.ctx.settings.accessories if a != item_id])
            adjust = dict(self.ctx.settings.accessory_adjust)
            adjust.pop(item_id, None)
            self.ctx.set("accessory_adjust", adjust)
            self.populate()
            self.ctx.notify("Accesorio eliminado", "info")

    def _clear(self) -> None:
        self.ctx.set("accessories", [])
        self.gallery.set_checked([])
