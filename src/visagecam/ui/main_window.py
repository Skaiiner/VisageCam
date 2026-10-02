import logging
from pathlib import Path

import cv2

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from visagecam.backgrounds import BackgroundLibrary
from visagecam.config import Settings
from visagecam.masks.library import MaskLibrary
from visagecam.output import VirtualCameraError
from visagecam.processing.engine import Engine
from visagecam.ui.components import PreviewWidget, Segmented, Toast, button, pill, set_tone
from visagecam.ui.context import Context
from visagecam.ui.icons import icon
from visagecam.ui.pages import (
    AccessoriesPage,
    BackgroundPage,
    BeautyPage,
    CameraPage,
    DistortionPage,
    FiltersPage,
    ObsPage,
    Person2Page,
)
from visagecam.ui.studio import ImageStudio, first_image_path
from visagecam.ui.theme import enable_dark_titlebar
from visagecam.ui.widgets import AsyncRunner

log = logging.getLogger(__name__)

RETRY_SECONDS = 3.0
NAV_ICONS = {
    "filters": "mask",
    "distortion": "sliders",
    "accessories": "hat",
    "beauty": "sparkle",
    "person2": "face",
    "background": "image",
    "camera": "camera",
    "obs": "plug",
}


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings, library: MaskLibrary, engine: Engine) -> None:
        super().__init__()
        self.settings = settings
        self.library = library
        self.engine = engine
        self._last_frame_id = -1
        self._camera_wanted = True
        self._starting = False
        self._retry_elapsed = 0.0
        self.setWindowTitle("VisageCam")
        self.resize(1320, 800)
        self.setMinimumSize(1100, 660)
        self.setAcceptDrops(True)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        self.toast = Toast(root)

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self.settings.save)

        self.ctx = Context(
            settings=settings,
            library=library,
            backgrounds=BackgroundLibrary(),
            engine=engine,
            runner=AsyncRunner(self),
            notify=self.notify,
            save=self._save_timer.start,
        )

        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())
        layout.addWidget(self._build_main(), 1)

        self._frame_timer = QTimer(self)
        self._frame_timer.setInterval(16)
        self._frame_timer.timeout.connect(self._tick)
        self._frame_timer.start()
        self._slow_timer = QTimer(self)
        self._slow_timer.setInterval(500)
        self._slow_timer.timeout.connect(self._slow_tick)
        self._slow_timer.start()
        QTimer.singleShot(150, self._start_camera)

    def _build_sidebar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("sidebar")
        bar.setFixedWidth(92)
        col = QVBoxLayout(bar)
        col.setContentsMargins(8, 16, 8, 14)
        col.setSpacing(6)
        logo = QLabel("VC")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(48, 48)
        logo.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #7c6cff, stop:1 #35c7f0);"
            "border-radius: 14px; color: #0b0d12; font-weight: 800; font-size: 17px;"
        )
        col.addWidget(logo, 0, Qt.AlignHCenter)
        col.addSpacing(14)
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: dict[str, QToolButton] = {}
        for key, label in (
            ("filters", "Filtros"),
            ("distortion", "Deformar"),
            ("accessories", "Accesorios"),
            ("beauty", "Belleza"),
            ("person2", "Persona 2"),
            ("background", "Fondo"),
            ("camera", "Camara"),
            ("obs", "OBS"),
        ):
            btn = QToolButton()
            btn.setObjectName("nav")
            btn.setText(label)
            btn.setIcon(icon(NAV_ICONS[key], "#b4bbcd", 26))
            btn.setIconSize(QSize(26, 26))
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(76, 64)
            self.nav_group.addButton(btn)
            self.nav_buttons[key] = btn
            col.addWidget(btn, 0, Qt.AlignHCenter)
            btn.clicked.connect(lambda _=False, k=key: self.show_page(k))
        col.addStretch(1)
        return bar

    def _build_main(self) -> QWidget:
        main = QWidget()
        outer = QVBoxLayout(main)
        outer.setContentsMargins(20, 14, 16, 16)
        outer.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("VisageCam")
        title.setObjectName("h1")
        top.addWidget(title)
        top.addStretch(1)
        self.pill_fps = pill("0 fps")
        self.pill_face = pill("Sin filtros")
        self.pill_out = pill("Camara virtual apagada")
        for p in (self.pill_fps, self.pill_face, self.pill_out):
            top.addWidget(p)
        outer.addLayout(top)

        body = QHBoxLayout()
        body.setSpacing(18)
        left = QVBoxLayout()
        left.setSpacing(12)
        self.preview = PreviewWidget()
        left.addWidget(self.preview, 1)
        self.mirror_bar = Segmented([("off", "Sin espejo"), ("preview", "Espejo en vista previa"), ("both", "Espejo total")])
        self.mirror_bar.set_value(self.settings.mirror_mode)
        self.mirror_bar.changed.connect(lambda v: self.set_mirror(str(v)))
        left.addWidget(self.mirror_bar)
        self.virtual_button = button("Iniciar camara virtual", "primary", "play", "#0b0d12")
        self.virtual_button.setCheckable(True)
        self.virtual_button.setMinimumHeight(48)
        self.virtual_button.toggled.connect(self._toggle_virtual)
        left.addWidget(self.virtual_button)
        body.addLayout(left, 1)

        self.stack = QStackedWidget()
        self.stack.setFixedWidth(430)
        self.filters = FiltersPage(self.ctx, lambda kind: self.open_studio(kind, 1))
        self.distortion = DistortionPage(self.ctx)
        self.accessories = AccessoriesPage(self.ctx, lambda kind: self.open_studio(kind, 1))
        self.beauty = BeautyPage(self.ctx)
        self.person2 = Person2Page(self.ctx, self.open_studio)
        self.background = BackgroundPage(self.ctx)
        self.camera = CameraPage(self.ctx, self._camera_changed)
        self.obs = ObsPage(self.ctx)
        self.camera.on_mirror = self._mirror_synced
        self.pages = {
            "filters": self.filters,
            "distortion": self.distortion,
            "accessories": self.accessories,
            "beauty": self.beauty,
            "person2": self.person2,
            "background": self.background,
            "camera": self.camera,
            "obs": self.obs,
        }
        for page in self.pages.values():
            self.stack.addWidget(page)
        body.addWidget(self.stack)
        outer.addLayout(body, 1)
        self.show_page("filters")
        return main

    def set_mirror(self, mode: str) -> None:
        self.ctx.set("mirror_mode", mode)
        self.camera.mirror.set_value(mode)
        self.notify({"off": "Espejo desactivado", "preview": "Espejo solo en la vista previa",
                     "both": "Espejo en vista previa y salida"}.get(mode, ""), "info")

    def _mirror_synced(self, mode: str) -> None:
        self.mirror_bar.set_value(mode)

    def show_page(self, key: str) -> None:
        self.stack.setCurrentWidget(self.pages[key])
        self.nav_buttons[key].setChecked(True)
        for name, btn in self.nav_buttons.items():
            btn.setIcon(icon(NAV_ICONS[name], "#ffffff" if name == key else "#b4bbcd", 26))

    def notify(self, message: str, tone: str = "info") -> None:
        self.toast.show_message(message, tone)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.toast.reposition()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        enable_dark_titlebar(self)

    def open_studio(self, kind: str = "mask", person: int = 1, path: Path | None = None) -> None:
        dialog = ImageStudio(self.ctx, self, kind, path)
        enable_dark_titlebar(dialog)
        if dialog.exec() != QDialog.Accepted or dialog.result_item is None:
            return
        item = dialog.result_item
        if person == 2:
            if item.kind == "mask":
                self.person2.populate()
                self.person2.select_mask(item.mask_id)
            else:
                self.person2.add_and_enable_accessory(item.mask_id)
            self.show_page("person2")
        elif item.kind == "mask":
            self.filters.populate()
            self.filters.select(item.mask_id)
            self.show_page("filters")
        else:
            self.accessories.add_and_enable(item.mask_id)
            self.show_page("accessories")
        self.notify(f"\"{item.name}\" anadido", "ok")

    def dragEnterEvent(self, event) -> None:
        if first_image_path(event.mimeData()) is not None:
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        path = first_image_path(event.mimeData())
        if path is not None:
            event.acceptProposedAction()
            current = self.stack.currentWidget()
            person = 2 if current is self.person2 else 1
            kind = "accessory" if current is self.accessories else "mask"
            QTimer.singleShot(0, lambda: self.open_studio(kind, person, path))

    def _camera_changed(self) -> None:
        self._camera_wanted = True
        self._start_camera()

    def _start_camera(self) -> None:
        if self._starting:
            return
        self._starting = True
        was_virtual = self.virtual_button.isChecked()
        if was_virtual:
            self._set_virtual_button(False)
            self.engine.stop_virtual()
        if not self.preview.has_image:
            self.preview.clear("Abriendo la camara...")
        self.ctx.runner.run(
            self.engine.start,
            lambda _r: self._camera_started(was_virtual),
            self._camera_failed,
        )

    def _camera_started(self, was_virtual: bool) -> None:
        self._starting = False
        self._last_frame_id = -1
        if was_virtual:
            self.virtual_button.setChecked(True)

    def _camera_failed(self, message: str) -> None:
        self._starting = False
        self.preview.live = False
        self.preview.clear(f"{message}\n\nComprueba que la camara esta conectada y que ninguna otra aplicacion la usa.")

    def _toggle_virtual(self, checked: bool) -> None:
        if checked:
            if not self.engine.running:
                self._set_virtual_button(False)
                self.notify("Primero hace falta una camara activa", "warn")
                return
            try:
                self.engine.start_virtual()
            except VirtualCameraError as exc:
                self._set_virtual_button(False)
                self.notify(str(exc).split(" Detalle:")[0], "error")
                return
            except Exception as exc:
                log.exception("Error inesperado al iniciar la camara virtual")
                self._set_virtual_button(False)
                self.notify(f"No se pudo iniciar la camara virtual: {exc}", "error")
                return
            self._set_virtual_button(True)
            self.notify(f"Camara virtual activa: {self.engine.output.device}", "ok")
        else:
            self.engine.stop_virtual()
            self._set_virtual_button(False)

    def _set_virtual_button(self, checked: bool) -> None:
        self.virtual_button.blockSignals(True)
        self.virtual_button.setChecked(checked)
        self.virtual_button.blockSignals(False)
        self.virtual_button.setText("Detener camara virtual" if checked else "Iniciar camara virtual")
        self.virtual_button.setIcon(icon("check" if checked else "play", "#ffffff" if checked else "#0b0d12", 18))

    def _tick(self) -> None:
        frame_id, frame = self.engine.latest()
        if frame is not None and frame_id != self._last_frame_id:
            self._last_frame_id = frame_id
            self.preview.live = True
            self.preview.set_frame(cv2.flip(frame, 1) if self.settings.mirror_mode == "preview" else frame)
        elif frame is None and self.preview.has_image and not self.engine.running:
            self.preview.live = False
            self.preview.clear("Camara detenida")

    def _slow_tick(self) -> None:
        engine = self.engine
        self.pill_fps.setText(f"{engine.fps:.0f} fps  |  {engine.process_ms:.0f} ms")
        set_tone(self.pill_fps, "ok" if engine.fps >= 24 else ("warn" if engine.fps > 0 else ""))
        s = self.settings
        if s.dual_faces:
            found = engine.faces_found
            count = sum(found)
            self.pill_face.setText(f"{count}/2 rostros")
            set_tone(self.pill_face, "ok" if count == 2 else ("warn" if count == 1 else ""))
        else:
            wants_face = bool(s.active_mask or s.accessories or s.beauty_smooth or s.beauty_lips
                              or s.beauty_bright or s.beauty_teeth)
            if wants_face:
                self.pill_face.setText("Rostro detectado" if engine.face_found else "Sin rostro")
                set_tone(self.pill_face, "ok" if engine.face_found else "warn")
            else:
                self.pill_face.setText("Sin filtros")
                set_tone(self.pill_face, "")
        if engine.virtual_active:
            self.pill_out.setText(f"Emitiendo: {engine.output.device}")
            set_tone(self.pill_out, "ok")
        else:
            self.pill_out.setText("Camara virtual apagada")
            set_tone(self.pill_out, "")
        if self.virtual_button.isChecked() and not engine.virtual_active:
            self._set_virtual_button(False)
            self.notify(engine.error or "La camara virtual se detuvo", "error")
            engine.error = ""
        if engine.error and engine.running:
            self.notify(engine.error, "warn")
            engine.error = ""
        if not engine.running and self._camera_wanted and not self._starting:
            self._retry_elapsed += 0.5
            if self._retry_elapsed >= RETRY_SECONDS:
                self._retry_elapsed = 0.0
                log.info("Reintentando abrir la camara")
                self._start_camera()
        else:
            self._retry_elapsed = 0.0
        self.stack.currentWidget().tick()

    def closeEvent(self, event) -> None:
        self._camera_wanted = False
        self._frame_timer.stop()
        self._slow_timer.stop()
        for page in self.pages.values():
            try:
                page.shutdown()
            except Exception:
                log.exception("Error al cerrar una pagina")
        self.engine.shutdown()
        self.settings.save()
        super().closeEvent(event)
