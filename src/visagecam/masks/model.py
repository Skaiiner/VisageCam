# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

from dataclasses import dataclass, field

import cv2
import numpy as np


@dataclass(frozen=True)
class Anchor:
    name: str
    landmarks: tuple[int, ...]
    point: tuple[float, float]


@dataclass
class Mask:
    mask_id: str
    name: str
    image: np.ndarray
    anchors: list[Anchor] = field(default_factory=list)
    face_landmarks: np.ndarray | None = None
    builtin: bool = False
    kind: str = "mask"
    slot: str = "free"
    pivot: tuple[float, float] | None = None
    width_ratio: float | None = None
    content_box: tuple[int, int, int, int] = (0, 0, 0, 0)
    mean_luma: float = 128.0

    def __post_init__(self) -> None:
        alpha = self.image[:, :, 3]
        solid = alpha > 16
        if solid.any():
            self.content_box = cv2.boundingRect(solid.astype(np.uint8))
            gray = cv2.cvtColor(self.image[:, :, :3], cv2.COLOR_BGR2GRAY)
            self.mean_luma = float(gray[solid].mean())
        else:
            self.content_box = (0, 0, self.image.shape[1], self.image.shape[0])

    @property
    def is_face(self) -> bool:
        return self.face_landmarks is not None

    def thumbnail(self, size: int) -> np.ndarray:
        x, y, w, h = self.content_box
        crop = self.image[y : y + h, x : x + w]
        scale = size / max(w, h)
        resized = cv2.resize(
            crop, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA
        )
        canvas = np.zeros((size, size, 4), dtype=np.uint8)
        oy = (size - resized.shape[0]) // 2
        ox = (size - resized.shape[1]) // 2
        canvas[oy : oy + resized.shape[0], ox : ox + resized.shape[1]] = resized
        return canvas
