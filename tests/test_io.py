import asyncio
import base64
import hashlib
import json
import threading
import time
import urllib.request

import pytest
import websockets

from synthetic import FakeCapture, StubTracker, make_frame
from visagecam.config import Settings
from visagecam.obs import ObsClient, ObsError
from visagecam.output import MjpegServer, VirtualCameraError, VirtualCameraOutput
from visagecam.processing import pipeline as pipeline_module
from visagecam.processing.engine import Engine

PASSWORD, SALT, CHALLENGE = "secreto", "salt123", "chal456"


def b64(value: str) -> str:
    return base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()


class MockObs:
    def __init__(self, port: int) -> None:
        self.port = port
        self.log: list[tuple[str, dict]] = []
        self.drop_on: str | None = None
        self.loop = asyncio.new_event_loop()
        self.ready = threading.Event()
        self.stop_event: asyncio.Event | None = None
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        assert self.ready.wait(5)

    async def handler(self, ws):
        await ws.send(json.dumps({"op": 0, "d": {"obsWebSocketVersion": "5.5.0", "rpcVersion": 1,
                                                   "authentication": {"challenge": CHALLENGE, "salt": SALT}}}))
        ident = json.loads(await ws.recv())
        if ident["d"].get("authentication") != b64(b64(PASSWORD + SALT) + CHALLENGE):
            await ws.close(4009)
            return
        await ws.send(json.dumps({"op": 2, "d": {"negotiatedRpcVersion": 1}}))
        async for raw in ws:
            message = json.loads(raw)["d"]
            kind, data = message["requestType"], message.get("requestData", {})
            self.log.append((kind, data))
            if kind == self.drop_on:
                await ws.close()
                return
            payload = {
                "GetSceneList": {"currentProgramSceneName": "Juego",
                                 "scenes": [{"sceneName": "Juego", "sceneIndex": 0}, {"sceneName": "Charla", "sceneIndex": 1}]},
                "GetSceneItemList": {"sceneItems": [{"sceneItemId": 3, "sourceName": "Chat", "sceneItemEnabled": True}]},
                "GetInputPropertiesListPropertyItems": {"propertyItems": []},
            }.get(kind, {})
            await ws.send(json.dumps({"op": 7, "d": {"requestType": kind, "requestId": message["requestId"],
                                                      "requestStatus": {"result": True, "code": 100}, "responseData": payload}}))

    def _run(self) -> None:
        asyncio.set_event_loop(self.loop)

        async def main() -> None:
            self.stop_event = asyncio.Event()
            async with websockets.serve(self.handler, "127.0.0.1", self.port):
                self.ready.set()
                await self.stop_event.wait()

        self.loop.run_until_complete(main())

    def close(self) -> None:
        self.loop.call_soon_threadsafe(self.stop_event.set)


@pytest.fixture()
def obs_server():
    server = MockObs(4477)
    yield server
    server.close()


def test_obs_full_flow(obs_server):
    client = ObsClient("127.0.0.1", 4477, PASSWORD)
    client.connect()
    assert client.connected
    scenes, current = client.list_scenes()
    assert scenes == ["Charla", "Juego"] and current == "Juego"
    client.set_scene("Charla")
    assert client.list_items("Juego")[0].name == "Chat"
    client.set_item_enabled("Juego", 3, False)
    label = client.add_camera_source("Juego", stream_url="http://127.0.0.1:8765/stream.mjpg")
    assert "flujo" in label
    created = [data for kind, data in obs_server.log if kind == "CreateInput"][0]
    assert created["inputKind"] == "ffmpeg_source"
    client.disconnect()
    assert not client.connected
    with pytest.raises(ObsError):
        client.list_scenes()


def test_obs_errors(obs_server):
    with pytest.raises(ObsError):
        ObsClient("127.0.0.1", 4477, "mal").connect()
    with pytest.raises(ObsError):
        ObsClient("127.0.0.1", 4477, "").connect()
    with pytest.raises(ObsError):
        ObsClient("127.0.0.1", 1, PASSWORD).connect(timeout=1)
    client = ObsClient("127.0.0.1", 4477, PASSWORD)
    client.connect()
    obs_server.drop_on = "GetSceneList"
    with pytest.raises(ObsError):
        client.list_scenes()
    client.disconnect()


def test_obs_concurrent_requests(obs_server):
    client = ObsClient("127.0.0.1", 4477, PASSWORD)
    client.connect()
    results, errors = [], []

    def worker():
        try:
            for _ in range(10):
                results.append(client.list_scenes()[1])
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    client.disconnect()
    assert not errors and len(results) == 60


def test_mjpeg_stream_serves_frames_and_multiple_clients():
    server = MjpegServer(8797)
    server.start()
    assert server.running
    counts = [0, 0]

    def client(index):
        response = urllib.request.urlopen(server.url, timeout=5)
        buffer = b""
        while counts[index] < 4:
            buffer += response.read(2048)
            while b"\xff\xd8" in buffer and b"\xff\xd9" in buffer:
                start = buffer.index(b"\xff\xd8")
                end = buffer.index(b"\xff\xd9", start) + 2
                counts[index] += 1
                buffer = buffer[end:]

    threads = [threading.Thread(target=client, args=(i,), daemon=True) for i in range(2)]
    [t.start() for t in threads]
    deadline = time.time() + 8
    while time.time() < deadline and min(counts) < 4:
        server.publish(make_frame())
        time.sleep(0.04)
    server.stop()
    assert min(counts) >= 4
    assert not server.running


def test_mjpeg_port_in_use_does_not_crash():
    first, second = MjpegServer(8796), MjpegServer(8796)
    first.start()
    second.start()
    assert first.running and second.running and first.port != second.port
    second.publish(make_frame())
    first.stop()
    second.stop()


def test_virtual_camera_lifecycle_and_errors():
    out = VirtualCameraOutput()
    out.send(make_frame())
    try:
        out.start(1280, 720, 30, "obs")
    except VirtualCameraError:
        pytest.skip("OBS Virtual Camera no disponible")
    out.send(make_frame())
    with pytest.raises(VirtualCameraError):
        out.send(make_frame(640, 480))
    out.stop()
    out.stop()
    assert not out.active
    with pytest.raises(VirtualCameraError):
        out.start(1280, 720, 30, "backend-que-no-existe")


@pytest.fixture()
def engine(library, monkeypatch, isolated_appdata):
    monkeypatch.setattr(pipeline_module, "FaceTracker", StubTracker)
    s = Settings()
    s.active_mask = "fox"
    s.stream_port = 8795
    eng = Engine(s, library)
    eng.capture = FakeCapture()
    yield eng
    eng.shutdown()


def test_engine_start_stop_cycles(engine):
    for _ in range(15):
        engine.start()
        time.sleep(0.05)
        engine.stop()
    engine.start()
    deadline = time.time() + 5
    while engine.latest()[1] is None and time.time() < deadline:
        time.sleep(0.05)
    frame_id, frame = engine.latest()
    assert frame is not None and frame.shape == (720, 1280, 3)
    assert engine.fps >= 0


def test_engine_camera_failure_and_recovery(engine):
    from visagecam.capture import CameraError

    engine.capture.fail_open = True
    with pytest.raises(CameraError):
        engine.start()
    assert not engine.running and engine.error
    engine.capture.fail_open = False
    engine.start()
    assert engine.running and not engine.error


def test_engine_virtual_output_toggle_under_load(engine):
    engine.start()
    time.sleep(0.3)
    try:
        for _ in range(3):
            engine.start_virtual()
            time.sleep(0.2)
            assert engine.virtual_active
            engine.stop_virtual()
            assert not engine.virtual_active
    except VirtualCameraError:
        pytest.skip("OBS Virtual Camera no disponible")
    engine.settings.active_mask = ""
    engine.settings.accessories = ["crown", "top_hat"]
    time.sleep(0.3)
    assert engine.running


def test_engine_survives_renderer_exceptions(engine, monkeypatch):
    engine.start()
    time.sleep(0.2)

    def boom(*args, **kwargs):
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr(engine._pipeline, "process", boom)
    time.sleep(0.4)
    assert engine.running
    assert engine.latest()[1] is not None
