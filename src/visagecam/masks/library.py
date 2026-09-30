import logging
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from visagecam.masks import generator
from visagecam.masks.cutout import remove_background
from visagecam.masks.model import Mask
from visagecam.masks.storage import load_image_bgra, read_mask, write_mask
from visagecam.processing.landmarks import detect_static_face

log = logging.getLogger(__name__)

SLOTS = ("head", "eyes", "mouth", "ears", "free")
MIN_SIDE = 24


class ImageError(ValueError):
    pass


@dataclass
class ImageAnalysis:
    name: str
    bgra: np.ndarray
    landmarks: np.ndarray | None
    has_alpha: bool
    cutout: np.ndarray | None

    @property
    def size(self) -> tuple[int, int]:
        return self.bgra.shape[1], self.bgra.shape[0]


def analyze_bgra(bgra: np.ndarray, name: str) -> ImageAnalysis:
    if bgra.ndim != 3 or bgra.shape[2] != 4:
        raise ImageError("Formato de imagen no soportado")
    if min(bgra.shape[:2]) < MIN_SIDE:
        raise ImageError("La imagen es demasiado pequena")
    bgr = np.ascontiguousarray(bgra[:, :, :3])
    has_alpha = bool((bgra[:, :, 3] < 250).any())
    landmarks = None
    try:
        landmarks = detect_static_face(bgr)
    except Exception:
        log.exception("Fallo la deteccion facial de %s", name)
    cutout = None
    if not has_alpha and landmarks is None:
        try:
            cutout = remove_background(bgr)
        except Exception:
            log.exception("Fallo el recorte de fondo de %s", name)
    return ImageAnalysis(name, bgra, landmarks, has_alpha, cutout)


def analyze_file(path: Path) -> ImageAnalysis:
    try:
        bgra = load_image_bgra(Path(path))
    except Exception as exc:
        raise ImageError("No se pudo leer la imagen. Usa PNG, JPG, WEBP, BMP o TIFF validos.") from exc
    return analyze_bgra(bgra, Path(path).stem)


class MaskLibrary:
    def __init__(self, root: Path) -> None:
        self.dirs = {
            ("mask", True): root / "builtin",
            ("mask", False): root / "custom",
            ("accessory", True): root.parent / "accessories" / "builtin",
            ("accessory", False): root.parent / "accessories" / "custom",
        }
        self._items: dict[str, Mask] = {}

    def load(self) -> None:
        generator.ensure_masks(self.dirs[("mask", True)])
        generator.ensure_accessories(self.dirs[("accessory", True)])
        self._items.clear()
        for (kind, builtin), directory in self.dirs.items():
            directory.mkdir(parents=True, exist_ok=True)
            for json_path in sorted(directory.glob("*.json")):
                try:
                    item = read_mask(json_path, builtin)
                except Exception:
                    log.exception("No se pudo cargar %s", json_path.name)
                    continue
                item.kind = kind
                self._items[item.mask_id] = item
        log.info("%d elementos cargados", len(self._items))

    def _listing(self, kind: str, order: list[str]) -> list[Mask]:
        pool = [m for m in list(self._items.values()) if m.kind == kind]
        rank = {mask_id: i for i, mask_id in enumerate(order)}
        builtin = sorted((m for m in pool if m.builtin), key=lambda m: rank.get(m.mask_id, len(rank)))
        return builtin + [m for m in pool if not m.builtin]

    def all(self) -> list[Mask]:
        return self._listing("mask", generator.MASK_ORDER)

    def accessories(self) -> list[Mask]:
        return self._listing("accessory", generator.ACCESSORY_ORDER)

    def get(self, mask_id: str) -> Mask | None:
        return self._items.get(mask_id)

    def add(
        self,
        analysis: ImageAnalysis,
        kind: str = "mask",
        slot: str = "free",
        name: str | None = None,
        use_cutout: bool = True,
        face_warp: bool = True,
    ) -> Mask:
        if kind not in ("mask", "accessory"):
            raise ImageError("Tipo no valido")
        if slot not in SLOTS:
            slot = "free"
        bgra = analysis.bgra.copy()
        if use_cutout and analysis.cutout is not None and not analysis.has_alpha:
            bgra[:, :, 3] = analysis.cutout
        landmarks = analysis.landmarks if (kind == "mask" and face_warp) else None
        label = (name or analysis.name or "Imagen").strip()[:40] or "Imagen"
        slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "imagen"
        prefix = "custom" if kind == "mask" else "acc"
        mask_id = f"{prefix}-{slug}-{int(time.time() * 1000) % 10**10}"
        directory = self.dirs[(kind, False)]
        write_mask(directory, mask_id, label, bgra, [], landmarks, kind=kind, slot=slot if kind == "accessory" else "free")
        item = read_mask(directory / f"{mask_id}.json", False)
        item.kind = kind
        self._items[item.mask_id] = item
        log.info("Imagen anadida como %s (%s, %s)", mask_id, kind, slot)
        return item

    def import_image(self, path: Path, kind: str = "mask", slot: str = "free") -> Mask:
        analysis = analyze_file(Path(path))
        return self.add(analysis, kind, slot, analysis.name)

    def remove(self, mask_id: str) -> bool:
        item = self._items.get(mask_id)
        if item is None or item.builtin:
            return False
        directory = self.dirs[(item.kind, False)]
        for suffix in (".json", ".png"):
            try:
                (directory / f"{mask_id}{suffix}").unlink()
            except FileNotFoundError:
                pass
        del self._items[mask_id]
        return True

    def export(self, mask_id: str, target: Path) -> None:
        item = self._items[mask_id]
        source = self.dirs[(item.kind, item.builtin)]
        for suffix in (".json", ".png"):
            shutil.copy2(source / f"{mask_id}{suffix}", target / f"{mask_id}{suffix}")
