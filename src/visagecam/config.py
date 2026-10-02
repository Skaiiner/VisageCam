# Copyright (c) 2026 Skain. Todos los derechos reservados.

import json
import logging
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

log = logging.getLogger(__name__)


def data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    path = Path(base) / "VisageCam"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _load_dict_into(instance, raw: dict, skip: tuple[str, ...] = ()) -> None:
    if not isinstance(raw, dict):
        return
    known = {f.name for f in fields(instance)}
    for key, value in raw.items():
        if key in skip or key not in known:
            continue
        current = getattr(instance, key)
        try:
            setattr(instance, key, type(current)(value))
        except (TypeError, ValueError):
            log.warning("Valor invalido para %s: %r", key, value)


PROFILE_RANGES = (
    ("mask_scale", 0.2, 3.0),
    ("mask_rotation", -180.0, 180.0),
    ("mask_offset_x", -1.0, 1.0),
    ("mask_offset_y", -1.0, 1.0),
    ("mask_opacity", 0.0, 1.0),
    ("color_match", 0.0, 1.0),
    ("light_match", 0.0, 1.0),
    ("edge_softness", 0.0, 1.0),
    ("beauty_smooth", 0.0, 1.0),
    ("beauty_bright", 0.0, 1.0),
    ("beauty_lips", 0.0, 1.0),
    ("beauty_teeth", 0.0, 1.0),
    ("distortion_strength", 0.3, 2.0),
)


@dataclass
class FilterProfile:
    active_mask: str = ""
    mask_scale: float = 1.0
    mask_rotation: float = 0.0
    mask_offset_x: float = 0.0
    mask_offset_y: float = 0.0
    mask_opacity: float = 1.0
    color_match: float = 0.85
    light_match: float = 0.6
    edge_softness: float = 0.3
    keep_eyes_mouth: bool = True
    face_warp: bool = True
    expression: bool = True

    distortion: str = ""
    distortion_strength: float = 1.0

    beauty_smooth: float = 0.0
    beauty_bright: float = 0.0
    beauty_lips: float = 0.0
    beauty_teeth: float = 0.0

    accessories: list = field(default_factory=list)
    accessory_adjust: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict) -> "FilterProfile":
        profile = cls()
        _load_dict_into(profile, raw if isinstance(raw, dict) else {})
        profile.sanitize()
        return profile

    def sanitize(self) -> None:
        for key, low, high in PROFILE_RANGES:
            setattr(self, key, _clamp(getattr(self, key), low, high))
        if not isinstance(self.active_mask, str):
            self.active_mask = ""
        if not isinstance(self.distortion, str):
            self.distortion = ""
        self.accessories = [str(a) for a in self.accessories if isinstance(a, str)]
        cleaned = {}
        for key, value in self.accessory_adjust.items():
            try:
                values = [float(v) for v in value]
            except (TypeError, ValueError):
                continue
            if len(values) == 4:
                cleaned[str(key)] = values
        self.accessory_adjust = cleaned


@dataclass
class Settings:
    camera_index: int = 0
    width: int = 1280
    height: int = 720
    fps: int = 30
    mirror: bool = False
    mirror_mode: str = "off"
    hq_capture: bool = True
    enhance: float = 0.5
    expression: bool = True
    virtual_backend: str = "auto"
    stream_port: int = 8765

    active_mask: str = ""
    mask_scale: float = 1.0
    mask_rotation: float = 0.0
    mask_offset_x: float = 0.0
    mask_offset_y: float = 0.0
    mask_opacity: float = 1.0
    color_match: float = 0.85
    light_match: float = 0.6
    edge_softness: float = 0.3
    keep_eyes_mouth: bool = True
    face_warp: bool = True

    distortion: str = ""
    distortion_strength: float = 1.0

    beauty_smooth: float = 0.0
    beauty_bright: float = 0.0
    beauty_lips: float = 0.0
    beauty_teeth: float = 0.0

    accessories: list = field(default_factory=list)
    accessory_adjust: dict = field(default_factory=dict)

    dual_faces: bool = False
    person2: FilterProfile = field(default_factory=FilterProfile)

    background_mode: str = "none"
    background_image: str = ""
    blur_strength: int = 40

    obs_host: str = "localhost"
    obs_port: int = 4455
    obs_password: str = ""

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        path = path or data_dir() / "config.json"
        settings = cls()
        if not path.exists():
            return settings
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            log.exception("No se pudo leer %s", path)
            return settings
        if not isinstance(raw, dict):
            return settings
        _load_dict_into(settings, raw, skip=("person2",))
        if isinstance(raw.get("person2"), dict):
            settings.person2 = FilterProfile.from_dict(raw["person2"])
        settings.sanitize()
        return settings

    def primary_profile(self) -> FilterProfile:
        return FilterProfile(
            active_mask=self.active_mask,
            mask_scale=self.mask_scale,
            mask_rotation=self.mask_rotation,
            mask_offset_x=self.mask_offset_x,
            mask_offset_y=self.mask_offset_y,
            mask_opacity=self.mask_opacity,
            color_match=self.color_match,
            light_match=self.light_match,
            edge_softness=self.edge_softness,
            keep_eyes_mouth=self.keep_eyes_mouth,
            face_warp=self.face_warp,
            expression=self.expression,
            distortion=self.distortion,
            distortion_strength=self.distortion_strength,
            beauty_smooth=self.beauty_smooth,
            beauty_bright=self.beauty_bright,
            beauty_lips=self.beauty_lips,
            beauty_teeth=self.beauty_teeth,
            accessories=list(self.accessories),
            accessory_adjust=dict(self.accessory_adjust),
        )

    def sanitize(self) -> None:
        for key, low, high in PROFILE_RANGES:
            setattr(self, key, _clamp(getattr(self, key), low, high))
        self.enhance = _clamp(self.enhance, 0.0, 1.0)
        self.blur_strength = int(_clamp(self.blur_strength, 5, 100))
        self.fps = int(_clamp(self.fps, 15, 60))
        self.obs_port = int(_clamp(self.obs_port, 1, 65535))
        self.stream_port = int(_clamp(self.stream_port, 1024, 65535))
        self.camera_index = max(0, int(self.camera_index))
        if (self.width, self.height) not in ((640, 480), (960, 540), (1280, 720), (1920, 1080)):
            self.width, self.height = 1280, 720
        if self.mirror and self.mirror_mode == "off":
            self.mirror_mode = "both"
        self.mirror = False
        if self.mirror_mode not in ("off", "preview", "both"):
            self.mirror_mode = "off"
        if self.background_mode not in ("none", "blur", "image"):
            self.background_mode = "none"
        if self.virtual_backend not in ("auto", "unitycapture", "obs"):
            self.virtual_backend = "auto"
        if not isinstance(self.distortion, str):
            self.distortion = ""
        self.accessories = [str(a) for a in self.accessories if isinstance(a, str)]
        cleaned = {}
        for key, value in self.accessory_adjust.items():
            try:
                values = [float(v) for v in value]
            except (TypeError, ValueError):
                continue
            if len(values) == 4:
                cleaned[str(key)] = values
        self.accessory_adjust = cleaned
        if not isinstance(self.person2, FilterProfile):
            self.person2 = FilterProfile.from_dict(self.person2 if isinstance(self.person2, dict) else {})
        else:
            self.person2.sanitize()
        self.dual_faces = bool(self.dual_faces)

    def save(self, path: Path | None = None) -> None:
        path = path or data_dir() / "config.json"
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, path)
        except OSError:
            log.exception("No se pudo guardar %s", path)
