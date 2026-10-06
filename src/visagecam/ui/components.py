# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

import math
from collections.abc import Iterable

import numpy as np
from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QStyle,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from visagecam.ui.icons import icon
from visagecam.ui.theme import COLORS, qcolor

ID_ROLE = Qt.UserRole
PIX_ROLE = Qt.UserRole + 1
CHECK_ROLE = Qt.UserRole + 2
NAME_ROLE = Qt.UserRole + 3
REMOVABLE_ROLE = Qt.UserRole + 4


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def set_tone(label: QLabel, tone: str) -> None:
    label.setProperty("tone", tone)
    repolish(label)


def pill(text: str = "", tone: str = "") -> QLabel:
    label = QLabel(text)
    label.setObjectName("pill")
    label.setProperty("tone", tone)
    return label


def chip(text: str, tone: str = "") -> QLabel:
    label = QLabel(text)
    label.setObjectName("chip")
    label.setProperty("tone", tone)
    return label


def button(text: str, variant: str = "", icon_name: str | None = None, color: str = "#eceff6") -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.PointingHandCursor)
    if variant:
        btn.setProperty("variant", variant)
    if icon_name:
        btn.setIcon(icon(icon_name, color, 18))
        btn.setIconSize(QSize(18, 18))
    return btn


class Card(QFrame):
    def __init__(self, title: str = "", subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(18, 16, 18, 16)
        self.body.setSpacing(12)
        if title:
            head = QVBoxLayout()
            head.setSpacing(2)
            t = QLabel(title)
            t.setObjectName("h2")
            head.addWidget(t)
            if subtitle:
                s = QLabel(subtitle)
                s.setObjectName("muted")
                s.setWordWrap(True)
                head.addWidget(s)
            self.body.addLayout(head)

    def add(self, widget: QWidget | None = None, layout=None) -> None:
        if widget is not None:
            self.body.addWidget(widget)
        if layout is not None:
            self.body.addLayout(layout)


class Switch(QCheckBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._knob = 0.0
        self.setCursor(Qt.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def sizeHint(self) -> QSize:
        return QSize(42, 24)

    def hitButton(self, pos: QPoint) -> bool:
        return self.rect().contains(pos)

    def _get_knob(self) -> float:
        return self._knob

    def _set_knob(self, value: float) -> None:
        self._knob = value
        self.update()

    knob = Property(float, _get_knob, _set_knob)

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        self._anim.stop()
        self._set_knob(1.0 if checked else 0.0)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._knob)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(1, 2, 40, 20)
        track = QPainterPath()
        track.addRoundedRect(rect, 10, 10)
        if self.isChecked():
            grad = QLinearGradient(rect.left(), 0, rect.right(), 0)
            grad.setColorAt(0, qcolor("accent"))
            grad.setColorAt(1, qcolor("accent2"))
            p.fillPath(track, QBrush(grad))
        else:
            p.fillPath(track, QColor("#313849"))
        if not self.isEnabled():
            p.fillPath(track, QColor(14, 16, 20, 120))
        x = rect.left() + 3 + self._knob * (rect.width() - 20)
        p.setBrush(QColor("#ffffff"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(x, rect.top() + 3, 14, 14))


class SwitchRow(QWidget):
    toggled = Signal(bool)

    def __init__(self, label: str, description: str = "") -> None:
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        texts = QVBoxLayout()
        texts.setSpacing(1)
        self._label = QLabel(label)
        texts.addWidget(self._label)
        if description:
            d = QLabel(description)
            d.setObjectName("muted")
            d.setWordWrap(True)
            texts.addWidget(d)
        row.addLayout(texts, 1)
        self.switch = Switch()
        row.addWidget(self.switch, 0, Qt.AlignVCenter)
        self.switch.toggled.connect(self.toggled)

    def setChecked(self, checked: bool) -> None:
        self.switch.blockSignals(True)
        self.switch.setChecked(checked)
        self.switch.blockSignals(False)

    def isChecked(self) -> bool:
        return self.switch.isChecked()

    def click(self) -> None:
        self.switch.click()

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self.switch.setEnabled(enabled)


class Segmented(QFrame):
    changed = Signal(object)

    def __init__(self, options: Iterable[tuple[object, str]]) -> None:
        super().__init__()
        self.setStyleSheet(
            f"QFrame {{ background: {COLORS['surface']}; border: 1px solid {COLORS['border']}; border-radius: 11px; }}"
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(3, 3, 3, 3)
        row.setSpacing(2)
        self._group = QButtonGroup(self)
        self._buttons: dict[object, QPushButton] = {}
        for value, label in options:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("segment", "true")
            self._group.addButton(btn)
            self._buttons[value] = btn
            row.addWidget(btn, 1)
            btn.clicked.connect(lambda _=False, v=value: self.changed.emit(v))
        self._group.setExclusive(True)

    def set_value(self, value: object) -> None:
        button_ = self._buttons.get(value)
        if button_ is not None:
            button_.setChecked(True)

    def value(self) -> object:
        for value, btn in self._buttons.items():
            if btn.isChecked():
                return value
        return None


class SliderRow(QWidget):
    changed = Signal(float)

    def __init__(
        self,
        label: str,
        minimum: float,
        maximum: float,
        value: float,
        step: float = 1.0,
        suffix: str = "",
        decimals: int = 0,
    ) -> None:
        super().__init__()
        from PySide6.QtWidgets import QSlider

        self._step = step
        self._suffix = suffix
        self._decimals = decimals
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        head = QHBoxLayout()
        self._label = QLabel(label)
        self._value_label = QLabel()
        self._value_label.setObjectName("muted")
        head.addWidget(self._label)
        head.addStretch(1)
        head.addWidget(self._value_label)
        layout.addLayout(head)
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(round(minimum / step), round(maximum / step))
        self._slider.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self._slider)
        self.set_value(value)
        self._slider.valueChanged.connect(self._on_change)

    def value(self) -> float:
        return self._slider.value() * self._step

    def set_value(self, value: float) -> None:
        self._slider.blockSignals(True)
        self._slider.setValue(round(value / self._step))
        self._slider.blockSignals(False)
        self._refresh_label()

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self._slider.setEnabled(enabled)

    def _refresh_label(self) -> None:
        self._value_label.setText(f"{self.value():.{self._decimals}f}{self._suffix}")

    def _on_change(self) -> None:
        self._refresh_label()
        self.changed.emit(self.value())


class TileDelegate(QStyledItemDelegate):
    TILE = QSize(116, 138)

    def sizeHint(self, option, index) -> QSize:
        return self.TILE

    def paint(self, painter: QPainter, option, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        rect = QRectF(option.rect).adjusted(3, 3, -3, -3)
        hover = bool(option.state & QStyle.State_MouseOver)
        selected = bool(option.state & QStyle.State_Selected)
        checked = bool(index.data(CHECK_ROLE))
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)
        fill = QColor(COLORS["card_hi"]) if (hover or selected) else QColor(COLORS["card"])
        painter.fillPath(path, fill)
        border = QColor(COLORS["accent"]) if (selected or checked) else QColor(COLORS["border"])
        painter.setPen(QPen(border, 2 if (selected or checked) else 1))
        painter.drawPath(path)
        pix = index.data(PIX_ROLE)
        if isinstance(pix, QPixmap) and not pix.isNull():
            target = QRectF(rect.left() + 12, rect.top() + 10, rect.width() - 24, rect.width() - 24)
            scaled = pix.scaled(target.size().toSize(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(
                int(target.left() + (target.width() - scaled.width()) / 2),
                int(target.top() + (target.height() - scaled.height()) / 2),
                scaled,
            )
        name = str(index.data(NAME_ROLE) or "")
        painter.setPen(QColor(COLORS["text"]))
        font = painter.font()
        font.setPointSizeF(9.0)
        font.setWeight(QFont.Medium)
        painter.setFont(font)
        text_rect = QRectF(rect.left() + 6, rect.bottom() - 30, rect.width() - 12, 24)
        painter.drawText(
            text_rect,
            Qt.AlignHCenter | Qt.AlignVCenter,
            painter.fontMetrics().elidedText(name, Qt.ElideRight, int(text_rect.width())),
        )
        if checked:
            badge = QRectF(rect.right() - 26, rect.top() + 7, 20, 20)
            grad = QLinearGradient(badge.topLeft(), badge.bottomRight())
            grad.setColorAt(0, qcolor("accent"))
            grad.setColorAt(1, qcolor("accent2"))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawEllipse(badge)
            check = icon("check", "#0b0d12", 14).pixmap(14, 14)
            painter.drawPixmap(int(badge.left() + 3), int(badge.top() + 3), check)
        painter.restore()


class Gallery(QListWidget):
    selected = Signal(str)
    toggled = Signal(str, bool)

    def __init__(self, checkable: bool = False) -> None:
        super().__init__()
        self.checkable = checkable
        self.setViewMode(QListView.IconMode)
        self.setMovement(QListView.Static)
        self.setResizeMode(QListView.Adjust)
        self.setWrapping(True)
        self.setSpacing(2)
        self.setUniformItemSizes(True)
        self.setMouseTracking(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setItemDelegate(TileDelegate(self))
        self.setFrameShape(QFrame.NoFrame)
        self.itemClicked.connect(self._clicked)
        self.currentItemChanged.connect(self._current_changed)

    def _clicked(self, item: QListWidgetItem) -> None:
        if self.checkable:
            state = not bool(item.data(CHECK_ROLE))
            item.setData(CHECK_ROLE, state)
            self.viewport().update()
            self.toggled.emit(item.data(ID_ROLE), state)

    def _current_changed(self, current: QListWidgetItem | None, _previous) -> None:
        if current is not None:
            self.selected.emit(current.data(ID_ROLE))

    def set_items(
        self, entries: Iterable[tuple[str, str, QPixmap, bool]], checked: Iterable[str] = ()
    ) -> None:
        active = set(checked)
        self.blockSignals(True)
        self.clear()
        for item_id, name, pixmap, removable in entries:
            item = QListWidgetItem()
            item.setData(ID_ROLE, item_id)
            item.setData(NAME_ROLE, name)
            item.setData(PIX_ROLE, pixmap)
            item.setData(CHECK_ROLE, item_id in active)
            item.setData(REMOVABLE_ROLE, removable)
            item.setSizeHint(TileDelegate.TILE)
            item.setToolTip(name)
            self.addItem(item)
        self.blockSignals(False)
        self._fit()

    def set_checked(self, ids: Iterable[str]) -> None:
        active = set(ids)
        for row in range(self.count()):
            item = self.item(row)
            item.setData(CHECK_ROLE, item.data(ID_ROLE) in active)
        self.viewport().update()

    def select(self, item_id: str) -> None:
        for row in range(self.count()):
            if self.item(row).data(ID_ROLE) == item_id:
                self.blockSignals(True)
                self.setCurrentRow(row)
                self.blockSignals(False)
                self.viewport().update()
                return
        self.blockSignals(True)
        self.setCurrentRow(-1)
        self.blockSignals(False)

    def current_id(self) -> str | None:
        item = self.currentItem()
        return item.data(ID_ROLE) if item else None

    def current_removable(self) -> bool:
        item = self.currentItem()
        return bool(item.data(REMOVABLE_ROLE)) if item else False

    def _fit(self) -> None:
        width = max(self.viewport().width(), 1)
        per_row = max(1, width // (TileDelegate.TILE.width() + 4))
        rows = math.ceil(self.count() / per_row)
        self.setFixedHeight(rows * (TileDelegate.TILE.height() + 4) + 6 if rows else 0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit()


class PreviewWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(520, 292)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._image: QImage | None = None
        self._frame: np.ndarray | None = None
        self.message = "Iniciando camara..."
        self.live = False
        self.hud = ""

    def set_frame(self, frame: np.ndarray) -> None:
        height, width = frame.shape[:2]
        self._frame = frame
        self._image = QImage(frame.data, width, height, 3 * width, QImage.Format_BGR888)
        self.update()

    @property
    def has_image(self) -> bool:
        return self._image is not None

    def clear(self, message: str) -> None:
        self._image = None
        self._frame = None
        self.message = message
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        clip = QPainterPath()
        clip.addRoundedRect(rect, 16, 16)
        p.setClipPath(clip)
        p.fillPath(clip, QColor("#0a0c10"))
        if self._image is not None:
            size = self._image.size().scaled(self.size(), Qt.KeepAspectRatio)
            target = QRect(
                (self.width() - size.width()) // 2,
                (self.height() - size.height()) // 2,
                size.width(),
                size.height(),
            )
            p.drawImage(target, self._image)
        else:
            p.setPen(QColor(COLORS["muted"]))
            p.drawText(self.rect(), Qt.AlignCenter | Qt.TextWordWrap, self.message)
        p.setClipping(False)
        p.setPen(QPen(QColor(COLORS["border"]), 1))
        p.drawPath(clip)
        if self.live and self._image is not None:
            self._badge(p, 14, 14, "EN VIVO", QColor(COLORS["danger"]))
        if self.hud and self._image is not None:
            self._badge(p, 14, self.height() - 38, self.hud, QColor(COLORS["accent"]), dot=False)

    @staticmethod
    def _badge(p: QPainter, x: int, y: int, text: str, color: QColor, dot: bool = True) -> None:
        font = p.font()
        font.setPointSizeF(9.0)
        font.setWeight(QFont.DemiBold)
        p.setFont(font)
        width = p.fontMetrics().horizontalAdvance(text) + (34 if dot else 22)
        path = QPainterPath()
        path.addRoundedRect(QRectF(x, y, width, 24), 12, 12)
        p.fillPath(path, QColor(10, 12, 16, 190))
        if dot:
            p.setBrush(color)
            p.setPen(Qt.NoPen)
            p.drawEllipse(QRectF(x + 10, y + 8, 8, 8))
        p.setPen(QColor("#eceff6"))
        p.drawText(QRectF(x + (24 if dot else 11), y, width, 24), Qt.AlignVCenter | Qt.AlignLeft, text)


class Toast(QLabel):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.setMaximumWidth(520)
        self.hide()
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._fade = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade.setDuration(220)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._hide)

    def show_message(self, text: str, tone: str = "info", ms: int = 3200) -> None:
        colors = {
            "info": COLORS["accent"],
            "ok": COLORS["ok"],
            "warn": COLORS["warn"],
            "error": COLORS["danger"],
        }
        self.setStyleSheet(
            f"background: {COLORS['card_hi']}; color: {COLORS['text']}; border: 1px solid {colors.get(tone, COLORS['accent'])};"
            "border-radius: 12px; padding: 10px 16px; font-weight: 500;"
        )
        self.setText(text)
        self.adjustSize()
        self.reposition()
        self.show()
        self.raise_()
        self._fade.stop()
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.start()
        self._timer.start(ms)

    def reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.move((parent.width() - self.width()) // 2, parent.height() - self.height() - 28)

    def _hide(self) -> None:
        self._fade.stop()
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.finished.connect(self._finish)
        self._fade.start()

    def _finish(self) -> None:
        try:
            self._fade.finished.disconnect(self._finish)
        except (RuntimeError, TypeError):
            pass
        if self._effect.opacity() < 0.05:
            self.hide()


def section_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("h2")
    return label


def muted(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("muted")
    label.setWordWrap(True)
    return label
