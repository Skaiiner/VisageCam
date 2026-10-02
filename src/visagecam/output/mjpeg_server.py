# Copyright (c) 2026 Skain. Todos los derechos reservados.

import logging
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import numpy as np

log = logging.getLogger(__name__)

BOUNDARY = "visagecamframe"
STREAM_PATH = "/stream.mjpg"


class _Server(ThreadingHTTPServer):
    allow_reuse_address = False
    daemon_threads = True

    def server_bind(self) -> None:
        if sys.platform == "win32":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class MjpegServer:
    def __init__(self, port: int = 8765, quality: int = 92) -> None:
        self.port = port
        self.quality = quality
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._cond = threading.Condition()
        self._jpeg = b""
        self._seq = 0
        self._clients = 0
        self._stopping = False

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}{STREAM_PATH}"

    @property
    def running(self) -> bool:
        return self._server is not None

    @property
    def has_clients(self) -> bool:
        return self._clients > 0

    def start(self) -> None:
        if self._server is not None:
            return
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args) -> None:
                return

            def do_GET(self) -> None:
                if self.path.split("?")[0] != STREAM_PATH:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY}")
                self.send_header("Cache-Control", "no-cache, no-store")
                self.send_header("Connection", "close")
                self.end_headers()
                owner._serve(self.wfile)

        server = None
        first = self.port
        for candidate in range(first, first + 10):
            try:
                server = _Server(("127.0.0.1", candidate), Handler)
                self.port = candidate
                break
            except OSError as exc:
                log.warning("Puerto %d ocupado para el flujo MJPEG: %s", candidate, exc)
        if server is None:
            self.port = first
            return
        self._stopping = False
        self._server = server
        self._thread = threading.Thread(target=server.serve_forever, name="mjpeg-server", daemon=True)
        self._thread.start()
        log.info("Flujo MJPEG disponible en %s", self.url)

    def _serve(self, out) -> None:
        with self._cond:
            self._clients += 1
            seq = self._seq
        try:
            while not self._stopping:
                with self._cond:
                    self._cond.wait_for(lambda: self._seq != seq or self._stopping, 2.0)
                    if self._seq == seq:
                        continue
                    seq, data = self._seq, self._jpeg
                out.write(
                    f"--{BOUNDARY}\r\nContent-Type: image/jpeg\r\nContent-Length: {len(data)}\r\n\r\n".encode()
                    + data
                    + b"\r\n"
                )
                out.flush()
        except (BrokenPipeError, ConnectionError, OSError):
            pass
        finally:
            with self._cond:
                self._clients -= 1

    def publish(self, frame: np.ndarray) -> None:
        if self._server is None or self._clients <= 0:
            return
        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
        if not ok:
            return
        with self._cond:
            self._jpeg = encoded.tobytes()
            self._seq += 1
            self._cond.notify_all()

    def stop(self) -> None:
        server, self._server = self._server, None
        self._stopping = True
        with self._cond:
            self._cond.notify_all()
        if server is not None:
            server.shutdown()
            server.server_close()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=2.0)
