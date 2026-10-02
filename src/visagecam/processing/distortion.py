from dataclasses import dataclass
from typing import NamedTuple

import cv2
import numpy as np

from visagecam.processing.landmarks import (
    CHIN,
    EYE_LEFT,
    EYE_RIGHT,
    FACE_EDGE_LEFT,
    FACE_EDGE_RIGHT,
    FACE_OVAL,
    FOREHEAD,
    MOUTH_CENTER,
    NOSE_TIP,
    face_width,
    group_center,
)


class DistortionPoint(NamedTuple):
    landmarks: tuple
    radius_ratio: float
    strength: float


@dataclass(frozen=True)
class DistortionPreset:
    name: str
    points: tuple[DistortionPoint, ...]


PRESETS: dict[str, DistortionPreset] = {
    "big_eyes": DistortionPreset("Ojos grandes", (
        DistortionPoint(EYE_LEFT, 0.24, 0.55),
        DistortionPoint(EYE_RIGHT, 0.24, 0.55),
    )),
    "tiny_eyes": DistortionPreset("Ojos pequenos", (
        DistortionPoint(EYE_LEFT, 0.22, -0.45),
        DistortionPoint(EYE_RIGHT, 0.22, -0.45),
    )),
    "big_forehead": DistortionPreset("Frente grande", (
        DistortionPoint(FOREHEAD, 0.34, 0.45),
    )),
    "big_mouth": DistortionPreset("Boca grande", (
        DistortionPoint(MOUTH_CENTER, 0.2, 0.5),
    )),
    "small_nose": DistortionPreset("Nariz pequena", (
        DistortionPoint(NOSE_TIP, 0.16, -0.55),
    )),
    "big_chin": DistortionPreset("Menton grande", (
        DistortionPoint(CHIN, 0.18, 0.4),
    )),
    "slim_face": DistortionPreset("Cara delgada", (
        DistortionPoint((FACE_EDGE_LEFT,), 0.32, -0.4),
        DistortionPoint((FACE_EDGE_RIGHT,), 0.32, -0.4),
    )),
    "bobble_head": DistortionPreset("Cabeza grande", (
        DistortionPoint(tuple(FACE_OVAL), 0.62, 0.38),
    )),
    "tiny_face": DistortionPreset("Cara mini", (
        DistortionPoint(tuple(FACE_OVAL), 0.68, -0.32),
    )),
    "funhouse": DistortionPreset("Espejo loco", (
        DistortionPoint(EYE_LEFT, 0.2, 0.6),
        DistortionPoint(EYE_RIGHT, 0.2, -0.5),
        DistortionPoint(MOUTH_CENTER, 0.22, 0.55),
    )),
}


class DistortionRenderer:
    def draw(self, frame: np.ndarray, landmarks: np.ndarray, profile) -> None:
        preset = PRESETS.get(getattr(profile, "distortion", ""))
        if preset is None:
            return
        fw = face_width(landmarks)
        if fw < 8:
            return
        multiplier = float(np.clip(getattr(profile, "distortion_strength", 1.0), 0.3, 2.0))
        height, width = frame.shape[:2]
        for point in preset.points:
            center = group_center(landmarks, point.landmarks)
            radius = point.radius_ratio * fw
            strength = float(np.clip(point.strength * multiplier, -0.85, 0.85))
            self._apply(frame, center, radius, strength, width, height)

    @staticmethod
    def _apply(frame: np.ndarray, center: np.ndarray, radius: float, strength: float, width: int, height: int) -> None:
        if radius < 6 or abs(strength) < 0.02:
            return
        pad = int(radius) + 2
        x0 = int(max(0, center[0] - pad))
        y0 = int(max(0, center[1] - pad))
        x1 = int(min(width, center[0] + pad))
        y1 = int(min(height, center[1] + pad))
        bw, bh = x1 - x0, y1 - y0
        if bw < 4 or bh < 4:
            return
        crop = np.ascontiguousarray(frame[y0:y1, x0:x1])
        ys, xs = np.mgrid[0:bh, 0:bw].astype(np.float32)
        cx, cy = float(center[0] - x0), float(center[1] - y0)
        dx, dy = xs - cx, ys - cy
        dist = np.sqrt(dx * dx + dy * dy)
        falloff = np.clip(1.0 - dist / radius, 0.0, 1.0)
        factor = strength * (falloff * falloff)
        scale = np.clip(1.0 - factor, 0.15, 3.0)
        map_x = cx + dx * scale
        map_y = cy + dy * scale
        warped = cv2.remap(crop, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        frame[y0:y1, x0:x1] = warped
