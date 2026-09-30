import json
import logging
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

log = logging.getLogger(__name__)


def data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    path = Path(base) / "VisageCam"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class Settings:
    camera_index: int = 0
    width: int = 1280
    height: int = 720
    fps: int = 30
    mirror: bool = False
    virtual_backend: str = "auto"

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
        known = {f.name: f.type for f in fields(cls)}
        for key, value in raw.items():
            if key in known:
                try:
                    setattr(settings, key, type(getattr(settings, key))(value))
                except (TypeError, ValueError):
                    log.warning("Valor invalido para %s: %r", key, value)
        return settings

    def save(self, path: Path | None = None) -> None:
        path = path or data_dir() / "config.json"
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, path)
        except OSError:
            log.exception("No se pudo guardar %s", path)
