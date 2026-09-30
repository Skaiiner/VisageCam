import logging
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from visagecam.capture import RESOLUTIONS, CameraError, list_cameras
from visagecam.config import Settings
from visagecam.masks.library import MaskLibrary
from visagecam.obs import ObsClient, ObsError
from visagecam.output import VirtualCameraError
from visagecam.processing.engine import Engine
from visagecam.ui.widgets import AsyncRunner, SliderRow, bgr_to_qimage, bgra_to_qimage

log = logging.getLogger(__name__)

IMAGE_FILTER = "Imagenes (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)"
THUMB = 96


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, library: MaskLibrary, engine: Engine) -> None:
        super().__init__()
        self.settings = settings
        self.library = library
        self.engine = engine
        self.obs = ObsClient(settings.obs_host, settings.obs_port, settings.obs_password)
        self.runner = AsyncRunner(self)
        self._last_frame_id = -1
        self._obs_items: list = []
        self.setWindowTitle("VisageCam")
        self.resize(1240, 760)

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(600)
        self._save_timer.timeout.connect(self.settings.save)

        self._build_ui()
        self._populate_masks()
        self._refresh_cameras()
        self._sync_controls()

        self._frame_timer = QTimer(self)
        self._frame_timer.setInterval(33)
        self._frame_timer.timeout.connect(self._tick)
        self._frame_timer.start()
        QTimer.singleShot(100, self._start_camera)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        left = QVBoxLayout()
        self.preview = QLabel("Iniciando camara...")
        self.preview.setObjectName("preview")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(560, 315)
        left.addWidget(self.preview, 1)
        self.status = QLabel("")
        self.status.setObjectName("hint")
        left.addWidget(self.status)
        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Salida"))
        self.backend_combo = QComboBox()
        self.backend_combo.addItem("Automatica", "auto")
        self.backend_combo.addItem("VisageCam (Unity Capture) - visible en OBS", "unitycapture")
        self.backend_combo.addItem("OBS Virtual Camera - solo para otras apps", "obs")
        self.backend_combo.activated.connect(lambda _: self._set("virtual_backend", self.backend_combo.currentData()))
        output_row.addWidget(self.backend_combo, 1)
        left.addLayout(output_row)
        self.virtual_button = QPushButton("Iniciar camara virtual")
        self.virtual_button.setObjectName("primary")
        self.virtual_button.setCheckable(True)
        self.virtual_button.toggled.connect(self._toggle_virtual)
        left.addWidget(self.virtual_button)
        root.addLayout(left, 3)

        right = QVBoxLayout()
        right.addWidget(self._build_camera_box())
        tabs = QTabWidget()
        tabs.addTab(self._build_masks_tab(), "Mascaras")
        tabs.addTab(self._build_background_tab(), "Fondo")
        tabs.addTab(self._build_obs_tab(), "OBS")
        right.addWidget(tabs, 1)
        container = QWidget()
        container.setLayout(right)
        container.setFixedWidth(430)
        root.addWidget(container)

    def _build_camera_box(self) -> QGroupBox:
        box = QGroupBox("Camara")
        form = QFormLayout(box)
        row = QHBoxLayout()
        self.camera_combo = QComboBox()
        refresh = QPushButton("Actualizar")
        refresh.clicked.connect(self._refresh_cameras)
        row.addWidget(self.camera_combo, 1)
        row.addWidget(refresh)
        form.addRow("Dispositivo", row)
        self.resolution_combo = QComboBox()
        for width, height in RESOLUTIONS:
            self.resolution_combo.addItem(f"{width} x {height}", (width, height))
        form.addRow("Resolucion", self.resolution_combo)
        self.mirror_check = QCheckBox("Espejo")
        form.addRow("", self.mirror_check)
        self.camera_combo.activated.connect(self._camera_changed)
        self.resolution_combo.activated.connect(self._camera_changed)
        self.mirror_check.toggled.connect(lambda v: self._set("mirror", bool(v)))
        return box

    def _build_masks_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.mask_list = QListWidget()
        self.mask_list.setViewMode(QListView.IconMode)
        self.mask_list.setIconSize(QSize(THUMB, THUMB))
        self.mask_list.setResizeMode(QListView.Adjust)
        self.mask_list.setMovement(QListView.Static)
        self.mask_list.setSpacing(6)
        self.mask_list.setMinimumHeight(190)
        self.mask_list.setMaximumHeight(230)
        self.mask_list.currentItemChanged.connect(self._mask_selected)
        layout.addWidget(self.mask_list)

        buttons = QHBoxLayout()
        load = QPushButton("Cargar imagen...")
        load.setToolTip("Usa cualquier imagen como filtro: fotos con rostro, PNG con transparencia o dibujos")
        load.clicked.connect(self._import_image)
        self.delete_button = QPushButton("Eliminar")
        self.delete_button.clicked.connect(self._delete_mask)
        buttons.addWidget(load, 1)
        buttons.addWidget(self.delete_button)
        layout.addLayout(buttons)
        self.mask_info = QLabel("")
        self.mask_info.setObjectName("hint")
        self.mask_info.setWordWrap(True)
        layout.addWidget(self.mask_info)

        self.sl_scale = SliderRow("Escala", 20, 300, 100, 1, " %")
        self.sl_rotation = SliderRow("Rotacion", -180, 180, 0, 1, " grados")
        self.sl_x = SliderRow("Desplaz. X", -100, 100, 0, 1)
        self.sl_y = SliderRow("Desplaz. Y", -100, 100, 0, 1)
        self.sl_opacity = SliderRow("Opacidad", 0, 100, 100, 1, " %")
        self.sl_color = SliderRow("Ajuste color", 0, 100, 85, 1, " %")
        self.sl_light = SliderRow("Ajuste luz", 0, 100, 60, 1, " %")
        self.sl_soft = SliderRow("Bordes suaves", 0, 100, 30, 1, " %")
        self.sl_scale.changed.connect(lambda v: self._set("mask_scale", v / 100.0))
        self.sl_rotation.changed.connect(lambda v: self._set("mask_rotation", v))
        self.sl_x.changed.connect(lambda v: self._set("mask_offset_x", v / 100.0))
        self.sl_y.changed.connect(lambda v: self._set("mask_offset_y", v / 100.0))
        self.sl_opacity.changed.connect(lambda v: self._set("mask_opacity", v / 100.0))
        self.sl_color.changed.connect(lambda v: self._set("color_match", v / 100.0))
        self.sl_light.changed.connect(lambda v: self._set("light_match", v / 100.0))
        self.sl_soft.changed.connect(lambda v: self._set("edge_softness", v / 100.0))
        for slider in (self.sl_scale, self.sl_rotation, self.sl_x, self.sl_y, self.sl_opacity,
                       self.sl_color, self.sl_light, self.sl_soft):
            layout.addWidget(slider)

        self.warp_check = QCheckBox("Deformar la imagen sobre mi rostro (si tiene cara)")
        self.eyes_check = QCheckBox("Conservar mis ojos y mi boca")
        self.warp_check.toggled.connect(lambda v: self._set("face_warp", bool(v)))
        self.eyes_check.toggled.connect(lambda v: self._set("keep_eyes_mouth", bool(v)))
        layout.addWidget(self.warp_check)
        layout.addWidget(self.eyes_check)
        reset = QPushButton("Restablecer ajustes")
        reset.clicked.connect(self._reset_adjustments)
        layout.addWidget(reset)
        layout.addStretch(1)
        return page

    def _build_background_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.bg_none = QRadioButton("Sin cambios")
        self.bg_blur = QRadioButton("Desenfocar fondo")
        self.bg_image = QRadioButton("Imagen propia")
        group = QButtonGroup(page)
        for index, button in enumerate((self.bg_none, self.bg_blur, self.bg_image)):
            group.addButton(button, index)
            layout.addWidget(button)
        group.idClicked.connect(self._background_mode)
        self.sl_blur = SliderRow("Desenfoque", 5, 100, 40, 1)
        self.sl_blur.changed.connect(lambda v: self._set("blur_strength", int(v)))
        layout.addWidget(self.sl_blur)
        row = QHBoxLayout()
        pick = QPushButton("Elegir imagen...")
        pick.clicked.connect(self._pick_background)
        self.bg_path = QLabel("")
        self.bg_path.setObjectName("hint")
        row.addWidget(pick)
        row.addWidget(self.bg_path, 1)
        layout.addLayout(row)
        layout.addStretch(1)
        return page

    def _build_obs_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.obs_host = QLineEdit(self.settings.obs_host)
        self.obs_port = QSpinBox()
        self.obs_port.setRange(1, 65535)
        self.obs_port.setValue(self.settings.obs_port)
        self.obs_password = QLineEdit(self.settings.obs_password)
        self.obs_password.setEchoMode(QLineEdit.Password)
        form.addRow("Servidor", self.obs_host)
        form.addRow("Puerto", self.obs_port)
        form.addRow("Contrasena", self.obs_password)
        layout.addLayout(form)
        self.obs_connect = QPushButton("Conectar")
        self.obs_connect.clicked.connect(self._obs_toggle)
        layout.addWidget(self.obs_connect)
        self.obs_status = QLabel("Desconectado")
        self.obs_status.setObjectName("hint")
        self.obs_status.setWordWrap(True)
        layout.addWidget(self.obs_status)

        self.scene_combo = QComboBox()
        self.scene_combo.activated.connect(self._obs_scene_view)
        layout.addWidget(QLabel("Escena"))
        layout.addWidget(self.scene_combo)
        switch = QPushButton("Cambiar a esta escena")
        switch.clicked.connect(self._obs_switch_scene)
        layout.addWidget(switch)
        layout.addWidget(QLabel("Fuentes de la escena (marca para activar)"))
        add_source = QPushButton("Anadir camara VisageCam a la escena")
        add_source.setToolTip("Crea en OBS un Dispositivo de captura de video con la camara de VisageCam")
        add_source.clicked.connect(self._obs_add_camera)
        layout.addWidget(add_source)
        self.item_list = QListWidget()
        self.item_list.itemChanged.connect(self._obs_item_toggled)
        layout.addWidget(self.item_list, 1)
        self._set_obs_enabled(False)
        return page

    def _set(self, key: str, value) -> None:
        setattr(self.settings, key, value)
        self._save_timer.start()

    def _sync_controls(self) -> None:
        s = self.settings
        self.sl_scale.set_value(s.mask_scale * 100)
        self.sl_rotation.set_value(s.mask_rotation)
        self.sl_x.set_value(s.mask_offset_x * 100)
        self.sl_y.set_value(s.mask_offset_y * 100)
        self.sl_opacity.set_value(s.mask_opacity * 100)
        self.sl_color.set_value(s.color_match * 100)
        self.sl_light.set_value(s.light_match * 100)
        self.sl_soft.set_value(s.edge_softness * 100)
        self.sl_blur.set_value(s.blur_strength)
        self.warp_check.setChecked(s.face_warp)
        self.eyes_check.setChecked(s.keep_eyes_mouth)
        self.mirror_check.setChecked(s.mirror)
        self.backend_combo.setCurrentIndex(max(self.backend_combo.findData(s.virtual_backend), 0))
        {"none": self.bg_none, "blur": self.bg_blur, "image": self.bg_image}.get(
            s.background_mode, self.bg_none
        ).setChecked(True)
        self.bg_path.setText(Path(s.background_image).name if s.background_image else "")
        for index, (width, height) in enumerate(RESOLUTIONS):
            if (width, height) == (s.width, s.height):
                self.resolution_combo.setCurrentIndex(index)

    def _reset_adjustments(self) -> None:
        defaults = Settings()
        for key in ("mask_scale", "mask_rotation", "mask_offset_x", "mask_offset_y", "mask_opacity",
                    "color_match", "light_match", "edge_softness"):
            setattr(self.settings, key, getattr(defaults, key))
        self._sync_controls()
        self._save_timer.start()

    def _populate_masks(self) -> None:
        self.mask_list.blockSignals(True)
        self.mask_list.clear()
        none = QListWidgetItem("Ninguna")
        none.setData(Qt.UserRole, "")
        none.setSizeHint(QSize(THUMB + 20, THUMB + 34))
        self.mask_list.addItem(none)
        for mask in self.library.all():
            item = QListWidgetItem(QIcon(QPixmap.fromImage(bgra_to_qimage(mask.thumbnail(THUMB)))), mask.name)
            item.setData(Qt.UserRole, mask.mask_id)
            item.setSizeHint(QSize(THUMB + 20, THUMB + 34))
            item.setTextAlignment(Qt.AlignHCenter)
            self.mask_list.addItem(item)
        self.mask_list.blockSignals(False)
        self._select_mask(self.settings.active_mask)

    def _select_mask(self, mask_id: str) -> None:
        for row in range(self.mask_list.count()):
            item = self.mask_list.item(row)
            if item.data(Qt.UserRole) == mask_id:
                self.mask_list.setCurrentItem(item)
                return
        self.mask_list.setCurrentRow(0)

    def _mask_selected(self, item: QListWidgetItem | None) -> None:
        mask_id = item.data(Qt.UserRole) if item else ""
        self._set("active_mask", mask_id)
        mask = self.library.get(mask_id) if mask_id else None
        self.delete_button.setEnabled(mask is not None and not mask.builtin)
        if mask is None:
            self.mask_info.setText("Sin mascara: se envia tu imagen sin filtro.")
        elif mask.is_face:
            self.mask_info.setText("Rostro detectado en la imagen: se deforma sobre tu cara punto a punto.")
        elif mask.anchors:
            self.mask_info.setText("Mascara anclada a los puntos del Face Mesh.")
        else:
            self.mask_info.setText("Imagen superpuesta y centrada en tu cara. Ajusta escala y posicion.")

    def _import_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Elegir imagen", "", IMAGE_FILTER)
        if not path:
            return
        self.mask_info.setText("Analizando imagen...")
        self.runner.run(
            lambda: self.library.import_image(Path(path)),
            self._import_done,
            lambda message: QMessageBox.warning(self, "VisageCam", f"No se pudo importar la imagen:\n{message}"),
        )

    def _import_done(self, mask) -> None:
        self._populate_masks()
        self._select_mask(mask.mask_id)

    def _delete_mask(self) -> None:
        item = self.mask_list.currentItem()
        mask_id = item.data(Qt.UserRole) if item else ""
        if mask_id and self.library.remove(mask_id):
            self._set("active_mask", "")
            self._populate_masks()

    def _background_mode(self, index: int) -> None:
        mode = ("none", "blur", "image")[index]
        if mode == "image" and not self.settings.background_image:
            if not self._pick_background():
                self.bg_none.setChecked(True)
                return
        self._set("background_mode", mode)

    def _pick_background(self) -> bool:
        path, _ = QFileDialog.getOpenFileName(self, "Imagen de fondo", "", IMAGE_FILTER)
        if not path:
            return False
        self._set("background_image", path)
        self.bg_path.setText(Path(path).name)
        return True

    def _refresh_cameras(self) -> None:
        self.camera_combo.clear()
        for device in list_cameras():
            self.camera_combo.addItem(device.name, device.index)
        index = self.camera_combo.findData(self.settings.camera_index)
        if index >= 0:
            self.camera_combo.setCurrentIndex(index)
        elif self.camera_combo.count():
            self.settings.camera_index = self.camera_combo.itemData(0)

    def _camera_changed(self) -> None:
        if self.camera_combo.currentData() is not None:
            self.settings.camera_index = int(self.camera_combo.currentData())
        width, height = RESOLUTIONS[self.resolution_combo.currentIndex()]
        self.settings.width, self.settings.height = width, height
        self._save_timer.start()
        self._start_camera()

    def _start_camera(self) -> None:
        was_virtual = self.virtual_button.isChecked()
        if was_virtual:
            self.virtual_button.setChecked(False)
        try:
            self.engine.start()
        except CameraError as exc:
            self.preview.setText(str(exc))
            return
        if was_virtual:
            self.virtual_button.setChecked(True)

    def _toggle_virtual(self, checked: bool) -> None:
        if checked:
            if not self.engine.running:
                self.virtual_button.setChecked(False)
                return
            try:
                self.engine.start_virtual()
            except VirtualCameraError as exc:
                self.virtual_button.blockSignals(True)
                self.virtual_button.setChecked(False)
                self.virtual_button.blockSignals(False)
                QMessageBox.critical(self, "VisageCam", str(exc))
                return
            self.virtual_button.setText("Detener camara virtual")
        else:
            self.engine.stop_virtual()
            self.virtual_button.setText("Iniciar camara virtual")

    def _tick(self) -> None:
        frame_id, frame = self.engine.latest()
        if frame is not None and frame_id != self._last_frame_id:
            self._last_frame_id = frame_id
            pixmap = QPixmap.fromImage(bgr_to_qimage(frame))
            self.preview.setPixmap(
                pixmap.scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.FastTransformation)
            )
        parts = [f"{self.engine.fps:4.1f} fps", f"{self.engine.process_ms:4.1f} ms"]
        if self.settings.active_mask:
            parts.append("rostro detectado" if self.engine.face_found else "sin rostro")
        if self.engine.virtual_active:
            parts.append(f"emitiendo en {self.engine.output.device}")
        if self.engine.error:
            parts.append(self.engine.error)
        self.status.setText("  |  ".join(parts))
        if self.virtual_button.isChecked() and not self.engine.virtual_active:
            self.virtual_button.setChecked(False)

    def _set_obs_enabled(self, enabled: bool) -> None:
        for widget in (self.scene_combo, self.item_list):
            widget.setEnabled(enabled)

    def _obs_toggle(self) -> None:
        if self.obs.connected:
            self.obs.disconnect()
            self.obs_connect.setText("Conectar")
            self.obs_status.setText("Desconectado")
            self._set_obs_enabled(False)
            return
        self.obs.host = self.obs_host.text().strip() or "localhost"
        self.obs.port = self.obs_port.value()
        self.obs.password = self.obs_password.text()
        self.settings.obs_host, self.settings.obs_port = self.obs.host, self.obs.port
        self.settings.obs_password = self.obs.password
        self._save_timer.start()
        self.obs_status.setText("Conectando...")

        def work():
            self.obs.connect()
            return self.obs.list_scenes()

        self.runner.run(work, self._obs_connected, self._obs_failed)

    def _obs_connected(self, result) -> None:
        scenes, current = result
        self.obs_connect.setText("Desconectar")
        self.obs_status.setText(f"Conectado a OBS {self.obs.obs_version}. Escena activa: {current}")
        self._set_obs_enabled(True)
        self.scene_combo.clear()
        self.scene_combo.addItems(scenes)
        self.scene_combo.setCurrentText(current)
        self._obs_scene_view()

    def _obs_failed(self, message: str) -> None:
        self.obs_status.setText(message)

    def _obs_scene_view(self) -> None:
        scene = self.scene_combo.currentText()
        if not scene:
            return
        self.runner.run(lambda: self.obs.list_items(scene), self._obs_show_items, self._obs_failed)

    def _obs_show_items(self, items) -> None:
        self._obs_items = items
        self.item_list.blockSignals(True)
        self.item_list.clear()
        for entry in items:
            row = QListWidgetItem(entry.name)
            row.setFlags(row.flags() | Qt.ItemIsUserCheckable)
            row.setCheckState(Qt.Checked if entry.enabled else Qt.Unchecked)
            row.setData(Qt.UserRole, entry.item_id)
            self.item_list.addItem(row)
        self.item_list.blockSignals(False)

    def _obs_switch_scene(self) -> None:
        scene = self.scene_combo.currentText()
        if not scene:
            return
        self.runner.run(
            lambda: self.obs.set_scene(scene),
            lambda _: self.obs_status.setText(f"Escena activa: {scene}"),
            self._obs_failed,
        )

    def _obs_add_camera(self) -> None:
        scene = self.scene_combo.currentText()
        if not scene:
            return
        self.obs_status.setText("Anadiendo camara a OBS...")
        self.runner.run(
            lambda: self.obs.add_camera_source(scene),
            lambda name: (self.obs_status.setText(f"Camara anadida a la escena {scene} ({name})"), self._obs_scene_view()),
            self._obs_failed,
        )

    def _obs_item_toggled(self, row: QListWidgetItem) -> None:
        scene = self.scene_combo.currentText()
        item_id = row.data(Qt.UserRole)
        enabled = row.checkState() == Qt.Checked
        self.runner.run(
            lambda: self.obs.set_item_enabled(scene, item_id, enabled),
            None,
            lambda message: (self.obs_status.setText(message), self._obs_scene_view()),
        )

    def closeEvent(self, event) -> None:
        self._frame_timer.stop()
        self.obs.disconnect()
        self.engine.shutdown()
        self.settings.save()
        super().closeEvent(event)
