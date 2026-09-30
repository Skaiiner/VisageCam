import random
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pytest
from PySide6.QtCore import QMimeData, QPointF, QUrl, Qt
from PySide6.QtGui import QDropEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog

from synthetic import FakeCapture, StubTracker
from visagecam.config import Settings
from visagecam.processing import pipeline as pipeline_module
from visagecam.processing.engine import Engine
from visagecam.ui.components import Gallery, SliderRow, SwitchRow
from visagecam.ui.main_window import MainWindow
from visagecam.ui.studio import ImageStudio
from visagecam.ui.theme import apply_theme


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    return app


@pytest.fixture()
def errors(monkeypatch):
    captured = []
    monkeypatch.setattr(sys, "excepthook", lambda t, e, tb: captured.append((t, e)))
    return captured


@pytest.fixture()
def window(qapp, library, monkeypatch, isolated_appdata, errors):
    monkeypatch.setattr(pipeline_module, "FaceTracker", StubTracker)
    settings = Settings()
    settings.stream_port = 8790
    engine = Engine(settings, library)
    engine.capture = FakeCapture()
    win = MainWindow(settings, library, engine)
    win.show()
    QTest.qWait(400)
    yield win
    win.close()
    QTest.qWait(50)


def wait_for(predicate, timeout=8.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        QTest.qWait(30)
        if predicate():
            return True
    return False


def write_png(path: Path, kind: str) -> Path:
    if kind == "sticker":
        image = np.full((320, 420, 3), 255, np.uint8)
        cv2.circle(image, (210, 160), 100, (40, 70, 210), -1)
        cv2.imencode(".png", image)[1].tofile(str(path))
    elif kind == "alpha":
        image = np.zeros((256, 256, 4), np.uint8)
        cv2.rectangle(image, (40, 60), (220, 200), (0, 180, 255, 255), -1)
        cv2.imencode(".png", image)[1].tofile(str(path))
    else:
        path.write_bytes(b"roto")
    return path


def test_window_shows_live_preview_and_pills(window):
    assert wait_for(lambda: window.preview.has_image)
    assert wait_for(lambda: "fps" in window.pill_fps.text() and window.engine.fps > 0, 6)
    assert window.engine.running


def test_every_page_and_control_is_operable(window, errors, monkeypatch, tmp_path):
    rng = random.Random(5)
    bg = tmp_path / "fondo.jpg"
    cv2.imencode(".jpg", np.random.default_rng(1).integers(0, 255, (300, 400, 3), dtype=np.uint8))[1].tofile(str(bg))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(bg), "")))
    for key in window.pages:
        window.show_page(key)
        QTest.qWait(40)
        page = window.pages[key]
        for slider in page.findChildren(SliderRow):
            for value in (slider._slider.minimum(), slider._slider.maximum(), rng.randint(slider._slider.minimum(), slider._slider.maximum())):
                slider._slider.setValue(value)
        for switch in page.findChildren(SwitchRow):
            if switch.isEnabled():
                switch.click()
                switch.click()
        for gallery in page.findChildren(Gallery):
            for row in range(gallery.count()):
                item = gallery.item(row)
                gallery.setCurrentItem(item)
                gallery.itemClicked.emit(item)
        QTest.qWait(60)
    window.show_page("background")
    for value in ("blur", "image", "none", "image"):
        window.background.segment.changed.emit(value)
        QTest.qWait(40)
    assert window.settings.background_mode == "image"
    assert Path(window.settings.background_image).is_file()
    window.background._delete()
    window.show_page("camera")
    for value in ("obs", "unitycapture", "auto"):
        window.camera.backend.changed.emit(value)
    assert window.settings.virtual_backend == "auto"
    QTest.qWait(300)
    assert not errors, errors


def test_settings_are_persisted(window):
    window.filters.sl_scale._slider.setValue(150)
    QTest.qWait(800)
    from visagecam.config import data_dir

    assert Settings.load(data_dir() / "config.json").mask_scale == 1.5


def test_studio_imports_sticker_and_accessory(window, tmp_path, errors):
    sticker = write_png(tmp_path / "pegatina.png", "sticker")
    studio = ImageStudio(window.ctx, window, "accessory", sticker)
    assert wait_for(lambda: studio.analysis is not None)
    assert studio.analysis.cutout is not None and studio.ok_button.isEnabled()
    studio._slot_changed("eyes")
    studio.kind_seg.changed.emit("accessory")
    studio.cut_row.click()
    studio.cut_row.click()
    studio.name_edit.setText("Mi pegatina")
    studio._accept()
    assert wait_for(lambda: studio.result_item is not None)
    item = studio.result_item
    assert item.kind == "accessory" and item.slot == "eyes" and item.name == "Mi pegatina"
    window.accessories.add_and_enable(item.mask_id)
    assert item.mask_id in window.settings.accessories
    window.accessories.gallery.select(item.mask_id)
    window.accessories._selected(item.mask_id)
    window.accessories._delete()
    assert item.mask_id not in window.settings.accessories
    assert window.library.get(item.mask_id) is None
    assert not errors


def test_studio_handles_bad_files_and_clipboard(window, tmp_path, qapp, errors):
    bad = write_png(tmp_path / "roto.png", "bad")
    studio = ImageStudio(window.ctx, window, "mask", bad)
    assert wait_for(lambda: "No se pudo" in studio.status.text())
    assert not studio.ok_button.isEnabled()
    studio._accept()
    qapp.clipboard().clear()
    studio.paste()
    assert "portapapeles" in studio.status.text()
    good = write_png(tmp_path / "transparente.png", "alpha")
    studio.load_path(good)
    assert wait_for(lambda: studio.analysis is not None and studio.ok_button.isEnabled())
    studio.load_path(bad)
    studio.load_path(good)
    assert wait_for(lambda: studio.analysis is not None)
    assert not errors


def test_drop_on_window_opens_flow(window, tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr(MainWindow, "open_studio", lambda self, kind="mask", path=None: opened.append((kind, path)))
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(write_png(tmp_path / "drop.png", "sticker")))])
    event = QDropEvent(QPointF(10, 10), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    window.dropEvent(event)
    QTest.qWait(100)
    assert opened and opened[0][0] == "mask"
    junk = QMimeData()
    junk.setUrls([QUrl.fromLocalFile(str(tmp_path / "x.exe"))])
    window.dropEvent(QDropEvent(QPointF(1, 1), Qt.CopyAction, junk, Qt.LeftButton, Qt.NoModifier))
    QTest.qWait(50)
    assert len(opened) == 1


def test_virtual_camera_failure_is_reported(window, errors):
    wait_for(lambda: window.engine.running)
    window.settings.virtual_backend = "backend-inexistente"
    window.virtual_button.setChecked(True)
    QTest.qWait(200)
    assert not window.virtual_button.isChecked()
    assert not window.engine.virtual_active
    assert window.toast.isVisible()
    assert not errors


def test_virtual_camera_works_or_reports(window, errors):
    wait_for(lambda: window.engine.running)
    window.settings.virtual_backend = "obs"
    window.virtual_button.setChecked(True)
    QTest.qWait(400)
    if window.virtual_button.isChecked():
        assert window.engine.virtual_active
        window.virtual_button.setChecked(False)
        assert not window.engine.virtual_active
    assert not errors


def test_camera_loss_triggers_recovery(window, errors):
    assert wait_for(lambda: window.engine.running)
    window.engine.capture.fail_open = True
    window.engine.capture.close()
    assert wait_for(lambda: not window.engine.running, 6)
    window._start_camera()
    assert wait_for(lambda: not window._starting, 6)
    assert not window.engine.running
    assert "camara" in window.preview.message.lower()
    window.engine.capture.fail_open = False
    window._retry_elapsed = 99
    window._slow_tick()
    assert wait_for(lambda: window.engine.running, 6)
    assert not errors


def test_obs_page_handles_unreachable_server(window, errors):
    window.show_page("obs")
    window.obs.port.setValue(1)
    window.obs._toggle()
    assert wait_for(lambda: window.obs.connect_button.isEnabled(), 10)
    assert window.obs.status.text() == "Error"
    assert not window.obs.obs.connected
    window.obs._switch()
    window.obs._add_camera()
    QTest.qWait(200)
    assert not errors


def test_window_close_is_clean(qapp, library, monkeypatch, isolated_appdata, errors):
    monkeypatch.setattr(pipeline_module, "FaceTracker", StubTracker)
    settings = Settings()
    settings.stream_port = 8780
    engine = Engine(settings, library)
    engine.capture = FakeCapture()
    win = MainWindow(settings, library, engine)
    win.show()
    QTest.qWait(300)
    win.close()
    QTest.qWait(100)
    assert not engine.running
    assert not errors


def test_mirror_modes(window, errors):
    assert wait_for(lambda: window.preview.has_image)
    for mode in ("preview", "both", "off", "preview"):
        window.mirror_bar.changed.emit(mode)
        QTest.qWait(150)
        assert window.settings.mirror_mode == mode
        assert window.camera.mirror.value() == mode
    window.camera.mirror.changed.emit("off")
    assert window.mirror_bar.value() == "off"
    window.mirror_bar.changed.emit("preview")
    wait_for(lambda: window.preview._frame is not None)
    _, raw = window.engine.latest()
    assert wait_for(lambda: window.preview._frame is not None and np.array_equal(window.preview._frame, raw[:, ::-1]), 6)
    assert not errors


def test_legacy_mirror_setting_is_migrated(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"mirror": true}', encoding="utf-8")
    s = Settings.load(path)
    assert s.mirror_mode == "both" and s.mirror is False
