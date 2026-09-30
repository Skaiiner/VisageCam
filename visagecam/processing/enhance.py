import math

import cv2
import numpy as np

TARGET_LUMA = 118.0


class Enhancer:
    def __init__(self) -> None:
        self._luma: float | None = None
        self._lut_key = -1
        self._lut = np.arange(256, dtype=np.uint8)

    def apply(self, frame: np.ndarray, amount: float) -> np.ndarray:
        if amount <= 0.01:
            return frame
        sample = frame[::12, ::12]
        luma = float(sample.mean())
        self._luma = luma if self._luma is None else 0.9 * self._luma + 0.1 * luma
        current = min(max(self._luma, 20.0), 235.0)
        gamma = math.log(TARGET_LUMA / 255.0) / math.log(current / 255.0)
        gamma = 1.0 - amount * (1.0 - min(max(gamma, 0.55), 1.0))
        key = int(gamma * 100)
        if key != self._lut_key:
            self._lut_key = key
            ramp = np.arange(256, dtype=np.float32) / 255.0
            self._lut = np.clip((ramp**gamma) * 255.0, 0, 255).astype(np.uint8)
        out = cv2.LUT(frame, self._lut)
        blur = cv2.GaussianBlur(out, (0, 0), 1.3)
        strength = 0.55 * amount
        return cv2.addWeighted(out, 1.0 + strength, blur, -strength, 0)
