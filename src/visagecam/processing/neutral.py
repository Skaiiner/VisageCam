# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

import json
import logging
import math

import numpy as np

from visagecam.config import data_dir
from visagecam.masks.model import Mask
from visagecam.processing.landmarks import (
    EYE_LEFT,
    EYE_RIGHT,
    FACE_EDGE_LEFT,
    FACE_EDGE_RIGHT,
    MESH_POINTS,
    face_roll,
    face_width,
    group_center,
    mouth_open_ratio,
)
from visagecam.processing.transforms import similarity

log = logging.getLogger(__name__)

FRAMES_NEEDED = 12


def face_space(points: np.ndarray) -> np.ndarray:
    left = group_center(points, EYE_LEFT)
    right = group_center(points, EYE_RIGHT)
    delta = right - left
    ioc = float(np.linalg.norm(delta)) or 1.0
    angle = math.atan2(float(delta[1]), float(delta[0]))
    cos, sin = math.cos(-angle), math.sin(-angle)
    rot = np.array([[cos, -sin], [sin, cos]])
    return ((points[:MESH_POINTS] - (left + right) / 2.0) @ rot.T / ioc).astype(np.float32)


def yaw_estimate(points: np.ndarray) -> float:
    fw = face_width(points) or 1.0
    left = np.linalg.norm(points[1] - points[FACE_EDGE_LEFT])
    right = np.linalg.norm(points[FACE_EDGE_RIGHT] - points[1])
    return float((left - right) / fw)


class NeutralFace:
    def __init__(self, suffix: str = "") -> None:
        self.path = data_dir() / f"neutral_face{suffix}.json"
        self.points: np.ndarray | None = None
        self.version = 0
        self.calibrating = False
        self._samples: list[np.ndarray] = []
        self._cache: dict[tuple[str, int], np.ndarray] = {}
        self._load()

    @property
    def ready(self) -> bool:
        return self.points is not None and not self.calibrating

    @property
    def progress(self) -> float:
        return min(1.0, len(self._samples) / FRAMES_NEEDED)

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = np.array(json.loads(self.path.read_text(encoding="utf-8"))["points"], dtype=np.float32)
        except (OSError, ValueError, KeyError):
            return
        if data.shape == (MESH_POINTS, 2):
            self.points = data
            self.version = 1

    def start_calibration(self) -> None:
        self.calibrating = True
        self._samples.clear()

    def observe(self, landmarks: np.ndarray) -> None:
        if self.ready:
            return
        frontal = (
            mouth_open_ratio(landmarks) < 0.02
            and abs(yaw_estimate(landmarks)) < 0.07
            and abs(face_roll(landmarks)) < 0.25
        )
        if not frontal:
            self._samples.clear()
            return
        self._samples.append(face_space(landmarks))
        if len(self._samples) >= FRAMES_NEEDED:
            self.points = np.mean(self._samples, axis=0).astype(np.float32)
            self._samples.clear()
            self.calibrating = False
            self.version += 1
            self._cache.clear()
            try:
                self.path.write_text(
                    json.dumps({"points": np.round(self.points, 5).tolist()}), encoding="utf-8"
                )
            except OSError:
                log.exception("No se pudo guardar el rostro neutro")
            log.info("Rostro neutro calibrado")

    def canonical_for(self, mask: Mask) -> np.ndarray | None:
        if not self.ready or not mask.anchors or mask.face_landmarks is not None:
            return None
        key = (mask.mask_id, self.version)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        src = np.array([group_center(self.points, a.landmarks) for a in mask.anchors], dtype=np.float64)
        dst = np.array([a.point for a in mask.anchors], dtype=np.float64)
        fit = similarity(src, dst)
        canon = (self.points @ fit[:, :2].T + fit[:, 2]).astype(np.float32)
        self._cache[key] = canon
        return canon
