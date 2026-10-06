# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

import logging
import time
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np

from visagecam.config import FilterProfile, Settings
from visagecam.masks.library import MaskLibrary
from visagecam.processing.background import BackgroundRenderer
from visagecam.processing.beauty import BeautyRenderer
from visagecam.processing.blend import mix
from visagecam.processing.camera_effects import CameraEffectRenderer, CameraGrader
from visagecam.processing.distortion import DistortionRenderer
from visagecam.processing.enhance import Denoiser, Enhancer
from visagecam.processing.face_warp import FaceWarpRenderer
from visagecam.processing.landmarks import FaceTracker, MultiFaceTracker, face_width
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
        self._multi_tracker: MultiFaceTracker | None = None
        self._background = BackgroundRenderer()
        self._overlay = OverlayRenderer()
        self._face = FaceWarpRenderer()
        self._beauty = BeautyRenderer()
        self._distortion = DistortionRenderer()
        self._camera_fx = CameraEffectRenderer()
        self._grader = CameraGrader()
        self._enhancer = Enhancer()
        self._denoiser = Denoiser()
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="visagecam")
        self.neutral = NeutralFace()
        self.neutral2 = NeutralFace(suffix="_2")
        self.face_found = False
        self.faces_found = (False, False)
        self._last_error = 0.0

    def recalibrate(self, person: int = 1) -> None:
        (self.neutral if person == 1 else self.neutral2).start_calibration()

    def process(self, frame: np.ndarray) -> np.ndarray:
        settings = self.settings
        if settings.mirror_mode == "both":
            frame = cv2.flip(frame, 1)
        height, width = frame.shape[:2]
        amount = float(settings.enhance)
        dual = bool(settings.dual_faces)
        profile1 = settings.primary_profile()
        profiles = (profile1, settings.person2) if dual else (profile1,)
        need_track = dual or any(self._profile_needs_face(p) for p in profiles)
        need_bg = settings.background_mode != "none"

        small, factor = frame, 1.0
        if (need_track or need_bg) and width > ANALYSIS_WIDTH:
            small = cv2.resize(
                frame, (ANALYSIS_WIDTH, int(height * ANALYSIS_WIDTH / width)), interpolation=cv2.INTER_AREA
            )
            factor = width / ANALYSIS_WIDTH
        if need_track or need_bg or amount > 0.01:
            self._enhancer.prepare(small, amount)
        track_job = backdrop_job = None
        if need_track:
            tone = self._enhancer.tone(small, amount)
            if dual:
                if self._multi_tracker is None:
                    self._multi_tracker = MultiFaceTracker()
                track_job = self._pool.submit(self._multi_tracker.process, tone, factor)
            else:
                if self._tracker is None:
                    self._tracker = FaceTracker()
                track_job = self._pool.submit(self._tracker.process, tone, factor)
        if need_bg:
            tone = self._enhancer.tone(small, amount)
            backdrop_job = self._pool.submit(self._backdrop, tone, (width, height))

        full = self._enhancer.finish(self._denoiser.apply(frame, amount), amount)
        owned = full is not frame

        people: list[tuple[FilterProfile, np.ndarray, NeutralFace] | None]
        if dual:
            people = self._resolve_dual(track_job, full)
        else:
            people = self._resolve_single(track_job, full, profile1)

        self.faces_found = tuple(p is not None for p in people) if dual else (people[0] is not None, False)
        self.face_found = self.faces_found[0] or self.faces_found[1]

        frame = full
        composed = None
        if backdrop_job is not None:
            try:
                backdrop, person_mask = backdrop_job.result()
            except Exception:
                log.exception("Error en el fondo")
                backdrop = person_mask = None
            if backdrop is not None and person_mask is not None:
                composed = mix(backdrop, full, person_mask)
        if composed is not None:
            frame = composed
        elif not owned:
            frame = frame.copy()

        for entry in people:
            if entry is None:
                continue
            profile, landmarks, neutral = entry
            self._apply_profile(frame, profile, landmarks, neutral)
        return self._finish(frame)

    def _finish(self, frame: np.ndarray) -> np.ndarray:
        settings = self.settings
        if CameraGrader.active(settings):
            try:
                frame = self._grader.apply(
                    frame,
                    settings.grade_brightness,
                    settings.grade_contrast,
                    settings.grade_saturation,
                    settings.grade_temperature,
                )
            except Exception:
                self._note_error("color")
        if settings.camera_effect:
            try:
                frame = self._camera_fx.apply(frame, settings.camera_effect, settings.camera_effect_strength)
            except Exception:
                self._note_error("efecto de camara")
        return frame

    def _note_error(self, stage: str) -> None:
        now = time.monotonic()
        if now - self._last_error > 2.0:
            self._last_error = now
            log.exception("Error en la etapa %s", stage)

    @staticmethod
    def _profile_needs_face(profile: FilterProfile) -> bool:
        return (
            bool(profile.active_mask)
            or bool(profile.accessories)
            or bool(profile.distortion)
            or BeautyRenderer.active(profile)
        )

    def _resolve_single(self, track_job, frame: np.ndarray, profile: FilterProfile):
        if track_job is None:
            return [None]
        landmarks = None
        try:
            landmarks = track_job.result()
        except Exception:
            log.exception("Error en el seguimiento facial")
        if not usable(landmarks, frame):
            landmarks = None
        if landmarks is not None:
            if profile.expression and not self.neutral.ready:
                self.neutral.observe(landmarks)
        else:
            landmarks = self._tracker.held()
            if not usable(landmarks, frame):
                landmarks = None
            if landmarks is None:
                self._overlay.reset()
                self._face.reset()
        if landmarks is None:
            return [None]
        return [(profile, landmarks, self.neutral)]

    def _resolve_dual(self, track_job, frame: np.ndarray):
        raw: list[np.ndarray | None] = [None, None]
        if track_job is not None:
            try:
                raw = track_job.result()
            except Exception:
                log.exception("Error en el seguimiento facial")
                raw = [None, None]
        held = self._multi_tracker.held() if self._multi_tracker is not None else [None, None]
        profiles = (self.settings.primary_profile(), self.settings.person2)
        neutrals = (self.neutral, self.neutral2)
        results: list[tuple[FilterProfile, np.ndarray, NeutralFace] | None] = [None, None]
        for slot in range(2):
            landmarks = raw[slot] if usable(raw[slot], frame) else None
            if landmarks is not None and profiles[slot].expression and not neutrals[slot].ready:
                neutrals[slot].observe(landmarks)
            if landmarks is None:
                landmarks = held[slot] if usable(held[slot], frame) else None
            if landmarks is None:
                continue
            results[slot] = (profiles[slot], landmarks, neutrals[slot])
        return results

    def _apply_profile(
        self, frame: np.ndarray, profile: FilterProfile, landmarks: np.ndarray, neutral: NeutralFace
    ) -> None:
        mask = self.library.get(profile.active_mask) if profile.active_mask else None
        extras = [a for a in (self.library.get(i) for i in profile.accessories) if a is not None]
        if BeautyRenderer.active(profile):
            self._guard("belleza", self._beauty.draw, frame, landmarks, profile)
        if profile.distortion:
            self._guard("deformacion", self._distortion.draw, frame, landmarks, profile)
        if mask is not None:
            if mask.is_face and profile.face_warp:
                self._guard("rostro", self._face.draw, frame, mask, landmarks, profile)
            else:
                self._guard("mascara", self._draw_mask, frame, mask, landmarks, profile, neutral)
        for accessory in extras:
            values = profile.accessory_adjust.get(accessory.mask_id, DEFAULT_ADJUST)
            self._guard(
                "accesorio", self._overlay.draw, frame, accessory, landmarks, profile, tuple(values), 1.0
            )

    def _backdrop(self, small: np.ndarray, size: tuple[int, int]):
        backdrop = self._background.backdrop(small, self.settings, size)
        if backdrop is None:
            return None, None
        person = self._background.mask(small)
        return backdrop, cv2.resize(person, size, interpolation=cv2.INTER_LINEAR)

    def _draw_mask(
        self, frame: np.ndarray, mask, landmarks: np.ndarray, profile: FilterProfile, neutral: NeutralFace
    ) -> None:
        canon = neutral.canonical_for(mask) if profile.expression else None
        expression = (self._face, canon) if canon is not None else None
        self._overlay.draw(frame, mask, landmarks, profile, expression=expression)

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
        if self._multi_tracker is not None:
            self._multi_tracker.close()
            self._multi_tracker = None
        self._background.close()
