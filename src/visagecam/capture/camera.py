# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

import logging
import threading
import time
from dataclasses import dataclass

import cv2
import numpy as np

log = logging.getLogger(__name__)

RESOLUTIONS = [(640, 480), (960, 540), (1280, 720), (1920, 1080)]
EXCLUDED_NAMES = ("obs virtual camera", "obs-camera", "visagecam")


class CameraError(RuntimeError):
    pass


@dataclass(frozen=True)
class CameraDevice:
    index: int
    name: str


def _dshow_names() -> list[str]:
    try:
        from pygrabber.dshow_graph import FilterGraph

        return list(FilterGraph().get_input_devices())
    except Exception:
        log.debug("pygrabber no disponible", exc_info=True)
        return []


def list_cameras(max_probe: int = 6) -> list[CameraDevice]:
    names = _dshow_names()
    if names:
        return [
            CameraDevice(i, name)
            for i, name in enumerate(names)
            if not any(token in name.lower() for token in EXCLUDED_NAMES)
        ]
    devices = []
    for index in range(max_probe):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        try:
            if cap.isOpened():
                devices.append(CameraDevice(index, f"Camara {index}"))
        finally:
            cap.release()
    return devices


class CameraCapture:
    def __init__(self) -> None:
        self._cap: cv2.VideoCapture | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._cond = threading.Condition()
        self._frame: np.ndarray | None = None
        self._seq = 0
        self.width = 0
        self.height = 0
        self.fps = 0.0

    @property
    def is_open(self) -> bool:
        return self._running

    def open(self, index: int, width: int, height: int, fps: int) -> None:
        self.close()
        cap = None
        frame = None
        for backend in (cv2.CAP_MSMF, cv2.CAP_DSHOW):
            candidate = cv2.VideoCapture(index, backend)
            if not candidate.isOpened():
                candidate.release()
                continue
            candidate.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            candidate.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            candidate.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            candidate.set(cv2.CAP_PROP_FPS, fps)
            candidate.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            ok, first = candidate.read()
            if ok and first is not None:
                cap, frame = candidate, first
                log.info("Captura con el backend %s", candidate.getBackendName())
                break
            candidate.release()
        if cap is None or frame is None:
            raise CameraError(f"No se pudo abrir la camara {index}")
        self.height, self.width = frame.shape[:2]
        self.fps = cap.get(cv2.CAP_PROP_FPS) or float(fps)
        log.info("Camara %d abierta a %dx%d @ %.1f fps", index, self.width, self.height, self.fps)
        self._cap = cap
        self._running = True
        with self._cond:
            self._frame = frame
            self._seq += 1
        self._thread = threading.Thread(target=self._loop, name="camera-capture", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        failures = 0
        while self._running and self._cap is not None:
            ok, frame = self._cap.read()
            if not ok or frame is None:
                failures += 1
                if failures > 100:
                    log.error("La camara dejo de entregar imagen")
                    break
                time.sleep(0.01)
                continue
            failures = 0
            with self._cond:
                self._frame = frame
                self._seq += 1
                self._cond.notify_all()
        self._running = False
        with self._cond:
            self._cond.notify_all()

    def read(self, last_seq: int, timeout: float = 0.5) -> tuple[int, np.ndarray | None]:
        with self._cond:
            self._cond.wait_for(lambda: self._seq != last_seq or not self._running, timeout)
            if self._seq == last_seq:
                return last_seq, None
            return self._seq, self._frame

    def close(self) -> None:
        self._running = False
        thread, self._thread = self._thread, None
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        with self._cond:
            self._frame = None
            self._cond.notify_all()
