# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

import logging
import time
from pathlib import Path

from PySide6.QtCore import QMimeData, QSize, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from visagecam.config import data_dir
from visagecam.masks.library import SLOTS, ImageAnalysis, analyze_file
from visagecam.ui.components import Segmented, SwitchRow, button, chip, muted, repolish
from visagecam.ui.context import Context
from visagecam.ui.icons import icon
from visagecam.ui.widgets import over_checker

log = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif"}
IMAGE_FILTER = "Imagenes (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.gif)"

SLOT_LABELS = {
    "head": ("Cabeza", "hat", "Sombreros, coronas, gorros"),
    "eyes": ("Ojos", "eye", "Gafas y antifaces"),
    "mouth": ("Boca", "mouth", "Bigotes y labios"),
    "ears": ("Orejas", "ears", "Auriculares y pendientes"),
    "free": ("Libre", "free", "Centrado en la cara"),
}


def first_image_path(mime: QMimeData) -> Path | None:
    for url in mime.urls():
        if url.isLocalFile():
            path = Path(url.toLocalFile())
            if path.suffix.lower() in IMAGE_EXTENSIONS and path.is_file():
                return path
    return None


class DropZone(QLabel):
    dropped = Signal(object)
    clicked = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("drop")
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumSize(380, 340)
        self.setCursor(Qt.PointingHandCursor)
        self.show_prompt()

    def show_prompt(self) -> None:
        self.setPixmap(QPixmap())
        self.setText("Arrastra una imagen aqui\n\no haz clic para examinar\n\nPNG, JPG, WEBP, BMP o TIFF")

    def _hover(self, on: bool) -> None:
        self.setProperty("hover", "true" if on else "false")
        repolish(self)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if first_image_path(event.mimeData()) is not None:
            event.acceptProposedAction()
            self._hover(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, _event) -> None:
        self._hover(False)

    def dropEvent(self, event: QDropEvent) -> None:
        self._hover(False)
        path = first_image_path(event.mimeData())
        if path is not None:
            event.acceptProposedAction()
            self.dropped.emit(path)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


class ImageStudio(QDialog):
    def __init__(
        self,
        ctx: Context,
        parent: QWidget | None = None,
        initial_kind: str = "mask",
        path: Path | None = None,
    ) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Anadir imagen")
        self.setModal(True)
        self.setAcceptDrops(True)
        self.setMinimumSize(880, 520)
        self.analysis: ImageAnalysis | None = None
        self.result_item = None
        self._token = 0
        self._slot = "head"
        self._kind = initial_kind

        root = QHBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(22)

        left = QVBoxLayout()
        self.drop = DropZone()
        self.drop.dropped.connect(self.load_path)
        self.drop.clicked.connect(self.browse)
        left.addWidget(self.drop, 1)
        tools = QHBoxLayout()
        browse = button("Examinar...", "ghost", "upload")
        browse.clicked.connect(self.browse)
        paste = button("Pegar", "ghost", "paste")
        paste.clicked.connect(self.paste)
        tools.addWidget(browse, 1)
        tools.addWidget(paste, 1)
        left.addLayout(tools)
        self.chips = QHBoxLayout()
        self.chips.setSpacing(6)
        self.chips.addStretch(1)
        left.addLayout(self.chips)
        root.addLayout(left, 5)

        right = QVBoxLayout()
        right.setSpacing(14)
        title = QLabel("Convierte una imagen en filtro")
        title.setObjectName("h1")
        right.addWidget(title)
        right.addWidget(
            muted("VisageCam analiza la imagen y elige la mejor forma de ponertela. Puedes cambiarlo aqui.")
        )

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nombre")
        self.name_edit.setMaxLength(40)
        right.addWidget(self.name_edit)

        self.kind_seg = Segmented([("mask", "Filtro de cara"), ("accessory", "Accesorio")])
        self.kind_seg.set_value(initial_kind)
        self.kind_seg.changed.connect(self._kind_changed)
        right.addWidget(self.kind_seg)
        self.kind_hint = muted("")
        right.addWidget(self.kind_hint)

        self.slot_box = QWidget()
        grid = QGridLayout(self.slot_box)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        self.slot_buttons: dict[str, QPushButton] = {}
        for index, slot in enumerate(SLOTS):
            label, icon_name, tip = SLOT_LABELS[slot]
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("slot", "true")
            btn.setIcon(icon(icon_name, "#eceff6", 22))
            btn.setIconSize(QSize(22, 22))
            btn.setToolTip(tip)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, s=slot: self._slot_changed(s))
            self.slot_buttons[slot] = btn
            grid.addWidget(btn, index // 3, index % 3)
        right.addWidget(self.slot_box)

        self.warp_row = SwitchRow(
            "Deformar sobre mi rostro",
            "Sigue tus gestos punto a punto. Desactivalo para usarla como pegatina.",
        )
        self.warp_row.setChecked(True)
        self.warp_row.toggled.connect(lambda _v: self._refresh_preview())
        right.addWidget(self.warp_row)
        self.cut_row = SwitchRow(
            "Quitar el fondo automaticamente", "Recorta el objeto principal para que solo se vea el."
        )
        self.cut_row.setChecked(True)
        self.cut_row.toggled.connect(lambda _v: self._refresh_preview())
        right.addWidget(self.cut_row)
        right.addStretch(1)

        self.status = muted("Elige una imagen para empezar.")
        right.addWidget(self.status)
        actions = QHBoxLayout()
        cancel = button("Cancelar", "ghost")
        cancel.clicked.connect(self.reject)
        self.ok_button = button("Anadir y usar", "primary")
        self.ok_button.setEnabled(False)
        self.ok_button.clicked.connect(self._accept)
        actions.addWidget(cancel)
        actions.addWidget(self.ok_button, 1)
        right.addLayout(actions)
        root.addLayout(right, 4)

        self._sync_visibility()
        if path is not None:
            self.load_path(path)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if first_image_path(event.mimeData()) is not None:
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        path = first_image_path(event.mimeData())
        if path is not None:
            event.acceptProposedAction()
            self.load_path(path)

    def browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Elegir imagen", "", IMAGE_FILTER)
        if path:
            self.load_path(Path(path))

    def paste(self) -> None:
        image = QGuiApplication.clipboard().image()
        if image.isNull():
            self.status.setText("El portapapeles no contiene una imagen.")
            return
        temp = data_dir() / "tmp"
        temp.mkdir(parents=True, exist_ok=True)
        target = temp / f"pegado-{int(time.time())}.png"
        if not image.save(str(target), "PNG"):
            self.status.setText("No se pudo leer la imagen del portapapeles.")
            return
        self.load_path(target, name="Imagen pegada")

    def load_path(self, path: Path, name: str | None = None) -> None:
        self._token += 1
        token = self._token
        self.ok_button.setEnabled(False)
        self.status.setText("Analizando imagen...")
        self.ctx.runner.run(
            lambda: analyze_file(Path(path)),
            lambda analysis: self._analyzed(token, analysis, name),
            lambda message: self._failed(token, message),
        )

    def _failed(self, token: int, message: str) -> None:
        if token != self._token:
            return
        self.analysis = None
        self.ok_button.setEnabled(False)
        self.status.setText(message)
        self.ctx.notify(message, "error")

    def _analyzed(self, token: int, analysis: ImageAnalysis, name: str | None) -> None:
        if token != self._token:
            return
        self.analysis = analysis
        self.name_edit.setText(name or analysis.name)
        self.cut_row.setChecked(True)
        self.warp_row.setChecked(True)
        kind = "mask" if analysis.landmarks is not None else "accessory"
        if analysis.landmarks is None and not analysis.has_alpha and analysis.cutout is None:
            kind = "mask"
        self._kind = kind
        self.kind_seg.set_value(kind)
        self._sync_visibility()
        self._show_chips()
        self._refresh_preview()
        self.ok_button.setEnabled(True)
        self.status.setText("Todo listo. Revisa las opciones y pulsa Anadir y usar.")

    def _show_chips(self) -> None:
        while self.chips.count() > 1:
            item = self.chips.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        a = self.analysis
        if a is None:
            return
        entries = [(f"{a.size[0]} x {a.size[1]}", "")]
        entries.append(("Rostro detectado", "ok") if a.landmarks is not None else ("Sin rostro", "warn"))
        entries.append(("Con transparencia", "info") if a.has_alpha else ("Sin transparencia", ""))
        for index, (text, tone) in enumerate(entries):
            self.chips.insertWidget(index, chip(text, tone))

    def _kind_changed(self, value: object) -> None:
        self._kind = str(value)
        self._sync_visibility()
        self._refresh_preview()

    def _slot_changed(self, slot: str) -> None:
        self._slot = slot
        self._sync_visibility()

    def _sync_visibility(self) -> None:
        accessory = self._kind == "accessory"
        for slot, btn in self.slot_buttons.items():
            btn.setChecked(slot == self._slot)
        self.slot_box.setVisible(accessory)
        a = self.analysis
        can_warp = (not accessory) and a is not None and a.landmarks is not None
        self.warp_row.setVisible(can_warp)
        can_cut = a is not None and not a.has_alpha and a.landmarks is None
        self.cut_row.setVisible(can_cut)
        if can_cut and a.cutout is None:
            self.cut_row.setEnabled(False)
            self.cut_row.setChecked(False)
        else:
            self.cut_row.setEnabled(True)
        if accessory:
            self.kind_hint.setText(
                "Se ancla a una zona de tu cara y se mueve con ella. Puedes combinar varios."
            )
        elif a is not None and a.landmarks is not None:
            self.kind_hint.setText(
                "Se detecto una cara: la imagen se deformara sobre tu rostro y seguira tus gestos."
            )
        else:
            self.kind_hint.setText(
                "Se coloca centrada sobre tu cara. Puedes ajustar escala, giro y posicion."
            )

    def _refresh_preview(self) -> None:
        a = self.analysis
        if a is None:
            return
        bgra = a.bgra.copy()
        if a.cutout is not None and not a.has_alpha and self.cut_row.isVisible() and self.cut_row.isChecked():
            bgra[:, :, 3] = a.cutout
        side = max(300, min(self.drop.width(), self.drop.height()) - 20)
        self.drop.setPixmap(over_checker(bgra, side))

    def _accept(self) -> None:
        a = self.analysis
        if a is None:
            return
        kind = self._kind
        slot = self._slot
        name = self.name_edit.text().strip() or a.name
        use_cutout = self.cut_row.isVisible() and self.cut_row.isChecked()
        face_warp = self.warp_row.isVisible() and self.warp_row.isChecked()
        self.ok_button.setEnabled(False)
        self.status.setText("Guardando...")
        self.ctx.runner.run(
            lambda: self.ctx.library.add(a, kind, slot, name, use_cutout, face_warp),
            self._saved,
            lambda message: (
                self.status.setText(message),
                self.ok_button.setEnabled(True),
                self.ctx.notify(message, "error"),
            ),
        )

    def _saved(self, item) -> None:
        self.result_item = item
        self.accept()
