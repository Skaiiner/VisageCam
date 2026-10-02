# Copyright (c) 2026 Skain. Todos los derechos reservados.

import cv2
import numpy as np

from visagecam.config import Settings
from visagecam.processing.blend import mix
from visagecam.processing.landmarks import (
    EYE_RING_LEFT,
    EYE_RING_RIGHT,
    FACE_OVAL,
    LIPS_INNER,
    LIPS_OUTER,
    face_width,
)

ROSE = np.diag([0.70, 0.52, 1.30]).astype(np.float32)


def _fill(shape: tuple[int, int], rings, points: np.ndarray) -> np.ndarray:
    layer = np.zeros(shape, np.uint8)
    for ring in rings:
        cv2.fillPoly(layer, [np.round(points[ring] * 16).astype(np.int32)], 255, cv2.LINE_AA, 4)
    return layer


def _scaled(alpha8: np.ndarray, amount: float) -> np.ndarray:
    return cv2.convertScaleAbs(alpha8, alpha=float(amount))


class BeautyRenderer:
    @staticmethod
    def active(settings: Settings) -> bool:
        return (
            max(settings.beauty_smooth, settings.beauty_bright, settings.beauty_lips, settings.beauty_teeth)
            > 0.01
        )

    def draw(self, frame: np.ndarray, landmarks: np.ndarray, settings: Settings) -> None:
        height, width = frame.shape[:2]
        fw = face_width(landmarks)
        pts = landmarks[FACE_OVAL]
        pad = int(fw * 0.05)
        x0 = int(max(0, pts[:, 0].min() - pad))
        y0 = int(max(0, pts[:, 1].min() - pad))
        x1 = int(min(width, pts[:, 0].max() + pad))
        y1 = int(min(height, pts[:, 1].max() + pad))
        if x1 - x0 < 32 or y1 - y0 < 32:
            return
        roi = frame[y0:y1, x0:x1]
        local = landmarks - np.array([x0, y0], dtype=np.float32)
        shape = roi.shape[:2]
        work = np.ascontiguousarray(roi)

        skin = cv2.erode(_fill(shape, [FACE_OVAL], local), np.ones((3, 3), np.uint8))
        keep = _fill(shape, [EYE_RING_LEFT, EYE_RING_RIGHT, LIPS_OUTER], local)
        keep = cv2.dilate(keep, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
        skin = cv2.GaussianBlur(cv2.subtract(skin, keep), (0, 0), max(1.0, fw * 0.02))

        smooth = float(np.clip(settings.beauty_smooth, 0.0, 1.0))
        if smooth > 0.01:
            scale = min(1.0, 320.0 / roi.shape[1])
            small = cv2.resize(
                work,
                (max(8, int(roi.shape[1] * scale)), max(8, int(roi.shape[0] * scale))),
                interpolation=cv2.INTER_AREA,
            )
            filtered = cv2.bilateralFilter(small, 7, 28 + 40 * smooth, 7)
            filtered = cv2.resize(filtered, (roi.shape[1], roi.shape[0]), interpolation=cv2.INTER_LINEAR)
            work = mix(work, filtered, _scaled(skin, smooth * 0.85))

        bright = float(np.clip(settings.beauty_bright, 0.0, 1.0))
        if bright > 0.01:
            lifted = cv2.convertScaleAbs(work, alpha=1.16, beta=9)
            work = mix(work, lifted, _scaled(skin, bright))

        lips = float(np.clip(settings.beauty_lips, 0.0, 1.0))
        if lips > 0.01:
            outer = _fill(shape, [LIPS_OUTER], local)
            inner = _fill(shape, [LIPS_INNER], local)
            band = cv2.GaussianBlur(cv2.subtract(outer, inner), (0, 0), max(1.0, fw * 0.006))
            work = mix(work, cv2.transform(work, ROSE), _scaled(band, lips * 0.7))

        teeth = float(np.clip(settings.beauty_teeth, 0.0, 1.0))
        if teeth > 0.01:
            mouth = _fill(shape, [LIPS_INNER], local)
            ys, xs = np.nonzero(mouth)
            if len(xs) > 20:
                mx0, mx1 = max(0, xs.min() - 3), min(shape[1], xs.max() + 4)
                my0, my1 = max(0, ys.min() - 3), min(shape[0], ys.max() + 4)
                crop = np.ascontiguousarray(work[my0:my1, mx0:mx1])
                soft = (
                    cv2.GaussianBlur(mouth[my0:my1, mx0:mx1], (0, 0), max(1.0, fw * 0.004)).astype(np.float32)
                    / 255.0
                )
                hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV).astype(np.float32)
                weight = soft * np.clip((hsv[:, :, 2] - 110.0) / 60.0, 0.0, 1.0) * teeth
                hsv[:, :, 1] *= 1.0 - 0.7 * weight
                hsv[:, :, 2] = np.minimum(255.0, hsv[:, :, 2] * (1.0 + 0.16 * weight))
                work[my0:my1, mx0:mx1] = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        roi[:] = work
