# Copyright (c) 2026 Skain. Todos los derechos reservados.

import math
import time

import mediapipe as mp
import numpy as np

from visagecam.processing.landmarks import FACE_OVAL

UPPER_LIP = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308]
LOWER_LIP = [324, 318, 402, 317, 14, 87, 178, 88, 95]
JAW = [
    14,
    87,
    178,
    88,
    95,
    317,
    402,
    318,
    324,
    17,
    84,
    181,
    91,
    146,
    405,
    321,
    375,
    200,
    199,
    175,
    152,
    377,
    400,
    378,
    379,
    365,
    397,
    288,
]


def _layout() -> np.ndarray:
    adjacency = {i: set() for i in range(468)}
    for a, b in mp.solutions.face_mesh.FACEMESH_TESSELATION:
        adjacency[a].add(b)
        adjacency[b].add(a)
    matrix = np.zeros((468, 468))
    rhs = np.zeros((468, 2))
    for i in range(468):
        if i in FACE_OVAL:
            k = FACE_OVAL.index(i)
            angle = 2 * math.pi * k / len(FACE_OVAL) - math.pi / 2
            matrix[i, i] = 1
            rhs[i] = (math.cos(angle) * 0.8, math.sin(angle) * 1.05)
        else:
            neighbours = list(adjacency[i])
            matrix[i, i] = len(neighbours)
            for j in neighbours:
                matrix[i, j] -= 1
    return np.linalg.solve(matrix, rhs)


LAYOUT = _layout()


def live_face(
    scale: float = 170.0, rotation: float = 0.0, center=(640.0, 360.0), open_: float = 0.0
) -> np.ndarray:
    points = LAYOUT.copy()
    mid = points[UPPER_LIP + LOWER_LIP, 1].mean()
    points[UPPER_LIP, 1] = mid - 0.004 - open_ * 0.2
    points[LOWER_LIP, 1] = mid + 0.004 + open_ * 0.2
    points[JAW, 1] += open_
    c, s = math.cos(rotation), math.sin(rotation)
    rot = np.array([[c, -s], [s, c]])
    return (points @ rot.T * scale + np.asarray(center)).astype(np.float32)


def make_frame(width: int = 1280, height: int = 720, color=(90, 110, 130)) -> np.ndarray:
    frame = np.full((height, width, 3), color, np.uint8)
    yy, xx = np.mgrid[:height, :width]
    frame[..., 0] = np.clip(frame[..., 0] + (xx // 40 + yy // 40) % 2 * 12, 0, 255)
    return frame


class StubTracker:
    def __init__(self, *args, **kwargs) -> None:
        self.frame = 0
        self.mode = "orbit"

    def process(self, frame, scale=1.0):
        self.frame += 1
        if self.mode == "none":
            return None
        t = self.frame / 30.0
        open_ = 0.12 * (0.5 + 0.5 * math.sin(t * 4))
        return live_face(
            170 + 20 * math.sin(t),
            0.3 * math.sin(t * 0.7),
            (640 + 160 * math.sin(t * 0.5), 360 + 60 * math.cos(t * 0.6)),
            open_,
        )

    def held(self):
        return None

    def forget(self) -> None:
        pass

    def close(self) -> None:
        pass


class FakeCapture:
    def __init__(self) -> None:
        self._running = False
        self._seq = 0
        self.width = 1280
        self.height = 720
        self.fps = 30.0
        self.fail_open = False
        self._frame = make_frame()

    @property
    def is_open(self) -> bool:
        return self._running

    def open(self, index, width, height, fps) -> None:
        from visagecam.capture import CameraError

        if self.fail_open:
            raise CameraError("No se pudo abrir la camara")
        self._running = True
        self.width, self.height = width, height
        self._frame = make_frame(width, height)

    def read(self, last_seq, timeout=0.5):
        if not self._running:
            time.sleep(min(timeout, 0.05))
            return last_seq, None
        time.sleep(1 / 120)
        self._seq += 1
        return self._seq, self._frame.copy()

    def close(self) -> None:
        self._running = False
