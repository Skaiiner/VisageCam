# Copyright (c) 2026 Skain. Todos los derechos reservados.

import math
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

CHEEK_LEFT = (205,)
CHEEK_RIGHT = (425,)
FACE_CENTER = tuple(FACE_OVAL)

CATEGORIES = (
    ("all", "Todos"),
    ("eyes", "Ojos"),
    ("mouth", "Boca y nariz"),
    ("face", "Cara"),
    ("fun", "Locos"),
)

KIND_LIMITS = {"bulge": 0.85, "stretch": 0.85, "swirl": 1.5, "shift": 0.7}


class DistortionPoint(NamedTuple):
    landmarks: tuple
    radius_ratio: float
    strength: float
    kind: str = "bulge"
    angle: float = 0.0


@dataclass(frozen=True)
class DistortionPreset:
    name: str
    points: tuple[DistortionPoint, ...]
    category: str = "face"


PRESETS: dict[str, DistortionPreset] = {
    "big_eyes": DistortionPreset(
        "Ojos grandes",
        (DistortionPoint(EYE_LEFT, 0.24, 0.55), DistortionPoint(EYE_RIGHT, 0.24, 0.55)),
        "eyes",
    ),
    "tiny_eyes": DistortionPreset(
        "Ojos pequenos",
        (DistortionPoint(EYE_LEFT, 0.22, -0.45), DistortionPoint(EYE_RIGHT, 0.22, -0.45)),
        "eyes",
    ),
    "bug_eyes": DistortionPreset(
        "Ojos saltones",
        (DistortionPoint(EYE_LEFT, 0.3, 0.85), DistortionPoint(EYE_RIGHT, 0.3, 0.85)),
        "eyes",
    ),
    "eyes_apart": DistortionPreset(
        "Ojos separados",
        (
            DistortionPoint(EYE_LEFT, 0.26, 0.45, "shift", 180),
            DistortionPoint(EYE_RIGHT, 0.26, 0.45, "shift", 0),
        ),
        "eyes",
    ),
    "eyes_together": DistortionPreset(
        "Ojos juntos",
        (
            DistortionPoint(EYE_LEFT, 0.26, 0.45, "shift", 0),
            DistortionPoint(EYE_RIGHT, 0.26, 0.45, "shift", 180),
        ),
        "eyes",
    ),
    "hypno_eyes": DistortionPreset(
        "Ojos hipnoticos",
        (
            DistortionPoint(EYE_LEFT, 0.22, 1.1, "swirl"),
            DistortionPoint(EYE_RIGHT, 0.22, -1.1, "swirl"),
        ),
        "eyes",
    ),
    "big_mouth": DistortionPreset("Boca grande", (DistortionPoint(MOUTH_CENTER, 0.2, 0.5),), "mouth"),
    "tiny_mouth": DistortionPreset("Boca pequena", (DistortionPoint(MOUTH_CENTER, 0.2, -0.6),), "mouth"),
    "wide_smile": DistortionPreset(
        "Sonrisa enorme", (DistortionPoint(MOUTH_CENTER, 0.3, 0.7, "stretch", 0),), "mouth"
    ),
    "twisted_mouth": DistortionPreset(
        "Boca torcida",
        (
            DistortionPoint(MOUTH_CENTER, 0.2, 0.4, "shift", 20),
            DistortionPoint(MOUTH_CENTER, 0.24, 0.6, "swirl"),
        ),
        "mouth",
    ),
    "small_nose": DistortionPreset("Nariz pequena", (DistortionPoint(NOSE_TIP, 0.16, -0.55),), "mouth"),
    "big_nose": DistortionPreset("Nariz grande", (DistortionPoint(NOSE_TIP, 0.18, 0.65),), "mouth"),
    "big_forehead": DistortionPreset("Frente grande", (DistortionPoint(FOREHEAD, 0.34, 0.45),), "face"),
    "big_chin": DistortionPreset("Menton grande", (DistortionPoint(CHIN, 0.18, 0.4),), "face"),
    "long_chin": DistortionPreset("Menton largo", (DistortionPoint(CHIN, 0.34, 0.6, "stretch", 90),), "face"),
    "fat_cheeks": DistortionPreset(
        "Mejillas grandes",
        (DistortionPoint(CHEEK_LEFT, 0.24, 0.6), DistortionPoint(CHEEK_RIGHT, 0.24, 0.6)),
        "face",
    ),
    "slim_face": DistortionPreset(
        "Cara delgada",
        (
            DistortionPoint((FACE_EDGE_LEFT,), 0.32, -0.4),
            DistortionPoint((FACE_EDGE_RIGHT,), 0.32, -0.4),
        ),
        "face",
    ),
    "stretched_face": DistortionPreset(
        "Cara alargada", (DistortionPoint(FACE_CENTER, 0.8, 0.35, "stretch", 90),), "face"
    ),
    "wide_face": DistortionPreset(
        "Cara ancha", (DistortionPoint(FACE_CENTER, 0.8, 0.35, "stretch", 0),), "face"
    ),
    "pinched_face": DistortionPreset("Cara apretada", (DistortionPoint(NOSE_TIP, 0.5, -0.7),), "face"),
    "bobble_head": DistortionPreset("Cabeza grande", (DistortionPoint(FACE_CENTER, 0.62, 0.38),), "face"),
    "tiny_face": DistortionPreset("Cara mini", (DistortionPoint(FACE_CENTER, 0.68, -0.32),), "face"),
    "alien_head": DistortionPreset(
        "Cabeza alien",
        (DistortionPoint(FOREHEAD, 0.42, 0.7), DistortionPoint(CHIN, 0.3, -0.55)),
        "fun",
    ),
    "swirl_face": DistortionPreset("Remolino", (DistortionPoint(FACE_CENTER, 0.62, 0.9, "swirl"),), "fun"),
    "melting": DistortionPreset(
        "Cara derretida",
        (
            DistortionPoint(CHIN, 0.5, 0.55, "shift", 90),
            DistortionPoint(MOUTH_CENTER, 0.3, 0.5, "stretch", 90),
        ),
        "fun",
    ),
    "chibi": DistortionPreset(
        "Chibi",
        (
            DistortionPoint(EYE_LEFT, 0.28, 0.7),
            DistortionPoint(EYE_RIGHT, 0.28, 0.7),
            DistortionPoint(FACE_CENTER, 0.68, -0.3),
        ),
        "fun",
    ),
    "funhouse": DistortionPreset(
        "Espejo loco",
        (
            DistortionPoint(EYE_LEFT, 0.2, 0.6),
            DistortionPoint(EYE_RIGHT, 0.2, -0.5),
            DistortionPoint(MOUTH_CENTER, 0.22, 0.55),
        ),
        "fun",
    ),
}


def presets_in(category: str) -> list[str]:
    return [pid for pid, preset in PRESETS.items() if category == "all" or preset.category == category]


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
            limit = KIND_LIMITS.get(point.kind, 0.85)
            strength = float(np.clip(point.strength * multiplier, -limit, limit))
            self._apply(frame, center, radius, point.kind, strength, point.angle, width, height)

    @staticmethod
    def _apply(
        frame: np.ndarray,
        center: np.ndarray,
        radius: float,
        kind: str,
        strength: float,
        angle: float,
        width: int,
        height: int,
    ) -> None:
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
        weight = falloff * falloff
        ux, uy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        if kind == "swirl":
            theta = strength * weight * math.pi
            cos, sin = np.cos(theta), np.sin(theta)
            map_x = cx + dx * cos + dy * sin
            map_y = cy - dx * sin + dy * cos
        elif kind == "stretch":
            along = dx * ux + dy * uy
            across = -dx * uy + dy * ux
            scale = np.clip(1.0 - strength * weight, 0.2, 3.0)
            map_x = cx + along * scale * ux - across * uy
            map_y = cy + along * scale * uy + across * ux
        elif kind == "shift":
            displacement = strength * radius * weight
            map_x = xs - ux * displacement
            map_y = ys - uy * displacement
        else:
            scale = np.clip(1.0 - strength * weight, 0.15, 3.0)
            map_x = cx + dx * scale
            map_y = cy + dy * scale
        warped = cv2.remap(
            crop,
            map_x.astype(np.float32),
            map_y.astype(np.float32),
            cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )
        frame[y0:y1, x0:x1] = warped
