import json
import logging
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from visagecam.masks.model import Anchor, Mask

log = logging.getLogger(__name__)

MAX_SIDE = 1280


def load_image_bgra(path: Path) -> np.ndarray:
    with Image.open(path) as source:
        source = ImageOps.exif_transpose(source)
        rgba = np.asarray(source.convert("RGBA"))
    bgra = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA)
    height, width = bgra.shape[:2]
    longest = max(height, width)
    if longest > MAX_SIDE:
        scale = MAX_SIDE / longest
        bgra = cv2.resize(
            bgra, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA
        )
    return np.ascontiguousarray(bgra)


def save_png(path: Path, bgra: np.ndarray) -> None:
    ok, encoded = cv2.imencode(".png", bgra)
    if not ok:
        raise OSError(f"No se pudo codificar {path.name}")
    encoded.tofile(str(path))


def write_mask(
    directory: Path,
    mask_id: str,
    name: str,
    bgra: np.ndarray,
    anchors: list[Anchor],
    face_landmarks: np.ndarray | None = None,
    kind: str = "mask",
    slot: str = "free",
    pivot: tuple[float, float] | None = None,
    width_ratio: float | None = None,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    save_png(directory / f"{mask_id}.png", bgra)
    payload: dict = {
        "name": name,
        "image": f"{mask_id}.png",
        "kind": kind,
        "slot": slot,
        "size": [int(bgra.shape[1]), int(bgra.shape[0])],
        "anchors": [
            {"name": a.name, "landmarks": list(a.landmarks), "point": [float(a.point[0]), float(a.point[1])]}
            for a in anchors
        ],
    }
    if pivot is not None:
        payload["pivot"] = [float(pivot[0]), float(pivot[1])]
    if width_ratio is not None:
        payload["width_ratio"] = float(width_ratio)
    if face_landmarks is not None:
        payload["face_landmarks"] = np.round(face_landmarks, 2).tolist()
    json_path = directory / f"{mask_id}.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return json_path


def read_mask(json_path: Path, builtin: bool) -> Mask:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    image = load_image_bgra(json_path.parent / payload["image"])
    anchors = [
        Anchor(a["name"], tuple(int(i) for i in a["landmarks"]), (float(a["point"][0]), float(a["point"][1])))
        for a in payload.get("anchors", [])
    ]
    landmarks = payload.get("face_landmarks")
    face = np.array(landmarks, dtype=np.float32) if landmarks else None
    if face is not None and face.shape != (468, 2):
        face = None
    return Mask(
        mask_id=json_path.stem,
        name=payload.get("name", json_path.stem),
        image=image,
        anchors=anchors,
        face_landmarks=face,
        builtin=builtin,
        kind=payload.get("kind", "mask"),
        slot=payload.get("slot", "free"),
        pivot=tuple(payload["pivot"]) if payload.get("pivot") else None,
        width_ratio=payload.get("width_ratio"),
    )
