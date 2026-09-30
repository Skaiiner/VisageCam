import math

import cv2
import numpy as np

from visagecam.processing.blend import mix

TARGET_LUMA = 118.0


class Enhancer:
    def __init__(self) -> None:
        self._luma: float | None = None
        self._lut_key = -1
        self._lut = np.arange(256, dtype=np.uint8)

    def prepare(self, sample_frame: np.ndarray, amount: float) -> None:
        if amount <= 0.01:
            return
        luma = float(sample_frame[::8, ::8].mean())
        self._luma = luma if self._luma is None else 0.9 * self._luma + 0.1 * luma
        current = min(max(self._luma, 20.0), 235.0)
        gamma = math.log(TARGET_LUMA / 255.0) / math.log(current / 255.0)
        gamma = 1.0 - amount * (1.0 - min(max(gamma, 0.55), 1.0))
        key = int(gamma * 100)
        if key != self._lut_key:
            self._lut_key = key
            ramp = np.arange(256, dtype=np.float32) / 255.0
            self._lut = np.clip((ramp**gamma) * 255.0, 0, 255).astype(np.uint8)

    def tone(self, frame: np.ndarray, amount: float) -> np.ndarray:
        if amount <= 0.01:
            return frame
        return cv2.LUT(frame, self._lut)

    def finish(self, frame: np.ndarray, amount: float) -> np.ndarray:
        if amount <= 0.01:
            return frame
        out = cv2.LUT(frame, self._lut)
        blur = cv2.GaussianBlur(out, (5, 5), 1.1)
        strength = 0.55 * amount
        return cv2.addWeighted(out, 1.0 + strength, blur, -strength, 0)

    def apply(self, frame: np.ndarray, amount: float) -> np.ndarray:
        self.prepare(frame, amount)
        return self.finish(frame, amount)


class Denoiser:
    def __init__(self) -> None:
        self._prev: np.ndarray | None = None
        self._prev_gray: np.ndarray | None = None

    def reset(self) -> None:
        self._prev = None
        self._prev_gray = None

    def apply(self, frame: np.ndarray, amount: float) -> np.ndarray:
        if amount <= 0.05:
            self.reset()
            return frame
        height, width = frame.shape[:2]
        small = cv2.cvtColor(cv2.resize(frame, (width // 8, height // 8), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        prev, prev_gray = self._prev, self._prev_gray
        if prev is None or prev.shape != frame.shape or prev_gray is None or prev_gray.shape != small.shape:
            self._prev, self._prev_gray = frame, small
            return frame
        motion = cv2.convertScaleAbs(cv2.subtract(cv2.absdiff(small, prev_gray), 3), alpha=20.0)
        motion = cv2.dilate(motion, np.ones((3, 3), np.uint8))
        still = cv2.resize(255 - motion, (width, height), interpolation=cv2.INTER_LINEAR)
        weight = cv2.convertScaleAbs(still, alpha=0.55 * min(amount, 1.0))
        out = mix(frame, prev, weight)
        self._prev, self._prev_gray = out, small
        return out
