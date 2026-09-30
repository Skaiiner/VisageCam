import logging
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from visagecam.capture import RESOLUTIONS, list_cameras
from visagecam.config import Settings
from visagecam.obs import ObsClient
from visagecam.ui.components import (
    Card,
    Gallery,
    Segmented,
    SliderRow,
    SwitchRow,
    button,
    muted,
    pill,
    set_tone,
)
from visagecam.ui.context import Context
from visagecam.ui.icons import icon
from visagecam.ui.studio import IMAGE_FILTER
from visagecam.ui.widgets import bgra_to_pixmap

log = logging.getLogger(__name__)

THUMB = 112
DEFAULT_ADJUST = [1.0, 0.0, 0.0, 0.0]


class Page(QScrollArea):
    def __init__(self, ctx: Context) -> None:
        super().__init__()
        self.ctx = ctx
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        inner.setObjectName("page")
        self.setWidget(inner)
        self.column = QVBoxLayout(inner)
        self.column.setContentsMargins(4, 4, 12, 16)
        self.column.setSpacing(14)

    def finish(self) -> None:
        self.column.addStretch(1)

    def refresh(self) -> None:
        pass

    def tick(self) -> None:
        pass

    def shutdown(self) -> None:
        pass


def header(title: str, button_widget=None) -> QHBoxLayout:
    row = QHBoxLayout()
    label = QLabel(title)
    label.setObjectName("h1")
    row.addWidget(label)
    row.addStretch(1)
    if button_widget is not None:
        row.addWidget(button_widget)
    return row


def empty_pixmap(icon_name: str) -> QPixmap:
    return icon(icon_name, "#8b93a7", 48).pixmap(48, 48)


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
        self.sw_warp = SwitchRow("Deformar sobre mi rostro", "Para imagenes con cara: se adaptan punto a punto.")
        self.sw_eyes = SwitchRow("Conservar mis ojos y mi boca", "Se ven tus ojos y tu boca real a traves del filtro.")
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
        for key in ("mask_scale", "mask_rotation", "mask_offset_x", "mask_offset_y", "mask_opacity",
                    "color_match", "light_match", "edge_softness"):
            setattr(self.ctx.settings, key, getattr(defaults, key))
        self.ctx.save()
        self.refresh()

    def _recalibrate(self) -> None:
        self.ctx.engine.recalibrate()
        self.ctx.notify("Mira de frente con la boca cerrada un segundo", "info")

    def tick(self) -> None:
        ready, progress = self.ctx.engine.calibration
        if ready:
            self.calib_status.setText("Rostro calibrado")
        elif self.ctx.engine.face_found:
            self.calib_status.setText(f"Calibrando... {int(progress * 100)} %  (mira de frente, boca cerrada)")
        else:
            self.calib_status.setText("Sin calibrar: colocate frente a la camara")


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
        entries = [(m.mask_id, m.name, bgra_to_pixmap(m.thumbnail(THUMB)), not m.builtin) for m in self.ctx.library.accessories()]
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
        adjust[item_id] = [self.sl_scale.value() / 100.0, self.sl_rot.value(), self.sl_x.value() / 100.0, self.sl_y.value() / 100.0]
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
            small = cv2.resize(data, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA)
            bgra = cv2.cvtColor(small, cv2.COLOR_BGR2BGRA)
            entries.append((str(path), "Fondo", bgra_to_pixmap(bgra), True))
        self.gallery.set_items(entries)
        self.empty.setVisible(not entries)
        self.gallery.select(self.ctx.settings.background_image)
        self.delete.setVisible(self.gallery.current_id() is not None)

    def refresh(self) -> None:
        s = self.ctx.settings
        self.segment.set_value(s.background_mode if s.background_mode in ("none", "blur", "image") else "none")
        self.sl_blur.set_value(s.blur_strength)

    def _mode(self, value: object) -> None:
        mode = str(value)
        if mode == "image" and not (self.ctx.settings.background_image and Path(self.ctx.settings.background_image).is_file()):
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
        self.sw_hq = SwitchRow("Captura en alta calidad", "Captura a 1080p y reescala a 720p para una imagen mas nitida.")
        self.mirror = Segmented([("off", "Sin espejo"), ("preview", "Solo vista previa"), ("both", "Vista previa y salida")])
        self.mirror.changed.connect(lambda v: self._on_mirror(str(v)))
        self.sw_hq.toggled.connect(self._hq)
        cam.add(self.sw_hq)
        cam.add(self.mirror)
        cam.add(muted("Solo vista previa te muestra como en un espejo sin invertir lo que ven los demas. Vista previa y salida tambien invierte la camara virtual."))
        self.sl_enhance = SliderRow("Mejora de imagen", 0, 100, 50, 1, " %")
        self.sl_enhance.changed.connect(lambda v: ctx.set("enhance", v / 100.0))
        cam.add(self.sl_enhance)
        self.column.addWidget(cam)

        out = Card("Salida", "Donde aparece tu camara en otras aplicaciones.")
        self.backend = Segmented([("auto", "Automatica"), ("unitycapture", "VisageCam"), ("obs", "OBS Virtual Camera")])
        self.backend.changed.connect(lambda v: ctx.set("virtual_backend", str(v)))
        out.add(self.backend)
        out.add(muted("VisageCam aparece como fuente de video en OBS (requiere el controlador Unity Capture). OBS Virtual Camera funciona en Discord, Zoom, Skype y Teams."))
        self.column.addWidget(out)

        stream = Card("Fuente para OBS sin controladores", "En OBS anade una Fuente multimedia, desmarca Archivo local y pega esta direccion.")
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
        self.backend.set_value(s.virtual_backend if s.virtual_backend in ("auto", "unitycapture", "obs") else "auto")
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


class ObsPage(Page):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        self.obs = ObsClient(ctx.settings.obs_host, ctx.settings.obs_port, ctx.settings.obs_password)
        self._scene_items: list = []
        self._updating = False
        status_row = pill("Desconectado")
        self.status = status_row
        self.column.addLayout(header("OBS Studio", status_row))

        conn = Card("Conexion", "En OBS: Herramientas > Ajustes del servidor WebSocket.")
        host_row = QHBoxLayout()
        self.host = QLineEdit(ctx.settings.obs_host)
        self.host.setPlaceholderText("Servidor")
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(ctx.settings.obs_port)
        self.port.setFixedWidth(90)
        self.port.setButtonSymbols(QSpinBox.NoButtons)
        host_row.addWidget(self.host, 1)
        host_row.addWidget(self.port)
        conn.add(layout=host_row)
        self.password = QLineEdit(ctx.settings.obs_password)
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("Contrasena")
        conn.add(self.password)
        self.connect_button = button("Conectar", "primary", "plug", "#0b0d12")
        self.connect_button.clicked.connect(self._toggle)
        conn.add(self.connect_button)
        self.message = muted("")
        conn.add(self.message)
        self.column.addWidget(conn)

        self.scenes_card = Card("Escenas", "Doble clic en una escena para cambiar a ella.")
        self.scenes = QListWidget()
        self.scenes.setObjectName("plain")
        self.scenes.setFixedHeight(130)
        self.scenes.currentItemChanged.connect(lambda *_: self._load_items())
        self.scenes.itemDoubleClicked.connect(lambda _i: self._switch())
        self.scenes_card.add(self.scenes)
        switch = button("Cambiar a la escena seleccionada", "ghost", "play")
        switch.clicked.connect(self._switch)
        self.scenes_card.add(switch)
        self.column.addWidget(self.scenes_card)

        self.items_card = Card("Fuentes de la escena", "Activa o desactiva fuentes al instante.")
        self.items_box = QVBoxLayout()
        self.items_box.setSpacing(10)
        self.items_card.add(layout=self.items_box)
        add = button("Anadir camara VisageCam a la escena", "ghost", "camera")
        add.clicked.connect(self._add_camera)
        self.items_card.add(add)
        self.column.addWidget(self.items_card)
        self.finish()
        self._set_connected(False)

    def shutdown(self) -> None:
        self.obs.disconnect()

    def _set_connected(self, connected: bool) -> None:
        self.scenes_card.setEnabled(connected)
        self.items_card.setEnabled(connected)
        self.status.setText("Conectado" if connected else "Desconectado")
        set_tone(self.status, "ok" if connected else "")
        self.connect_button.setText("Desconectar" if connected else "Conectar")

    def _toggle(self) -> None:
        if self.obs.connected:
            self.obs.disconnect()
            self._set_connected(False)
            self.message.setText("")
            return
        s = self.ctx.settings
        self.obs.host = self.host.text().strip() or "localhost"
        self.obs.port = self.port.value()
        self.obs.password = self.password.text()
        s.obs_host, s.obs_port, s.obs_password = self.obs.host, self.obs.port, self.obs.password
        self.ctx.save()
        self.connect_button.setEnabled(False)
        self.message.setText("Conectando...")

        def work():
            self.obs.connect()
            return self.obs.list_scenes()

        self.ctx.runner.run(work, self._connected, self._failed)

    def _connected(self, result) -> None:
        scenes, current = result
        self.connect_button.setEnabled(True)
        self._set_connected(True)
        self.message.setText(f"OBS {self.obs.obs_version}. Escena activa: {current}")
        self._updating = True
        self.scenes.clear()
        for name in scenes:
            entry = QListWidgetItem(name)
            self.scenes.addItem(entry)
            if name == current:
                self.scenes.setCurrentItem(entry)
        self._updating = False
        self._load_items()

    def _failed(self, message: str) -> None:
        self.connect_button.setEnabled(True)
        self._set_connected(False)
        self.message.setText(message)
        set_tone(self.status, "danger")
        self.status.setText("Error")
        self.ctx.notify(message, "error")

    def _scene(self) -> str:
        item = self.scenes.currentItem()
        return item.text() if item else ""

    def _load_items(self) -> None:
        scene = self._scene()
        if not scene or self._updating or not self.obs.connected:
            return
        self.ctx.runner.run(lambda: self.obs.list_items(scene), self._show_items, self._failed)

    def _show_items(self, items) -> None:
        while self.items_box.count():
            entry = self.items_box.takeAt(0)
            if entry.widget() is not None:
                entry.widget().deleteLater()
        if not items:
            self.items_box.addWidget(muted("Esta escena no tiene fuentes."))
        for item in items:
            row = SwitchRow(item.name)
            row.setChecked(item.enabled)
            row.toggled.connect(lambda state, i=item.item_id: self._toggle_item(i, state))
            self.items_box.addWidget(row)

    def _toggle_item(self, item_id: int, state: bool) -> None:
        scene = self._scene()
        self.ctx.runner.run(
            lambda: self.obs.set_item_enabled(scene, item_id, state),
            None,
            lambda message: (self.ctx.notify(message, "error"), self._load_items()),
        )

    def _switch(self) -> None:
        scene = self._scene()
        if not scene:
            return
        self.ctx.runner.run(
            lambda: self.obs.set_scene(scene),
            lambda _r: (self.message.setText(f"Escena activa: {scene}"), self.ctx.notify(f"Escena: {scene}", "ok")),
            self._failed,
        )

    def _add_camera(self) -> None:
        scene = self._scene()
        if not scene:
            return
        url = self.ctx.engine.stream.url
        self.ctx.runner.run(
            lambda: self.obs.add_camera_source(scene, stream_url=url),
            lambda label: (self.ctx.notify(f"Camara anadida a {scene} ({label})", "ok"), self._load_items()),
            lambda message: self.ctx.notify(message, "error"),
        )
