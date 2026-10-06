# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

from collections.abc import Callable

from PySide6.QtWidgets import (
    QHBoxLayout,
)

from visagecam.processing.distortion import PRESETS as DISTORTION_PRESETS
from visagecam.ui.components import Card, Gallery, SliderRow, SwitchRow, button, muted
from visagecam.ui.context import Context
from visagecam.ui.pages.base import DEFAULT_ADJUST, THUMB, Page, empty_pixmap, header
from visagecam.ui.pages.distortion import distortion_entries
from visagecam.ui.widgets import bgra_to_pixmap


class Person2Page(Page):
    def __init__(self, ctx: Context, open_studio: Callable[[str, int], None]) -> None:
        super().__init__(ctx)
        self.column.addLayout(header("Persona 2"))
        intro = Card(
            "Segunda persona",
            "Pon un filtro distinto a otra persona que aparezca contigo en la camara. Cada una mantiene su propio filtro aunque se muevan o se crucen.",
        )
        self.sw_dual = SwitchRow(
            "Activar modo dos personas", "Busca hasta dos caras en la imagen y aplica un filtro a cada una."
        )
        self.sw_dual.toggled.connect(lambda v: ctx.set("dual_faces", bool(v)))
        intro.add(self.sw_dual)
        self.hint = muted("")
        intro.add(self.hint)
        self.column.addWidget(intro)

        add = button("Anadir imagen para esta persona", "primary", "plus", "#0b0d12")
        add.clicked.connect(lambda: open_studio("mask", 2))
        self.column.addLayout(header("Filtro de cara", add))
        gallery_card = Card("Galeria")
        self.gallery = Gallery()
        self.gallery.selected.connect(self._mask_selected)
        gallery_card.add(self.gallery)
        row = QHBoxLayout()
        self.info = muted("")
        self.delete = button("Eliminar", "danger", "trash", "#ff5d73")
        self.delete.clicked.connect(self._delete_mask)
        row.addWidget(self.info, 1)
        row.addWidget(self.delete)
        gallery_card.add(layout=row)
        self.column.addWidget(gallery_card)

        pos = Card("Posicion y realismo")
        self.sl_scale = SliderRow("Escala", 20, 300, 100, 1, " %")
        self.sl_rotation = SliderRow("Rotacion", -180, 180, 0, 1, " grados")
        self.sl_x = SliderRow("Desplazamiento horizontal", -100, 100, 0, 1)
        self.sl_y = SliderRow("Desplazamiento vertical", -100, 100, 0, 1)
        self.sl_opacity = SliderRow("Opacidad", 0, 100, 100, 1, " %")
        self.sl_color = SliderRow("Ajuste de color a su piel", 0, 100, 85, 1, " %")
        self.sl_light = SliderRow("Ajuste de luz", 0, 100, 60, 1, " %")
        self.sl_soft = SliderRow("Bordes suaves", 0, 100, 30, 1, " %")
        for slider in (
            self.sl_scale,
            self.sl_rotation,
            self.sl_x,
            self.sl_y,
            self.sl_opacity,
            self.sl_color,
            self.sl_light,
            self.sl_soft,
        ):
            pos.add(slider)
        self.column.addWidget(pos)

        behave = Card("Comportamiento")
        self.sw_expr = SwitchRow("Seguir sus gestos", "La mascara se deforma con su boca, mejillas y cejas.")
        self.sw_warp = SwitchRow(
            "Deformar sobre su rostro", "Para imagenes con cara: se adaptan punto a punto."
        )
        self.sw_eyes = SwitchRow(
            "Conservar sus ojos y su boca", "Se ven sus ojos y su boca real a traves del filtro."
        )
        for sw in (self.sw_expr, self.sw_warp, self.sw_eyes):
            behave.add(sw)
        calib = QHBoxLayout()
        self.calib_status = muted("")
        recal = button("Recalibrar ese rostro", "ghost", "face")
        recal.setToolTip("Pide a esa persona que mire de frente con la boca cerrada un segundo")
        recal.clicked.connect(self._recalibrate)
        calib.addWidget(self.calib_status, 1)
        calib.addWidget(recal)
        behave.add(layout=calib)
        self.column.addWidget(behave)

        self.column.addLayout(header("Deformacion"))
        dist_card = Card(
            "Deforma su cara",
            "En vez de superponer una imagen, agranda o encoge partes de su rostro. Se puede combinar con la mascara.",
        )
        self.dist_gallery = Gallery()
        self.dist_gallery.selected.connect(self._distortion_selected)
        self.dist_gallery.set_items(distortion_entries())
        dist_card.add(self.dist_gallery)
        self.dist_info = muted("")
        dist_card.add(self.dist_info)
        self.sl_dist_strength = SliderRow("Fuerza del efecto", 30, 200, 100, 1, " %")
        self.sl_dist_strength.changed.connect(lambda v: ctx.set_person2("distortion_strength", v / 100.0))
        dist_card.add(self.sl_dist_strength)
        self.column.addWidget(dist_card)

        add_acc = button("Anadir accesorio", "ghost", "plus")
        add_acc.clicked.connect(lambda: open_studio("accessory", 2))
        self.column.addLayout(header("Accesorios", add_acc))
        acc_card = Card("Galeria", "Marca los que quieras llevar puestos para esta persona.")
        self.acc_gallery = Gallery(checkable=True)
        self.acc_gallery.toggled.connect(self._acc_toggled)
        self.acc_gallery.selected.connect(self._acc_selected)
        acc_card.add(self.acc_gallery)
        acc_row = QHBoxLayout()
        self.acc_delete = button("Eliminar", "danger", "trash", "#ff5d73")
        self.acc_delete.clicked.connect(self._acc_delete)
        clear = button("Quitar todos", "ghost")
        clear.clicked.connect(self._acc_clear)
        acc_row.addWidget(clear)
        acc_row.addStretch(1)
        acc_row.addWidget(self.acc_delete)
        acc_card.add(layout=acc_row)
        self.column.addWidget(acc_card)

        acc_adjust = Card("Ajuste del accesorio")
        self.acc_target = muted("Selecciona un accesorio para ajustar su posicion.")
        acc_adjust.add(self.acc_target)
        self.acc_scale = SliderRow("Escala", 20, 300, 100, 1, " %")
        self.acc_rot = SliderRow("Rotacion", -180, 180, 0, 1, " grados")
        self.acc_x = SliderRow("Desplazamiento horizontal", -100, 100, 0, 1)
        self.acc_y = SliderRow("Desplazamiento vertical", -100, 100, 0, 1)
        for slider in (self.acc_scale, self.acc_rot, self.acc_x, self.acc_y):
            slider.changed.connect(self._acc_adjust_changed)
            acc_adjust.add(slider)
        self.column.addWidget(acc_adjust)

        self.column.addLayout(header("Belleza"))
        beauty_card = Card("Retoque en vivo", "Se aplica solo al rostro de esta persona.")
        self.beauty_sliders = {
            "beauty_smooth": SliderRow("Piel suave", 0, 100, 0, 1, " %"),
            "beauty_bright": SliderRow("Luminosidad", 0, 100, 0, 1, " %"),
            "beauty_lips": SliderRow("Color de labios", 0, 100, 0, 1, " %"),
            "beauty_teeth": SliderRow("Dientes mas blancos", 0, 100, 0, 1, " %"),
        }
        for key, slider in self.beauty_sliders.items():
            slider.changed.connect(lambda v, k=key: ctx.set_person2(k, v / 100.0))
            beauty_card.add(slider)
        self.column.addWidget(beauty_card)
        self.finish()

        self.sl_scale.changed.connect(lambda v: ctx.set_person2("mask_scale", v / 100.0))
        self.sl_rotation.changed.connect(lambda v: ctx.set_person2("mask_rotation", v))
        self.sl_x.changed.connect(lambda v: ctx.set_person2("mask_offset_x", v / 100.0))
        self.sl_y.changed.connect(lambda v: ctx.set_person2("mask_offset_y", v / 100.0))
        self.sl_opacity.changed.connect(lambda v: ctx.set_person2("mask_opacity", v / 100.0))
        self.sl_color.changed.connect(lambda v: ctx.set_person2("color_match", v / 100.0))
        self.sl_light.changed.connect(lambda v: ctx.set_person2("light_match", v / 100.0))
        self.sl_soft.changed.connect(lambda v: ctx.set_person2("edge_softness", v / 100.0))
        self.sw_expr.toggled.connect(lambda v: ctx.set_person2("expression", bool(v)))
        self.sw_warp.toggled.connect(lambda v: ctx.set_person2("face_warp", bool(v)))
        self.sw_eyes.toggled.connect(lambda v: ctx.set_person2("keep_eyes_mouth", bool(v)))

        self.populate()
        self.refresh()

    def populate(self) -> None:
        entries = [("", "Ninguno", empty_pixmap("mask"), False)]
        for mask in self.ctx.library.all():
            entries.append((mask.mask_id, mask.name, bgra_to_pixmap(mask.thumbnail(THUMB)), not mask.builtin))
        self.gallery.set_items(entries)
        self.gallery.select(self.ctx.settings.person2.active_mask)
        self._describe_mask(self.ctx.settings.person2.active_mask)
        acc_entries = [
            (m.mask_id, m.name, bgra_to_pixmap(m.thumbnail(THUMB)), not m.builtin)
            for m in self.ctx.library.accessories()
        ]
        self.acc_gallery.set_items(acc_entries, self.ctx.settings.person2.accessories)
        self._acc_selected(self.acc_gallery.current_id() or "")
        self.dist_gallery.select(self.ctx.settings.person2.distortion)
        self._describe_distortion(self.ctx.settings.person2.distortion)

    def select_mask(self, mask_id: str) -> None:
        self.ctx.set_person2("active_mask", mask_id)
        self.gallery.select(mask_id)
        self._describe_mask(mask_id)

    def add_and_enable_accessory(self, item_id: str) -> None:
        active = [a for a in self.ctx.settings.person2.accessories if a != item_id] + [item_id]
        self.ctx.set_person2("accessories", active)
        self.populate()
        self.acc_gallery.select(item_id)
        self._acc_selected(item_id)

    def refresh(self) -> None:
        p = self.ctx.settings.person2
        self.sw_dual.setChecked(self.ctx.settings.dual_faces)
        self.sl_scale.set_value(p.mask_scale * 100)
        self.sl_rotation.set_value(p.mask_rotation)
        self.sl_x.set_value(p.mask_offset_x * 100)
        self.sl_y.set_value(p.mask_offset_y * 100)
        self.sl_opacity.set_value(p.mask_opacity * 100)
        self.sl_color.set_value(p.color_match * 100)
        self.sl_light.set_value(p.light_match * 100)
        self.sl_soft.set_value(p.edge_softness * 100)
        self.sw_expr.setChecked(p.expression)
        self.sw_warp.setChecked(p.face_warp)
        self.sw_eyes.setChecked(p.keep_eyes_mouth)
        for key, slider in self.beauty_sliders.items():
            slider.set_value(getattr(p, key) * 100)
        self.dist_gallery.select(p.distortion)
        self.sl_dist_strength.set_value(p.distortion_strength * 100)
        self._describe_distortion(p.distortion)
        self.hint.setText(
            "Modo dos personas activo: cada quien mantiene su filtro."
            if self.ctx.settings.dual_faces
            else "Activa el interruptor de arriba para que los dos filtros se apliquen a la vez en la camara."
        )

    def _distortion_selected(self, preset_id: str) -> None:
        self.ctx.set_person2("distortion", preset_id)
        self._describe_distortion(preset_id)

    def _describe_distortion(self, preset_id: str) -> None:
        if not preset_id:
            self.dist_info.setText("Sin deformacion para esta persona.")
        else:
            self.dist_info.setText(f'"{DISTORTION_PRESETS[preset_id].name}" activo.')

    def _mask_selected(self, mask_id: str) -> None:
        self.ctx.set_person2("active_mask", mask_id)
        self._describe_mask(mask_id)

    def _describe_mask(self, mask_id: str) -> None:
        mask = self.ctx.library.get(mask_id) if mask_id else None
        self.delete.setVisible(mask is not None and not mask.builtin)
        if mask is None:
            self.info.setText("Sin filtro para esta persona.")
        elif mask.is_face:
            self.info.setText("Imagen con cara: se deforma sobre su rostro.")
        elif mask.anchors:
            self.info.setText("Mascara anclada a los puntos del rostro.")
        else:
            self.info.setText("Imagen superpuesta y centrada en su cara.")

    def _delete_mask(self) -> None:
        mask_id = self.gallery.current_id()
        if mask_id and self.ctx.library.remove(mask_id):
            if self.ctx.settings.person2.active_mask == mask_id:
                self.ctx.set_person2("active_mask", "")
            self.populate()
            self.ctx.notify("Filtro eliminado", "info")

    def _recalibrate(self) -> None:
        self.ctx.engine.recalibrate(2)
        self.ctx.notify("Pide a esa persona que mire de frente con la boca cerrada", "info")

    def _acc_toggled(self, item_id: str, state: bool) -> None:
        active = [a for a in self.ctx.settings.person2.accessories if a != item_id]
        if state:
            active.append(item_id)
        self.ctx.set_person2("accessories", active)

    def _acc_selected(self, item_id: str) -> None:
        item = self.ctx.library.get(item_id) if item_id else None
        for slider in (self.acc_scale, self.acc_rot, self.acc_x, self.acc_y):
            slider.setEnabled(item is not None)
        self.acc_delete.setVisible(item is not None and not item.builtin)
        if item is None:
            self.acc_target.setText("Selecciona un accesorio para ajustar su posicion.")
            return
        self.acc_target.setText(f"Ajustando: {item.name}")
        scale, rotation, dx, dy = self.ctx.settings.person2.accessory_adjust.get(item_id, DEFAULT_ADJUST)
        self.acc_scale.set_value(scale * 100)
        self.acc_rot.set_value(rotation)
        self.acc_x.set_value(dx * 100)
        self.acc_y.set_value(dy * 100)

    def _acc_adjust_changed(self, _value: float = 0.0) -> None:
        item_id = self.acc_gallery.current_id()
        if not item_id:
            return
        adjust = dict(self.ctx.settings.person2.accessory_adjust)
        adjust[item_id] = [
            self.acc_scale.value() / 100.0,
            self.acc_rot.value(),
            self.acc_x.value() / 100.0,
            self.acc_y.value() / 100.0,
        ]
        self.ctx.set_person2("accessory_adjust", adjust)

    def _acc_delete(self) -> None:
        item_id = self.acc_gallery.current_id()
        if item_id and self.ctx.library.remove(item_id):
            self.ctx.set_person2(
                "accessories", [a for a in self.ctx.settings.person2.accessories if a != item_id]
            )
            adjust = dict(self.ctx.settings.person2.accessory_adjust)
            adjust.pop(item_id, None)
            self.ctx.set_person2("accessory_adjust", adjust)
            self.populate()
            self.ctx.notify("Accesorio eliminado", "info")

    def _acc_clear(self) -> None:
        self.ctx.set_person2("accessories", [])
        self.acc_gallery.set_checked([])

    def tick(self) -> None:
        ready, progress = self.ctx.engine.calibration(2)
        faces = self.ctx.engine.faces_found
        if not self.ctx.settings.dual_faces:
            self.calib_status.setText("Activa el modo dos personas para calibrar")
        elif ready:
            self.calib_status.setText("Rostro calibrado")
        elif faces[1]:
            self.calib_status.setText(
                f"Calibrando... {int(progress * 100)} %  (que mire de frente, boca cerrada)"
            )
        else:
            self.calib_status.setText("Sin calibrar: se necesita una segunda cara frente a la camara")
