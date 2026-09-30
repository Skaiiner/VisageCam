import logging
import math
import time
from functools import lru_cache

import cv2
import mediapipe as mp
import numpy as np

log = logging.getLogger(__name__)

MESH_POINTS = 468

EYE_LEFT = (33, 133, 159, 145)
EYE_RIGHT = (362, 263, 386, 374)
NOSE_TIP = (1,)
CHIN = (152,)
FOREHEAD = (10,)
MOUTH_CENTER = (13, 14)
FACE_EDGE_LEFT = 234
FACE_EDGE_RIGHT = 454

FACE_OVAL = [
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378,
    400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21,
    54, 103, 67, 109,
]
STABLE_POINTS = FACE_OVAL + [1, 4, 6, 168, 33, 133, 362, 263, 195, 5]
EYE_RING_LEFT = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
EYE_RING_RIGHT = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
LIPS_OUTER = [
    61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185,
]
LIPS_INNER = [
    78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95,
]

HOLD_SECONDS = 0.8


@lru_cache(maxsize=1)
def mesh_triangles() -> np.ndarray:
    neighbours: dict[int, set[int]] = {}
    for a, b in mp.solutions.face_mesh.FACEMESH_TESSELATION:
        neighbours.setdefault(a, set()).add(b)
        neighbours.setdefault(b, set()).add(a)
    triangles = set()
    for a, b in mp.solutions.face_mesh.FACEMESH_TESSELATION:
        if a > b:
            a, b = b, a
        for c in neighbours[a] & neighbours[b]:
            if c > b:
                triangles.add((a, b, c))
    return np.array(sorted(triangles), dtype=np.int32)


def group_center(points: np.ndarray, indices) -> np.ndarray:
    return points[list(indices)].mean(axis=0)


def face_width(points: np.ndarray) -> float:
    return float(np.linalg.norm(points[FACE_EDGE_RIGHT] - points[FACE_EDGE_LEFT]))


def face_roll(points: np.ndarray) -> float:
    delta = group_center(points, EYE_RIGHT) - group_center(points, EYE_LEFT)
    return math.atan2(float(delta[1]), float(delta[0]))


def mouth_open_ratio(points: np.ndarray) -> float:
    return float(np.linalg.norm(points[13] - points[14]) / (face_width(points) or 1.0))


class LandmarkFilter:
    def __init__(self, min_cutoff: float = 1.6, beta: float = 0.05, d_cutoff: float = 1.0) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.reset()

    def reset(self) -> None:
        self._x: np.ndarray | None = None
        self._dx: np.ndarray | None = None
        self._t = 0.0

    @staticmethod
    def _alpha(cutoff, dt: float):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x: np.ndarray, t: float) -> np.ndarray:
        if self._x is None:
            self._x = x.copy()
            self._dx = np.zeros_like(x)
            self._t = t
            return x
        dt = max(t - self._t, 1e-3)
        self._t = t
        dx = (x - self._x) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        self._dx = a_d * dx + (1.0 - a_d) * self._dx
        speed = np.linalg.norm(self._dx, axis=1, keepdims=True)
        cutoff = self.min_cutoff + self.beta * speed
        a = self._alpha(cutoff, dt)
        self._x = a * x + (1.0 - a) * self._x
        return self._x.copy()

    @property
    def state(self) -> np.ndarray | None:
        return self._x


def _to_array(landmarks, width: int, height: int) -> np.ndarray:
    pts = np.empty((MESH_POINTS, 2), dtype=np.float32)
    for i in range(MESH_POINTS):
        p = landmarks[i]
        pts[i, 0] = p.x * width
        pts[i, 1] = p.y * height
    return pts


def _new_mesh(static: bool):
    return mp.solutions.face_mesh.FaceMesh(
        static_image_mode=static,
        max_num_faces=1,
        refine_landmarks=False,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.4,
    )


class FaceTracker:
    def __init__(self, detect_width: int = 640) -> None:
        self._mesh = _new_mesh(False)
        self._static = None
        self._filter = LandmarkFilter()
        self._detect_width = detect_width
        self._last: np.ndarray | None = None
        self._last_time = 0.0
        self._misses = 0

    def _run(self, mesh, frame: np.ndarray, box: tuple[int, int, int, int], width: int) -> np.ndarray | None:
        x0, y0, x1, y1 = box
        crop = frame[y0:y1, x0:x1]
        ch, cw = crop.shape[:2]
        if cw < 32 or ch < 32:
            return None
        if cw > width:
            crop = cv2.resize(crop, (width, int(ch * width / cw)), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        result = mesh.process(rgb)
        if not result.multi_face_landmarks:
            return None
        points = _to_array(result.multi_face_landmarks[0].landmark, cw, ch)
        return points + np.array([x0, y0], dtype=np.float32)

    def _recovery_box(self, shape) -> tuple[int, int, int, int] | None:
        if self._last is None:
            return None
        height, width = shape[:2]
        lo, hi = self._last.min(axis=0), self._last.max(axis=0)
        center, half = (lo + hi) / 2.0, float(max(hi - lo)) * 1.15
        return (
            int(max(0, center[0] - half)),
            int(max(0, center[1] - half)),
            int(min(width, center[0] + half)),
            int(min(height, center[1] + half)),
        )

    def process(self, frame_bgr: np.ndarray) -> np.ndarray | None:
        height, width = frame_bgr.shape[:2]
        points = self._run(self._mesh, frame_bgr, (0, 0, width, height), self._detect_width)
        if points is None:
            box = self._recovery_box(frame_bgr.shape)
            if self._static is None:
                self._static = _new_mesh(True)
            if box is not None:
                points = self._run(self._static, frame_bgr, box, 512)
            if points is None:
                self._misses += 1
                if self._misses % 3 == 0:
                    points = self._run(self._static, frame_bgr, (0, 0, width, height), 960)
        if points is None:
            return None
        self._misses = 0
        self._last = points
        self._last_time = time.perf_counter()
        return self._filter(points, self._last_time)

    def held(self) -> np.ndarray | None:
        if self._last is not None and time.perf_counter() - self._last_time < HOLD_SECONDS:
            state = self._filter.state
            return state if state is not None else self._last
        return None

    def forget(self) -> None:
        self._filter.reset()
        self._last = None

    def close(self) -> None:
        self._mesh.close()
        if self._static is not None:
            self._static.close()


def detect_static_face(image_bgr: np.ndarray) -> np.ndarray | None:
    height, width = image_bgr.shape[:2]
    rgb = cv2.cvtColor(image_bgr[:, :, :3], cv2.COLOR_BGR2RGB)
    with _new_mesh(True) as mesh:
        result = mesh.process(rgb)
    if not result.multi_face_landmarks:
        return None
    return _to_array(result.multi_face_landmarks[0].landmark, width, height)
