import logging
import time
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np

from visagecam.config import Settings
from visagecam.masks.library import MaskLibrary
from visagecam.processing.background import BackgroundRenderer
from visagecam.processing.beauty import BeautyRenderer
from visagecam.processing.blend import mix
from visagecam.processing.enhance import Denoiser, Enhancer
from visagecam.processing.face_warp import FaceWarpRenderer
from visagecam.processing.landmarks import FaceTracker, face_width
from visagecam.processing.neutral import NeutralFace
from visagecam.processing.overlay import OverlayRenderer

log = logging.getLogger(__name__)

DEFAULT_ADJUST = (1.0, 0.0, 0.0, 0.0)
ANALYSIS_WIDTH = 640


def usable(landmarks: np.ndarray | None, frame: np.ndarray) -> bool:
    if landmarks is None or landmarks.shape != (468, 2) or not np.isfinite(landmarks).all():
        return False
    return 16.0 < face_width(landmarks) < 3.0 * frame.shape[1]


class FramePipeline:
    def __init__(self, settings: Settings, library: MaskLibrary) -> None:
        self.settings = settings
        self.library = library
        self._tracker: FaceTracker | None = None
        self._background = BackgroundRenderer()
        self._overlay = OverlayRenderer()
        self._face = FaceWarpRenderer()
        self._beauty = BeautyRenderer()
        self._enhancer = Enhancer()
        self._denoiser = Denoiser()
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="visagecam")
        self.neutral = NeutralFace()
        self.face_found = False
        self._last_error = 0.0

    def recalibrate(self) -> None:
        self.neutral.start_calibration()

    def process(self, frame: np.ndarray) -> np.ndarray:
        settings = self.settings
        if settings.mirror:
            frame = cv2.flip(frame, 1)
        height, width = frame.shape[:2]
        amount = float(settings.enhance)
        mask = self.library.get(settings.active_mask) if settings.active_mask else None
        extras = [a for a in (self.library.get(i) for i in settings.accessories) if a is not None]
        beauty = BeautyRenderer.active(settings)
        need_track = mask is not None or bool(extras) or beauty
        need_bg = settings.background_mode != "none"

        small, factor = frame, 1.0
        if (need_track or need_bg) and width > ANALYSIS_WIDTH:
            small = cv2.resize(frame, (ANALYSIS_WIDTH, int(height * ANALYSIS_WIDTH / width)), interpolation=cv2.INTER_AREA)
            factor = width / ANALYSIS_WIDTH
        if need_track or need_bg or amount > 0.01:
            self._enhancer.prepare(small, amount)
        track_job = backdrop_job = None
        if need_track or need_bg:
            tone = self._enhancer.tone(small, amount)
            if need_track:
                if self._tracker is None:
                    self._tracker = FaceTracker()
                track_job = self._pool.submit(self._tracker.process, tone, factor)
            if need_bg:
                backdrop_job = self._pool.submit(self._backdrop, tone, (width, height))

        full = self._enhancer.finish(self._denoiser.apply(frame, amount), amount)
        owned = full is not frame

        landmarks = None
        if track_job is not None:
            try:
                landmarks = track_job.result()
            except Exception:
                log.exception("Error en el seguimiento facial")
                landmarks = None
            if not usable(landmarks, full):
                landmarks = None
            if landmarks is not None:
                if settings.expression and not self.neutral.ready:
                    self.neutral.observe(landmarks)
            else:
                landmarks = self._tracker.held()
                if not usable(landmarks, full):
                    landmarks = None
                if landmarks is None:
                    self._overlay.reset()
                    self._face.reset()
        self.face_found = landmarks is not None

        frame = full
        composed = None
        if backdrop_job is not None:
            try:
                backdrop, person = backdrop_job.result()
            except Exception:
                log.exception("Error en el fondo")
                backdrop = person = None
            if backdrop is not None and person is not None:
                composed = mix(backdrop, full, person)
        if composed is not None:
            frame = composed
        elif not owned:
            frame = frame.copy()

        if landmarks is not None:
            if beauty:
                self._guard("belleza", self._beauty.draw, frame, landmarks, settings)
            if mask is not None:
                if mask.is_face and settings.face_warp:
                    self._guard("rostro", self._face.draw, frame, mask, landmarks, settings)
                else:
                    self._guard("mascara", self._draw_mask, frame, mask, landmarks)
            for accessory in extras:
                values = settings.accessory_adjust.get(accessory.mask_id, DEFAULT_ADJUST)
                self._guard("accesorio", self._overlay.draw, frame, accessory, landmarks, settings, tuple(values), 1.0)
        return frame

    def _backdrop(self, small: np.ndarray, size: tuple[int, int]):
        backdrop = self._background.backdrop(small, self.settings, size)
        if backdrop is None:
            return None, None
        person = self._background.mask(small)
        return backdrop, cv2.resize(person, size, interpolation=cv2.INTER_LINEAR)

    def _draw_mask(self, frame: np.ndarray, mask, landmarks: np.ndarray) -> None:
        settings = self.settings
        canon = self.neutral.canonical_for(mask) if settings.expression else None
        expression = (self._face, canon) if canon is not None else None
        self._overlay.draw(frame, mask, landmarks, settings, expression=expression)

    def _guard(self, stage: str, fn, *args) -> None:
        try:
            fn(*args)
        except Exception:
            now = time.monotonic()
            if now - self._last_error > 2.0:
                self._last_error = now
                log.exception("Error en la etapa %s", stage)

    def close(self) -> None:
        self._pool.shutdown(wait=True, cancel_futures=True)
        if self._tracker is not None:
            self._tracker.close()
            self._tracker = None
        self._background.close()
