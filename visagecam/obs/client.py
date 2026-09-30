import base64
import hashlib
import itertools
import json
import logging
import threading
from dataclasses import dataclass
from typing import Any

import websocket

log = logging.getLogger(__name__)

RPC_VERSION = 1
OP_HELLO = 0
OP_IDENTIFY = 1
OP_IDENTIFIED = 2
OP_REQUEST = 6
OP_REQUEST_RESPONSE = 7


class ObsError(RuntimeError):
    pass


@dataclass(frozen=True)
class SceneItem:
    item_id: int
    name: str
    enabled: bool


def _sha256_b64(value: str) -> str:
    return base64.b64encode(hashlib.sha256(value.encode("utf-8")).digest()).decode("ascii")


def build_auth(password: str, salt: str, challenge: str) -> str:
    return _sha256_b64(_sha256_b64(password + salt) + challenge)


class ObsClient:
    def __init__(self, host: str = "localhost", port: int = 4455, password: str = "") -> None:
        self.host = host
        self.port = port
        self.password = password
        self._ws: websocket.WebSocket | None = None
        self._reader: threading.Thread | None = None
        self._stop = threading.Event()
        self._send_lock = threading.Lock()
        self._pending: dict[str, tuple[threading.Event, dict]] = {}
        self._pending_lock = threading.Lock()
        self._ids = itertools.count(1)
        self.obs_version = ""

    @property
    def connected(self) -> bool:
        return self._ws is not None and self._reader is not None and self._reader.is_alive()

    def connect(self, timeout: float = 5.0) -> None:
        self.disconnect()
        url = f"ws://{self.host}:{self.port}"
        try:
            ws = websocket.create_connection(url, timeout=timeout)
        except Exception as exc:
            raise ObsError(f"No se pudo conectar con OBS en {url}: {exc}") from exc
        try:
            hello = self._recv_json(ws)
            if hello.get("op") != OP_HELLO:
                raise ObsError("Respuesta inesperada del servidor de OBS")
            data = hello["d"]
            identify: dict[str, Any] = {"rpcVersion": RPC_VERSION, "eventSubscriptions": 0}
            auth = data.get("authentication")
            if auth:
                if not self.password:
                    raise ObsError("OBS requiere contrasena")
                identify["authentication"] = build_auth(
                    self.password, auth["salt"], auth["challenge"]
                )
            ws.send(json.dumps({"op": OP_IDENTIFY, "d": identify}))
            reply = self._recv_json(ws)
            if reply.get("op") != OP_IDENTIFIED:
                raise ObsError("OBS rechazo la identificacion")
            self.obs_version = str(data.get("obsWebSocketVersion", ""))
        except ObsError:
            ws.close()
            raise
        except Exception as exc:
            ws.close()
            raise ObsError(f"Fallo el saludo con OBS: {exc}") from exc
        ws.settimeout(1.0)
        self._ws = ws
        self._stop.clear()
        self._reader = threading.Thread(target=self._read_loop, name="obs-reader", daemon=True)
        self._reader.start()
        log.info("Conectado a OBS WebSocket %s", self.obs_version)

    @staticmethod
    def _recv_json(ws: websocket.WebSocket) -> dict:
        try:
            return json.loads(ws.recv())
        except websocket.WebSocketException as exc:
            raise ObsError(f"Conexion con OBS interrumpida: {exc}") from exc
        except (ValueError, TypeError) as exc:
            raise ObsError("Mensaje invalido de OBS") from exc

    def _read_loop(self) -> None:
        ws = self._ws
        while not self._stop.is_set() and ws is not None:
            try:
                raw = ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            except Exception:
                break
            if not raw:
                break
            try:
                message = json.loads(raw)
            except ValueError:
                continue
            if message.get("op") == OP_REQUEST_RESPONSE:
                data = message["d"]
                with self._pending_lock:
                    entry = self._pending.pop(data.get("requestId", ""), None)
                if entry is not None:
                    entry[1].update(data)
                    entry[0].set()
        with self._pending_lock:
            waiting = list(self._pending.values())
            self._pending.clear()
        for event, holder in waiting:
            holder["aborted"] = True
            event.set()
        log.info("Lector de OBS finalizado")

    def disconnect(self) -> None:
        self._stop.set()
        ws, self._ws = self._ws, None
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass
        reader, self._reader = self._reader, None
        if reader is not None and reader is not threading.current_thread():
            reader.join(timeout=2.0)

    def request(self, request_type: str, data: dict | None = None, timeout: float = 5.0) -> dict:
        ws = self._ws
        if ws is None or not self.connected:
            raise ObsError("No hay conexion con OBS")
        request_id = f"{request_type}-{next(self._ids)}"
        event = threading.Event()
        holder: dict = {}
        with self._pending_lock:
            self._pending[request_id] = (event, holder)
        payload: dict[str, Any] = {"requestType": request_type, "requestId": request_id}
        if data:
            payload["requestData"] = data
        try:
            with self._send_lock:
                ws.send(json.dumps({"op": OP_REQUEST, "d": payload}))
        except Exception as exc:
            with self._pending_lock:
                self._pending.pop(request_id, None)
            raise ObsError(f"No se pudo enviar la peticion a OBS: {exc}") from exc
        if not event.wait(timeout):
            with self._pending_lock:
                self._pending.pop(request_id, None)
            raise ObsError(f"OBS no respondio a {request_type}")
        if holder.get("aborted"):
            raise ObsError("Se perdio la conexion con OBS")
        status = holder.get("requestStatus", {})
        if not status.get("result"):
            raise ObsError(status.get("comment") or f"OBS devolvio el codigo {status.get('code')}")
        return holder.get("responseData") or {}

    def list_scenes(self) -> tuple[list[str], str]:
        data = self.request("GetSceneList")
        scenes = [s["sceneName"] for s in sorted(data["scenes"], key=lambda s: -s["sceneIndex"])]
        return scenes, data.get("currentProgramSceneName", "")

    def set_scene(self, name: str) -> None:
        self.request("SetCurrentProgramScene", {"sceneName": name})

    def list_items(self, scene: str) -> list[SceneItem]:
        data = self.request("GetSceneItemList", {"sceneName": scene})
        return [
            SceneItem(i["sceneItemId"], i["sourceName"], bool(i["sceneItemEnabled"]))
            for i in data["sceneItems"]
        ]

    def add_camera_source(self, scene: str, source_name: str = "VisageCam",
                          tokens: tuple[str, ...] = ("unity video capture", "visagecam")) -> str:
        data = self.request(
            "GetInputPropertiesListPropertyItems",
            {"inputKind": "dshow_input", "propertyName": "video_device_id"},
        )
        device = next(
            (i for i in data.get("propertyItems", []) if any(t in i["itemName"].lower() for t in tokens)),
            None,
        )
        if device is None:
            raise ObsError("OBS no ve el dispositivo de VisageCam. Instala Unity Capture y reinicia OBS.")
        try:
            self.request(
                "CreateInput",
                {
                    "sceneName": scene,
                    "inputName": source_name,
                    "inputKind": "dshow_input",
                    "inputSettings": {"video_device_id": device["itemValue"]},
                    "sceneItemEnabled": True,
                },
            )
        except ObsError:
            self.request("CreateSceneItem", {"sceneName": scene, "sourceName": source_name})
        return device["itemName"]

    def set_item_enabled(self, scene: str, item_id: int, enabled: bool) -> None:
        self.request(
            "SetSceneItemEnabled",
            {"sceneName": scene, "sceneItemId": item_id, "sceneItemEnabled": enabled},
        )
