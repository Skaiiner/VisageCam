import logging
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from visagecam.config import Settings

log = logging.getLogger(__name__)


class BackgroundRenderer:
    def __init__(self) -> None:
        self._segmenter = None
        self._previous: np.ndarray | None = None
        self._image_path = ""
        self._image: np.ndarray | None = None
        self._image_size = (0, 0)

    def _ensure_segmenter(self):
        if self._segmenter is None:
            self._segmenter = mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=1)
        return self._segmenter

    def _person_mask(self, frame: np.ndarray) -> np.ndarray:
        height, width = frame.shape[:2]
        small = cv2.resize(frame, (256, 144), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        raw = self._ensure_segmenter().process(rgb).segmentation_mask
        if raw is None:
            raw = np.ones((144, 256), np.float32)
        if self._previous is not None and self._previous.shape == raw.shape:
            raw = 0.55 * raw + 0.45 * self._previous
        self._previous = raw
        soft = np.clip((raw - 0.35) / 0.3, 0.0, 1.0)
        soft = cv2.GaussianBlur(soft, (0, 0), 1.2)
        return cv2.resize(soft, (width, height), interpolation=cv2.INTER_LINEAR)

    def _load_image(self, path: str, size: tuple[int, int]) -> np.ndarray | None:
        if path == self._image_path and self._image is not None and self._image_size == size:
            return self._image
        self._image_path = path
        self._image = None
        self._image_size = size
        if not path or not Path(path).is_file():
            return None
        data = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
        if data is None:
            log.warning("No se pudo leer la imagen de fondo %s", path)
            return None
        width, height = size
        scale = max(width / data.shape[1], height / data.shape[0])
        resized = cv2.resize(
            data, (int(data.shape[1] * scale + 0.5), int(data.shape[0] * scale + 0.5)), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
        )
        ox = (resized.shape[1] - width) // 2
        oy = (resized.shape[0] - height) // 2
        self._image = np.ascontiguousarray(resized[oy : oy + height, ox : ox + width])
        return self._image

    @staticmethod
    def _blurred(frame: np.ndarray, strength: int) -> np.ndarray:
        height, width = frame.shape[:2]
        small = cv2.resize(frame, (width // 4, height // 4), interpolation=cv2.INTER_AREA)
        sigma = max(1.0, strength / 4.0)
        small = cv2.GaussianBlur(small, (0, 0), sigma)
        return cv2.resize(small, (width, height), interpolation=cv2.INTER_LINEAR)

    def apply(self, frame: np.ndarray, settings: Settings) -> np.ndarray:
        mode = settings.background_mode
        if mode == "blur":
            background = self._blurred(frame, settings.blur_strength)
        elif mode == "image":
            background = self._load_image(settings.background_image, (frame.shape[1], frame.shape[0]))
            if background is None:
                return frame
        else:
            return frame
        person = self._person_mask(frame)[..., None]
        return (frame * person + background * (1.0 - person)).astype(np.uint8)

    def close(self) -> None:
        if self._segmenter is not None:
            self._segmenter.close()
            self._segmenter = None
        self._previous = None
