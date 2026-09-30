import logging
import threading
import time

import cv2
import numpy as np

from visagecam.capture import CameraCapture, CameraError
from visagecam.config import Settings
from visagecam.masks.library import MaskLibrary
from visagecam.output import MjpegServer, VirtualCameraError, VirtualCameraOutput
from visagecam.processing.pipeline import FramePipeline

log = logging.getLogger(__name__)


class Engine:
    def __init__(self, settings: Settings, library: MaskLibrary) -> None:
        self.settings = settings
        self.capture = CameraCapture()
        self.output = VirtualCameraOutput()
        self.stream = MjpegServer(settings.stream_port)
        self._pipeline = FramePipeline(settings, library)
        self._thread: threading.Thread | None = None
        self._running = False
        self._lock = threading.Lock()
        self._lifecycle = threading.RLock()
        self._latest: np.ndarray | None = None
        self._frame_id = 0
        self._out_cond = threading.Condition()
        self._out_frame: np.ndarray | None = None
        self._out_seq = 0
        self._out_thread: threading.Thread | None = None
        self.fps = 0.0
        self.process_ms = 0.0
        self.error = ""
        self.target = (settings.width, settings.height)

    @property
    def running(self) -> bool:
        return self._running

    @property
    def virtual_active(self) -> bool:
        return self.output.active

    @property
    def face_found(self) -> bool:
        return self._pipeline.face_found

    def start(self) -> None:
        with self._lifecycle:
            self._start()

    def _start(self) -> None:
        self.stop()
        s = self.settings
        self.error = ""
        try:
            cap_w, cap_h = (1920, 1080) if s.hq_capture and s.height <= 720 else (s.width, s.height)
            self.capture.open(s.camera_index, cap_w, cap_h, s.fps)
        except CameraError as exc:
            self.error = str(exc)
            raise
        self.target = (s.width, s.height)
        self.stream.start()
        self._running = True
        self._out_thread = threading.Thread(target=self._output_loop, name="engine-output", daemon=True)
        self._out_thread.start()
        self._thread = threading.Thread(target=self._loop, name="engine", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        with self._lifecycle:
            self._stop()

    def _stop(self) -> None:
        self._running = False
        thread, self._thread = self._thread, None
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=3.0)
        with self._out_cond:
            self._out_cond.notify_all()
        out_thread, self._out_thread = self._out_thread, None
        if out_thread is not None and out_thread is not threading.current_thread():
            out_thread.join(timeout=3.0)
        self.capture.close()
        self.output.stop()
        self.stream.stop()
        with self._lock:
            self._latest = None

    def shutdown(self) -> None:
        self.stop()
        self._pipeline.close()

    def recalibrate(self) -> None:
        self._pipeline.recalibrate()

    @property
    def calibration(self) -> tuple[bool, float]:
        neutral = self._pipeline.neutral
        return neutral.ready, neutral.progress

    def start_virtual(self) -> None:
        width, height = self.target
        self.output.start(width, height, self.settings.fps, self.settings.virtual_backend)

    def stop_virtual(self) -> None:
        self.output.stop()

    def latest(self) -> tuple[int, np.ndarray | None]:
        with self._lock:
            return self._frame_id, self._latest

    def _output_loop(self) -> None:
        seq = 0
        while self._running:
            with self._out_cond:
                self._out_cond.wait_for(lambda: self._out_seq != seq or not self._running, 0.5)
                if self._out_seq == seq or not self._running:
                    continue
                seq, frame = self._out_seq, self._out_frame
            if frame is None:
                continue
            if self.output.active:
                try:
                    self.output.send(frame)
                except VirtualCameraError as exc:
                    self.error = str(exc)
                    self.output.stop()
                except Exception as exc:
                    log.exception("Error enviando a la camara virtual")
                    self.error = f"Camara virtual: {exc}"
                    self.output.stop()
            self.stream.publish(frame)

    def _loop(self) -> None:
        seq = 0
        counter = 0
        window = time.perf_counter()
        width, height = self.target
        while self._running and self.capture.is_open:
            seq, frame = self.capture.read(seq)
            if frame is None:
                continue
            started = time.perf_counter()
            if frame.shape[1] != width or frame.shape[0] != height:
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
            try:
                result = self._pipeline.process(frame)
            except Exception:
                log.exception("Error procesando el fotograma")
                result = frame
            self.process_ms = 0.9 * self.process_ms + 0.1 * (time.perf_counter() - started) * 1000.0
            with self._out_cond:
                self._out_frame = result
                self._out_seq += 1
                self._out_cond.notify_all()
            with self._lock:
                self._latest = result
                self._frame_id += 1
            counter += 1
            now = time.perf_counter()
            if now - window >= 1.0:
                self.fps = counter / (now - window)
                counter = 0
                window = now
        if self._running:
            self.error = "La camara dejo de responder"
        self._running = False
