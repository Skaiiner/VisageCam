# Copyright (c) 2026 Skain. Todos los derechos reservados.

import numpy as np
import pytest

from synthetic import StubTracker, live_face, make_frame
from visagecam.config import Settings
from visagecam.processing import pipeline as pipeline_module
from visagecam.processing.background import BackgroundRenderer
from visagecam.processing.beauty import BeautyRenderer
from visagecam.processing.enhance import Enhancer
from visagecam.processing.face_warp import FaceWarpRenderer
from visagecam.processing.neutral import NeutralFace
from visagecam.processing.overlay import OverlayRenderer


def changed(before: np.ndarray, after: np.ndarray) -> float:
    return float(np.abs(before.astype(np.int16) - after.astype(np.int16)).mean())


@pytest.fixture()
def neutral(isolated_appdata):
    n = NeutralFace()
    n.points = None
    n.start_calibration()
    for _ in range(20):
        n.observe(live_face())
    assert n.ready
    return n


@pytest.mark.parametrize(
    "mask_id",
    [
        "fox",
        "robot",
        "dragon",
        "cat_astronaut",
        "alien",
        "bear",
        "chrome_knight",
        "phoenix",
        "tribal_wolf",
        "venetian_gold",
        "butterfly",
        "feather_noir",
        "harlequin",
        "cat_eye_lace",
    ],
)
@pytest.mark.parametrize(
    "pose",
    [
        dict(),
        dict(rotation=0.5),
        dict(scale=60, center=(100, 100)),
        dict(scale=400),
        dict(center=(-50, 700)),
        dict(center=(1300, -20), open_=0.2),
    ],
)
def test_masks_render_in_every_pose(library, neutral, mask_id, pose):
    frame = make_frame()
    mask = library.get(mask_id)
    renderer, face = OverlayRenderer(), FaceWarpRenderer()
    canon = neutral.canonical_for(mask)
    assert canon is not None
    before = frame.copy()
    renderer.draw(frame, mask, live_face(**pose), Settings(), expression=(face, canon))
    assert frame.shape == before.shape and frame.dtype == np.uint8
    if not pose:
        assert changed(before, frame) > 0.3


def test_rigid_overlay_and_accessories(library):
    s = Settings()
    renderer = OverlayRenderer()
    for acc in library.accessories():
        frame = make_frame()
        before = frame.copy()
        renderer.draw(frame, acc, live_face(rotation=0.2), s, (1.2, 10.0, 0.05, -0.05), 1.0)
        assert changed(before, frame) > 0.05, acc.mask_id


def test_extreme_adjustments_do_not_crash(library):
    s = Settings()
    s.mask_scale, s.mask_rotation, s.mask_offset_x, s.mask_offset_y = 3.0, 180.0, 1.0, -1.0
    frame = make_frame()
    OverlayRenderer().draw(frame, library.get("fox"), live_face(), s)
    s.mask_scale = 0.2
    OverlayRenderer().draw(frame, library.get("fox"), live_face(), s)


def test_expression_changes_with_mouth(library, neutral):
    mask = library.get("fox")
    renderer, face = OverlayRenderer(), FaceWarpRenderer()
    canon = neutral.canonical_for(mask)
    closed, opened = make_frame(), make_frame()
    renderer.draw(closed, mask, live_face(open_=0.0), Settings(), expression=(face, canon))
    renderer.draw(opened, mask, live_face(open_=0.22), Settings(), expression=(face, canon))
    assert changed(closed, opened) > 0.3


def test_photo_face_warp(library):
    from visagecam.masks.model import Mask

    yy, xx = np.mgrid[:600, :600]
    image = np.zeros((600, 600, 4), np.uint8)
    image[..., 0] = 120 + 60 * ((xx // 40 + yy // 40) % 2)
    image[..., 1], image[..., 2], image[..., 3] = 150, 200, 255
    photo = Mask("photo-test", "x", image, [], live_face(250, 0, (300, 300)))
    frame = make_frame()
    before = frame.copy()
    FaceWarpRenderer().draw(frame, photo, live_face(rotation=0.2, open_=0.15), Settings())
    assert changed(before, frame) > 0.3


def test_beauty_enhance_background():
    s = Settings()
    s.beauty_smooth = s.beauty_bright = s.beauty_lips = s.beauty_teeth = 1.0
    frame = make_frame()
    before = frame.copy()
    BeautyRenderer().draw(frame, live_face(open_=0.12), s)
    assert changed(before, frame) > 0.05
    dark = np.full((720, 1280, 3), 25, np.uint8)
    lifted = Enhancer().apply(dark, 1.0)
    assert lifted.mean() > dark.mean()
    s.background_mode = "blur"
    out = BackgroundRenderer().apply(make_frame(), s)
    assert out.shape == (720, 1280, 3)


def test_background_image_missing_file_is_safe(tmp_path):
    s = Settings()
    s.background_mode, s.background_image = "image", str(tmp_path / "missing.jpg")
    frame = make_frame()
    assert BackgroundRenderer().apply(frame, s).shape == frame.shape


def test_pipeline_end_to_end(library, monkeypatch, isolated_appdata):
    monkeypatch.setattr(pipeline_module, "FaceTracker", StubTracker)
    s = Settings()
    s.active_mask = "fox"
    s.accessories = ["top_hat", "sunglasses", "ghost-id"]
    s.beauty_smooth = 0.5
    s.background_mode = "blur"
    pipe = pipeline_module.FramePipeline(s, library)
    pipe.recalibrate()
    base = make_frame()
    results = []
    for i in range(45):
        results.append(pipe.process(base.copy()))
    assert all(r.shape == base.shape for r in results)
    assert pipe.face_found and pipe.neutral.ready
    assert changed(base, results[-1]) > 0.5
    for key in ("fox", "", "missing-mask"):
        s.active_mask = key
        pipe.process(base.copy())
    s.mirror_mode = "both"
    s.expression = False
    s.enhance = 1.0
    pipe.process(base.copy())
    pipe.close()


def test_pipeline_ignores_garbage_landmarks(library, monkeypatch):
    class Garbage(StubTracker):
        def process(self, frame, scale=1.0):
            self.frame += 1
            return [
                None,
                np.full((468, 2), np.nan, np.float32),
                np.zeros((468, 2), np.float32),
                live_face(scale=1e6),
            ][self.frame % 4]

    monkeypatch.setattr(pipeline_module, "FaceTracker", Garbage)
    s = Settings()
    s.active_mask = "robot"
    pipe = pipeline_module.FramePipeline(s, library)
    for _ in range(12):
        assert pipe.process(make_frame()).shape == (720, 1280, 3)


def test_denoiser_reduces_noise_and_respects_motion():
    from visagecam.processing.enhance import Denoiser

    rng = np.random.default_rng(4)
    base = np.full((360, 640, 3), 100, np.uint8)
    denoiser = Denoiser()
    noisy = [np.clip(base + rng.normal(0, 8, base.shape), 0, 255).astype(np.uint8) for _ in range(12)]
    outputs = [denoiser.apply(f, 1.0) for f in noisy]
    assert outputs[-1].astype(float).std() < noisy[-1].astype(float).std() * 0.8
    moving = base.copy()
    moving[100:200, 100:300] = 250
    result = denoiser.apply(moving, 1.0)
    assert result[150, 200].mean() > 200
    assert denoiser.apply(moving, 0.0) is moving


def test_covering_masks_hide_real_eyes(library, neutral):
    mask = library.get("alien")
    frame = make_frame(color=(40, 40, 200))
    face = live_face()
    OverlayRenderer().draw(
        frame, mask, face, Settings(), expression=(FaceWarpRenderer(), neutral.canonical_for(mask))
    )
    eye = face[[33, 133, 159, 145]].mean(axis=0).astype(int)
    patch = frame[eye[1] - 3 : eye[1] + 4, eye[0] - 3 : eye[0] + 4].astype(int)
    assert np.abs(patch - np.array([40, 40, 200])).mean() > 30


def test_tracker_scale_contract():
    from visagecam.processing.landmarks import FaceTracker

    tracker = FaceTracker()
    blank = np.zeros((360, 640, 3), np.uint8)
    assert tracker.process(blank, 2.0) is None
    assert tracker.held() is None
    tracker.close()


def test_multi_face_tracker_runs_without_crashing():
    from visagecam.processing.landmarks import MultiFaceTracker

    tracker = MultiFaceTracker()
    frame = make_frame(1280, 720)
    for _ in range(3):
        slots = tracker.process(frame)
    assert slots == [None, None]
    assert tracker.held() == [None, None]
    tracker.forget()
    tracker.close()


def test_pipeline_dual_faces_applies_independent_profiles(library, monkeypatch, isolated_appdata):
    from visagecam.processing import pipeline as pipeline_module

    class TwoFaceStub:
        def __init__(self, *a, **k) -> None:
            self.frame = 0

        def process(self, frame, scale=1.0):
            self.frame += 1
            return [live_face(160, 0.0, (300, 380)), live_face(150, 0.1, (980, 400))]

        def held(self):
            return [None, None]

        def forget(self, slot=None) -> None:
            pass

        def close(self) -> None:
            pass

    monkeypatch.setattr(pipeline_module, "MultiFaceTracker", TwoFaceStub)
    s = Settings()
    s.dual_faces = True
    s.active_mask = "fox"
    s.person2.active_mask = "robot"
    pipe = pipeline_module.FramePipeline(s, library)
    frame = make_frame()
    for _ in range(8):
        out = pipe.process(frame.copy())
    assert pipe.faces_found == (True, True)
    left_region = out[300:560, 140:540]
    right_region = out[300:560, 760:1180]
    assert changed(frame[300:560, 140:540], left_region) > 0.3
    assert changed(frame[300:560, 760:1180], right_region) > 0.3
    s.dual_faces = False
    pipe.process(frame.copy())
    assert pipe.faces_found[1] is False
    pipe.close()


def test_pipeline_dual_faces_handles_missing_second_face(library, monkeypatch, isolated_appdata):
    from visagecam.processing import pipeline as pipeline_module

    class OneFaceStub:
        def __init__(self, *a, **k) -> None:
            pass

        def process(self, frame, scale=1.0):
            return [live_face(160, 0.0, (640, 380)), None]

        def held(self):
            return [None, None]

        def forget(self, slot=None) -> None:
            pass

        def close(self) -> None:
            pass

    monkeypatch.setattr(pipeline_module, "MultiFaceTracker", OneFaceStub)
    s = Settings()
    s.dual_faces = True
    s.active_mask = "fox"
    s.person2.active_mask = "robot"
    pipe = pipeline_module.FramePipeline(s, library)
    for _ in range(5):
        out = pipe.process(make_frame())
    assert pipe.faces_found == (True, False)
    assert out.shape == (720, 1280, 3)
    pipe.close()


def test_distortion_presets_change_pixels_and_respect_radius(library):
    from visagecam.config import FilterProfile
    from visagecam.processing.distortion import PRESETS, DistortionRenderer

    renderer = DistortionRenderer()
    face = live_face()
    for preset_id in PRESETS:
        frame = make_frame()
        before = frame.copy()
        renderer.draw(frame, face, FilterProfile(distortion=preset_id, distortion_strength=1.0))
        assert not np.array_equal(before, frame), preset_id
        far_corner = frame[:40, :40]
        assert np.array_equal(before[:40, :40], far_corner), preset_id


def test_distortion_strength_scales_effect(library):
    from visagecam.config import FilterProfile
    from visagecam.processing.distortion import DistortionRenderer

    renderer = DistortionRenderer()
    face = live_face()
    weak = make_frame()
    strong = make_frame()
    renderer.draw(weak, face, FilterProfile(distortion="big_eyes", distortion_strength=0.3))
    renderer.draw(strong, face, FilterProfile(distortion="big_eyes", distortion_strength=2.0))
    base = make_frame()
    assert changed(base, strong) > changed(base, weak)


def test_distortion_unknown_or_empty_is_noop(library):
    from visagecam.config import FilterProfile
    from visagecam.processing.distortion import DistortionRenderer

    renderer = DistortionRenderer()
    face = live_face()
    for preset_id in ("", "does-not-exist"):
        frame = make_frame()
        before = frame.copy()
        renderer.draw(frame, face, FilterProfile(distortion=preset_id))
        assert np.array_equal(before, frame)


def test_distortion_combines_with_mask(library, neutral):
    mask = library.get("fox")
    face = live_face()
    s = Settings()
    s.active_mask = "fox"
    s.distortion = "big_eyes"
    pipeline_profile = s.primary_profile()
    from visagecam.processing.distortion import DistortionRenderer

    frame = make_frame()
    DistortionRenderer().draw(frame, face, pipeline_profile)
    before_mask = frame.copy()
    OverlayRenderer().draw(
        frame, mask, face, pipeline_profile, expression=(FaceWarpRenderer(), neutral.canonical_for(mask))
    )
    assert changed(before_mask, frame) > 0.3


def test_pipeline_applies_distortion_alone_and_with_mask(library, monkeypatch, isolated_appdata):
    from visagecam.processing import pipeline as pipeline_module

    monkeypatch.setattr(pipeline_module, "FaceTracker", StubTracker)
    s = Settings()
    s.distortion = "big_eyes"
    pipe = pipeline_module.FramePipeline(s, library)
    frame = make_frame()
    for _ in range(10):
        out = pipe.process(frame.copy())
    assert pipe.face_found
    assert changed(frame, out) > 0.01
    pipe.close()


def test_all_distortion_presets_render_every_kind(library):
    from visagecam.config import FilterProfile
    from visagecam.processing.distortion import PRESETS, DistortionRenderer

    renderer = DistortionRenderer()
    face = live_face()
    kinds = {point.kind for preset in PRESETS.values() for point in preset.points}
    assert kinds == {"bulge", "stretch", "swirl", "shift"}
    assert len(PRESETS) >= 25
    for preset_id in PRESETS:
        frame = make_frame()
        before = frame.copy()
        renderer.draw(frame, face, FilterProfile(distortion=preset_id, distortion_strength=1.0))
        assert not np.array_equal(before, frame), preset_id
        assert np.array_equal(before[:30, :30], frame[:30, :30]), preset_id
        assert frame.dtype == np.uint8 and frame.shape == before.shape


def test_distortion_categories_cover_every_preset():
    from visagecam.processing.distortion import CATEGORIES, PRESETS, presets_in

    assert set(presets_in("all")) == set(PRESETS)
    named = {key for key, _ in CATEGORIES if key != "all"}
    assert {preset.category for preset in PRESETS.values()} <= named
    covered = {pid for key in named for pid in presets_in(key)}
    assert covered == set(PRESETS)


def test_camera_effects_all_run_and_keep_shape():
    from visagecam.processing.camera_effects import EFFECTS, CameraEffectRenderer

    renderer = CameraEffectRenderer()
    base = make_frame(640, 360)
    base[40:120, 60:200] = (20, 200, 240)
    base[260:330, 430:600] = (240, 40, 90)
    assert len(EFFECTS) >= 25
    for effect_id in EFFECTS:
        out = renderer.apply(base.copy(), effect_id, 1.0)
        assert out.shape == base.shape and out.dtype == np.uint8, effect_id
        assert not np.array_equal(out, base), effect_id


def test_camera_effect_unknown_is_noop_and_cache_is_bounded():
    from visagecam.processing.camera_effects import MAX_CACHED_MAPS, CameraEffectRenderer

    renderer = CameraEffectRenderer()
    base = make_frame(320, 180)
    assert np.array_equal(renderer.apply(base.copy(), "", 1.0), base)
    assert np.array_equal(renderer.apply(base.copy(), "no-existe", 1.0), base)
    for strength in np.linspace(0.3, 2.0, 20):
        renderer.apply(base.copy(), "fisheye", float(strength))
    assert len(renderer._maps) <= MAX_CACHED_MAPS


def test_camera_grader_changes_image_and_detects_activity():
    from visagecam.config import Settings
    from visagecam.processing.camera_effects import CameraGrader

    settings = Settings()
    assert CameraGrader.active(settings) is False
    settings.grade_contrast = 0.5
    assert CameraGrader.active(settings) is True
    base = make_frame()
    grader = CameraGrader()
    brighter = grader.apply(base.copy(), 0.5, 0.0, 0.0, 0.0)
    assert brighter.mean() > base.mean()
    warm = grader.apply(base.copy(), 0.0, 0.0, 0.0, 0.6)
    cool = grader.apply(base.copy(), 0.0, 0.0, 0.0, -0.6)
    assert warm[..., 2].mean() > cool[..., 2].mean()
    assert warm[..., 0].mean() < cool[..., 0].mean()
    gray = grader.apply(base.copy(), 0.0, 0.0, -1.0, 0.0)
    assert abs(float(gray[..., 0].mean()) - float(gray[..., 2].mean())) < 6.0


def test_pipeline_applies_camera_effect_and_grade(library, monkeypatch, isolated_appdata):
    from visagecam.processing import pipeline as pipeline_module

    monkeypatch.setattr(pipeline_module, "FaceTracker", StubTracker)
    s = Settings()
    s.camera_effect = "sepia"
    s.grade_contrast = 0.4
    pipe = pipeline_module.FramePipeline(s, library)
    base = make_frame()
    out = pipe.process(base.copy())
    assert out.shape == base.shape
    assert changed(base, out) > 1.0
    s.camera_effect = ""
    s.grade_contrast = 0.0
    s.grade_brightness = 0.0
    neutral_out = pipe.process(base.copy())
    assert changed(base, neutral_out) < changed(base, out)
    s.camera_effect = "no-existe"
    assert pipe.process(base.copy()).shape == base.shape
    pipe.close()


def test_camera_effect_applies_over_mask(library, monkeypatch, isolated_appdata):
    from visagecam.processing import pipeline as pipeline_module

    monkeypatch.setattr(pipeline_module, "FaceTracker", StubTracker)
    s = Settings()
    s.active_mask = "fox"
    s.camera_effect = "bw"
    pipe = pipeline_module.FramePipeline(s, library)
    for _ in range(6):
        out = pipe.process(make_frame())
    assert abs(float(out[..., 0].mean()) - float(out[..., 2].mean())) < 3.0
    pipe.close()
