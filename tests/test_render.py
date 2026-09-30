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


@pytest.mark.parametrize("mask_id", ["fox", "robot", "dragon", "cat_astronaut", "alien", "bear"])
@pytest.mark.parametrize("pose", [
    dict(),
    dict(rotation=0.5),
    dict(scale=60, center=(100, 100)),
    dict(scale=400),
    dict(center=(-50, 700)),
    dict(center=(1300, -20), open_=0.2),
])
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
            return [None, np.full((468, 2), np.nan, np.float32), np.zeros((468, 2), np.float32), live_face(scale=1e6)][self.frame % 4]

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
    OverlayRenderer().draw(frame, mask, face, Settings(), expression=(FaceWarpRenderer(), neutral.canonical_for(mask)))
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
