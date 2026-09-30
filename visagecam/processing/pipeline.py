import logging

import cv2
import numpy as np

from visagecam.config import Settings
from visagecam.masks.library import MaskLibrary
from visagecam.processing.background import BackgroundRenderer
from visagecam.processing.face_warp import FaceWarpRenderer
from visagecam.processing.landmarks import FaceTracker
from visagecam.processing.overlay import OverlayRenderer

log = logging.getLogger(__name__)

HOLD_FRAMES = 4


class FramePipeline:
    def __init__(self, settings: Settings, library: MaskLibrary) -> None:
        self.settings = settings
        self.library = library
        self._tracker: FaceTracker | None = None
        self._background = BackgroundRenderer()
        self._overlay = OverlayRenderer()
        self._face = FaceWarpRenderer()
        self._last_landmarks: np.ndarray | None = None
        self._lost = 0
        self.face_found = False

    def process(self, frame: np.ndarray) -> np.ndarray:
        settings = self.settings
        if settings.mirror:
            frame = cv2.flip(frame, 1)
        mask = self.library.get(settings.active_mask) if settings.active_mask else None
        landmarks = None
        if mask is not None:
            if self._tracker is None:
                self._tracker = FaceTracker()
            landmarks = self._tracker.process(frame)
            if landmarks is None and self._last_landmarks is not None and self._lost < HOLD_FRAMES:
                self._lost += 1
                landmarks = self._last_landmarks
            elif landmarks is not None:
                self._lost = 0
                self._last_landmarks = landmarks
            else:
                self._last_landmarks = None
                self._overlay.reset()
                self._face.reset()
        self.face_found = landmarks is not None
        if settings.background_mode != "none":
            frame = self._background.apply(frame, settings)
        else:
            frame = frame.copy()
        if mask is not None and landmarks is not None:
            if mask.is_face and settings.face_warp:
                self._face.draw(frame, mask, landmarks, settings)
            else:
                self._overlay.draw(frame, mask, landmarks, settings)
        return frame

    def close(self) -> None:
        if self._tracker is not None:
            self._tracker.close()
            self._tracker = None
        self._background.close()
