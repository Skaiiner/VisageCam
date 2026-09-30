import logging

import cv2
import numpy as np

from visagecam.config import Settings
from visagecam.masks.library import MaskLibrary
from visagecam.processing.background import BackgroundRenderer
from visagecam.processing.enhance import Enhancer
from visagecam.processing.neutral import NeutralFace
from visagecam.processing.beauty import BeautyRenderer
from visagecam.processing.face_warp import FaceWarpRenderer
from visagecam.processing.landmarks import FaceTracker
from visagecam.processing.overlay import OverlayRenderer

log = logging.getLogger(__name__)

DEFAULT_ADJUST = (1.0, 0.0, 0.0, 0.0)


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
        self.neutral = NeutralFace()
        self.face_found = False

    def recalibrate(self) -> None:
        self.neutral.start_calibration()

    def process(self, frame: np.ndarray) -> np.ndarray:
        settings = self.settings
        if settings.mirror:
            frame = cv2.flip(frame, 1)
        enhanced = self._enhancer.apply(frame, float(settings.enhance))
        owned = enhanced is not frame
        frame = enhanced
        mask = self.library.get(settings.active_mask) if settings.active_mask else None
        extras = [a for a in (self.library.get(i) for i in settings.accessories) if a is not None]
        beauty = BeautyRenderer.active(settings)
        landmarks = None
        if mask is not None or extras or beauty:
            if self._tracker is None:
                self._tracker = FaceTracker()
            landmarks = self._tracker.process(frame)
            if landmarks is not None:
                if settings.expression and not self.neutral.ready:
                    self.neutral.observe(landmarks)
            else:
                landmarks = self._tracker.held()
                if landmarks is None:
                    self._overlay.reset()
                    self._face.reset()
        self.face_found = landmarks is not None
        if settings.background_mode != "none":
            frame = self._background.apply(frame, settings)
        elif not owned:
            frame = frame.copy()
        if landmarks is not None:
            if beauty:
                self._beauty.draw(frame, landmarks, settings)
            if mask is not None:
                if mask.is_face and settings.face_warp:
                    self._face.draw(frame, mask, landmarks, settings)
                else:
                    canon = self.neutral.canonical_for(mask) if settings.expression else None
                    expression = (self._face, canon) if canon is not None else None
                    self._overlay.draw(frame, mask, landmarks, settings, expression=expression)
            for accessory in extras:
                values = settings.accessory_adjust.get(accessory.mask_id, DEFAULT_ADJUST)
                self._overlay.draw(frame, accessory, landmarks, settings, tuple(values), 1.0)
        return frame

    def close(self) -> None:
        if self._tracker is not None:
            self._tracker.close()
            self._tracker = None
        self._background.close()
