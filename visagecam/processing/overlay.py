import math

import cv2
import numpy as np

from visagecam.config import Settings
from visagecam.masks.model import Mask
from visagecam.processing.blend import blend_premultiplied
from visagecam.processing.landmarks import (
    FACE_OVAL,
    face_roll,
    face_width,
    group_center,
)
from visagecam.processing.transforms import adjustment, similarity, to3


class OverlayRenderer:
    def __init__(self) -> None:
        self._pyramids: dict[str, list[np.ndarray]] = {}
        self._luma: float | None = None

    def reset(self) -> None:
        self._luma = None

    def _pyramid(self, mask: Mask) -> list[np.ndarray]:
        levels = self._pyramids.get(mask.mask_id)
        if levels is None or levels[0].shape != mask.image.shape:
            alpha = mask.image[:, :, 3:4].astype(np.float32) / 255.0
            pre = np.dstack([mask.image[:, :, :3].astype(np.float32) * alpha, alpha * 255.0])
            levels = [pre.astype(np.uint8)]
            while min(levels[-1].shape[:2]) >= 256 and len(levels) < 4:
                last = levels[-1]
                levels.append(cv2.resize(last, (last.shape[1] // 2, last.shape[0] // 2), interpolation=cv2.INTER_AREA))
            self._pyramids[mask.mask_id] = levels
        return levels

    @staticmethod
    def _base(mask: Mask, landmarks: np.ndarray) -> np.ndarray:
        if mask.anchors:
            src = np.array([a.point for a in mask.anchors], dtype=np.float64)
            dst = np.array([group_center(landmarks, a.landmarks) for a in mask.anchors], dtype=np.float64)
            return to3(similarity(src, dst))
        bx, by, bw, bh = mask.content_box
        fw = face_width(landmarks)
        center = landmarks[FACE_OVAL].mean(axis=0)
        roll = face_roll(landmarks)
        scale = 1.6 * fw / max(bw, bh, 1)
        cos, sin = math.cos(roll) * scale, math.sin(roll) * scale
        cx, cy = bx + bw / 2.0, by + bh / 2.0
        return np.array(
            [
                [cos, -sin, center[0] - cos * cx + sin * cy],
                [sin, cos, center[1] - sin * cx - cos * cy],
                [0.0, 0.0, 1.0],
            ]
        )

    def _light_gain(self, frame: np.ndarray, landmarks: np.ndarray, mask: Mask, amount: float) -> float:
        if amount <= 0.01:
            return 1.0
        pts = landmarks[FACE_OVAL]
        x0, y0 = np.maximum(pts.min(axis=0).astype(int), 0)
        x1, y1 = pts.max(axis=0).astype(int)
        crop = frame[y0 : max(y1, y0 + 2), x0 : max(x1, x0 + 2)]
        if crop.size == 0:
            return 1.0
        small = cv2.resize(crop, (24, 24), interpolation=cv2.INTER_AREA)
        luma = float(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).mean())
        self._luma = luma if self._luma is None else 0.85 * self._luma + 0.15 * luma
        ratio = (self._luma + 20.0) / (mask.mean_luma + 20.0)
        return float(np.clip(ratio ** (0.8 * amount), 0.55, 1.5))

    def draw(self, frame: np.ndarray, mask: Mask, landmarks: np.ndarray, settings: Settings) -> None:
        height, width = frame.shape[:2]
        fw = face_width(landmarks)
        base = self._base(mask, landmarks)
        center = landmarks[FACE_OVAL].mean(axis=0)
        adj = adjustment(
            center,
            settings.mask_scale,
            settings.mask_rotation,
            (settings.mask_offset_x * fw, settings.mask_offset_y * fw),
        )
        full = adj @ base
        scale = math.sqrt(abs(np.linalg.det(full[:2, :2])))
        levels = self._pyramid(mask)
        level = int(np.clip(math.floor(math.log2(1.0 / max(scale, 1e-3))), 0, len(levels) - 1))
        image = levels[level]
        factor = 0.5**level
        m = full @ np.diag([1.0 / factor, 1.0 / factor, 1.0])

        h, w = image.shape[:2]
        corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float64)
        moved = corners @ m[:2, :2].T + m[:2, 2]
        x0 = int(max(0, math.floor(moved[:, 0].min())))
        y0 = int(max(0, math.floor(moved[:, 1].min())))
        x1 = int(min(width, math.ceil(moved[:, 0].max())))
        y1 = int(min(height, math.ceil(moved[:, 1].max())))
        if x1 - x0 < 4 or y1 - y0 < 4:
            return
        shift = m.copy()
        shift[0, 2] -= x0
        shift[1, 2] -= y0
        warped = cv2.warpAffine(
            image,
            shift[:2],
            (x1 - x0, y1 - y0),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )
        softness = float(np.clip(settings.edge_softness, 0.0, 1.0))
        if softness > 0.05:
            warped = cv2.GaussianBlur(warped, (0, 0), 0.4 + 1.6 * softness)
        gain = self._light_gain(frame, landmarks, mask, float(settings.light_match))
        opacity = float(np.clip(settings.mask_opacity, 0.0, 1.0))
        alpha = warped[:, :, 3].astype(np.float32) / 255.0 * opacity
        pre = warped[:, :, :3].astype(np.float32) * (gain * opacity)
        blend_premultiplied(frame, x0, y0, pre, alpha)
