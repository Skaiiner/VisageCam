import logging

import numpy as np
import pyvirtualcam

log = logging.getLogger(__name__)


class VirtualCameraError(RuntimeError):
    pass


class VirtualCameraOutput:
    def __init__(self) -> None:
        self._cam: pyvirtualcam.Camera | None = None
        self.width = 0
        self.height = 0
        self.device = ""

    @property
    def active(self) -> bool:
        return self._cam is not None

    def start(self, width: int, height: int, fps: int) -> None:
        self.stop()
        try:
            cam = pyvirtualcam.Camera(
                width=width,
                height=height,
                fps=fps,
                fmt=pyvirtualcam.PixelFormat.BGR,
                backend="obs",
            )
        except Exception as exc:
            raise VirtualCameraError(
                "No se pudo iniciar la camara virtual. Instala OBS Studio y abre su "
                "camara virtual al menos una vez para registrar el dispositivo."
                f" Detalle: {exc}"
            ) from exc
        self._cam = cam
        self.width = width
        self.height = height
        self.device = cam.device
        log.info("Camara virtual activa: %s (%dx%d @ %d)", cam.device, width, height, fps)

    def send(self, frame: np.ndarray) -> None:
        cam = self._cam
        if cam is None:
            return
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            raise VirtualCameraError("El tamano del fotograma no coincide con la camara virtual")
        cam.send(frame)

    def stop(self) -> None:
        cam, self._cam = self._cam, None
        if cam is not None:
            try:
                cam.close()
            except Exception:
                log.exception("Error al cerrar la camara virtual")
            log.info("Camara virtual detenida")
