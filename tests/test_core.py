import json

import cv2
import numpy as np
import pytest

from synthetic import live_face
from visagecam.config import Settings
from visagecam.masks import generator
from visagecam.masks.cutout import remove_background
from visagecam.masks.library import ImageError, analyze_bgra, analyze_file
from visagecam.processing.landmarks import LandmarkFilter, mouth_open_ratio
from visagecam.processing.transforms import affine_fit, similarity


def test_settings_roundtrip_and_sanitize(tmp_path):
    path = tmp_path / "config.json"
    s = Settings()
    s.mask_scale = 99
    s.width, s.height = 1234, 5
    s.background_mode = "weird"
    s.virtual_backend = "nope"
    s.accessories = ["a", 3, None]
    s.accessory_adjust = {"a": [1, 2, 3, 4], "b": "bad", "c": [1, 2]}
    s.sanitize()
    assert s.mask_scale == 3.0
    assert (s.width, s.height) == (1280, 720)
    assert s.background_mode == "none" and s.virtual_backend == "auto"
    assert s.accessories == ["a"]
    assert list(s.accessory_adjust) == ["a"]
    s.save(path)
    assert Settings.load(path).accessories == ["a"]


@pytest.mark.parametrize("content", ["", "{", "[]", '{"mask_scale": "abc", "unknown": 1}', '{"fps": null}'])
def test_settings_survive_corrupt_files(tmp_path, content):
    path = tmp_path / "config.json"
    path.write_text(content, encoding="utf-8")
    s = Settings.load(path)
    assert 0.2 <= s.mask_scale <= 3.0


def test_similarity_and_affine_recover_transform():
    rng = np.random.default_rng(1)
    src = rng.uniform(0, 100, (12, 2))
    angle, scale = 0.4, 1.7
    rot = scale * np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    dst = src @ rot.T + np.array([30, -20])
    sim = similarity(src, dst)
    assert np.allclose(sim[:, :2], rot, atol=1e-6)
    assert np.allclose(affine_fit(src, dst)[:, 2], [30, -20], atol=1e-6)


def test_landmark_filter_smooths_and_follows():
    f = LandmarkFilter()
    base = live_face()
    rng = np.random.default_rng(3)
    out = [f(base + rng.normal(0, 0.8, base.shape).astype(np.float32), i / 30.0) for i in range(40)]
    jitter_in = np.abs(rng.normal(0, 0.8, 10000)).mean()
    assert np.abs(out[-1] - base).mean() < jitter_in
    moved = base + 80
    for i in range(40, 60):
        result = f(moved, i / 30.0)
    assert np.abs(result - moved).mean() < 2.0


def test_mouth_ratio_reacts_to_opening():
    assert mouth_open_ratio(live_face(open_=0.0)) < mouth_open_ratio(live_face(open_=0.2))


def test_generated_assets_complete(library):
    assert [m.mask_id for m in library.all()[:6]] == generator.MASK_ORDER
    assert [m.mask_id for m in library.accessories()[:6]] == generator.ACCESSORY_ORDER
    for mask in library.all():
        assert mask.image.shape[2] == 4 and mask.anchors
    data = json.loads((library.dirs[("mask", True)] / "fox.json").read_text(encoding="utf-8"))
    assert {a["name"] for a in data["anchors"]} >= {"eye_left", "eye_right", "nose_tip"}


def _save(path, image):
    cv2.imencode(path.suffix, image)[1].tofile(str(path))


def test_import_variants(library, tmp_path):
    sticker = np.full((300, 400, 3), 255, np.uint8)
    cv2.circle(sticker, (200, 150), 90, (30, 60, 200), -1)
    path = tmp_path / "pegatina ñ é.png"
    _save(path, sticker)
    analysis = analyze_file(path)
    assert analysis.landmarks is None and analysis.cutout is not None
    item = library.add(analysis, "accessory", "head", "Pegatina")
    assert item.kind == "accessory" and item.slot == "head" and item.image[:, :, 3].min() == 0
    assert library.get(item.mask_id) is item

    transparent = np.zeros((200, 200, 4), np.uint8)
    cv2.circle(transparent, (100, 100), 60, (0, 200, 255, 255), -1)
    tpath = tmp_path / "sombrero.png"
    _save(tpath, transparent)
    analysis = analyze_file(tpath)
    assert analysis.has_alpha and analysis.cutout is None
    mask = library.add(analysis, "mask", "free", "Sombrero")
    assert mask.kind == "mask" and not mask.is_face

    ids = {library.add(analysis, "mask").mask_id for _ in range(30)}
    assert len(ids) == 30
    for mask_id in ids | {item.mask_id, mask.mask_id}:
        assert library.remove(mask_id)
    assert not library.remove("fox")
    assert not library.remove("does-not-exist")


def test_import_rejects_bad_input(tmp_path):
    bad = tmp_path / "roto.png"
    bad.write_bytes(b"not an image at all")
    with pytest.raises(ImageError):
        analyze_file(bad)
    with pytest.raises(ImageError):
        analyze_file(tmp_path / "no-existe.png")
    tiny = tmp_path / "tiny.png"
    _save(tiny, np.zeros((8, 8, 3), np.uint8))
    with pytest.raises(ImageError):
        analyze_file(tiny)
    with pytest.raises(ImageError):
        analyze_bgra(np.zeros((100, 100, 3), np.uint8), "x")


def test_import_large_image_is_downscaled(tmp_path):
    big = np.random.default_rng(0).integers(0, 255, (3000, 4000, 3), dtype=np.uint8)
    path = tmp_path / "grande.jpg"
    _save(path, big)
    analysis = analyze_file(path)
    assert max(analysis.size) <= 1280


def test_cutout_handles_flat_and_noise():
    flat = np.full((200, 200, 3), 128, np.uint8)
    assert remove_background(flat) is None
    noise = np.random.default_rng(2).integers(0, 255, (200, 200, 3), dtype=np.uint8)
    result = remove_background(noise)
    assert result is None or result.shape == (200, 200)


def test_shortcuts_are_created_and_removed(tmp_path):
    import subprocess

    from visagecam import shortcuts

    start, desktop = tmp_path / "inicio", tmp_path / "escritorio"
    created = shortcuts.install(desktop=True, start_menu=start, desktop_folder=desktop)
    assert [p.name for p in created] == ["VisageCam.lnk", "VisageCam.lnk"]
    assert all(p.exists() for p in created)
    script = "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:VC); $s.TargetPath; $s.Arguments; $s.IconLocation"
    info = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True,
                          env={**__import__("os").environ, "VC": str(created[0])}).stdout.splitlines()
    assert info[0].lower().endswith(("pythonw.exe", "python.exe")) and info[1] == "-m visagecam"
    assert info[2].endswith("visagecam.ico,0") and shortcuts.icon_path().exists()
    assert len(shortcuts.remove(start_menu=start, desktop_folder=desktop)) == 2
    assert shortcuts.remove(start_menu=start, desktop_folder=desktop) == []


def test_cli_flags_do_not_start_the_app(tmp_path, monkeypatch):
    import visagecam.shortcuts as shortcuts
    from visagecam.__main__ import main

    calls = []
    monkeypatch.setattr(shortcuts, "install", lambda desktop=False: calls.append(("install", desktop)) or [tmp_path / "x.lnk"])
    monkeypatch.setattr(shortcuts, "remove", lambda: calls.append(("remove",)) or [])
    assert main(["--install-shortcuts", "--desktop"]) == 0
    assert main(["--remove-shortcuts"]) == 0
    assert calls == [("install", True), ("remove",)]
