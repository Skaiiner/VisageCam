import logging
import re
import shutil
import time
from pathlib import Path

import numpy as np

from visagecam.masks import generator
from visagecam.masks.cutout import remove_background
from visagecam.masks.model import Mask
from visagecam.masks.storage import load_image_bgra, read_mask, write_mask
from visagecam.processing.landmarks import detect_static_face

log = logging.getLogger(__name__)

SLOTS = ("head", "eyes", "mouth", "ears", "free")


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
        pool = [m for m in self._items.values() if m.kind == kind]
        rank = {mask_id: i for i, mask_id in enumerate(order)}
        builtin = sorted((m for m in pool if m.builtin), key=lambda m: rank.get(m.mask_id, len(rank)))
        return builtin + [m for m in pool if not m.builtin]

    def all(self) -> list[Mask]:
        return self._listing("mask", generator.MASK_ORDER)

    def accessories(self) -> list[Mask]:
        return self._listing("accessory", generator.ACCESSORY_ORDER)

    def get(self, mask_id: str) -> Mask | None:
        return self._items.get(mask_id)

    def import_image(self, path: Path, kind: str = "mask", slot: str = "free") -> Mask:
        bgra = load_image_bgra(path)
        bgr = np.ascontiguousarray(bgra[:, :, :3])
        landmarks = detect_static_face(bgr) if kind == "mask" else None
        if landmarks is None and not bool((bgra[:, :, 3] < 250).any()):
            alpha = remove_background(bgr)
            if alpha is not None:
                bgra[:, :, 3] = alpha
                log.info("Fondo eliminado automaticamente de %s", path.name)
        slug = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-") or "imagen"
        prefix = "custom" if kind == "mask" else "acc"
        mask_id = f"{prefix}-{slug}-{int(time.time())}"
        directory = self.dirs[(kind, False)]
        write_mask(directory, mask_id, path.stem, bgra, [], landmarks, kind=kind, slot=slot)
        item = read_mask(directory / f"{mask_id}.json", False)
        item.kind = kind
        self._items[item.mask_id] = item
        log.info("Imagen importada como %s (%s)", mask_id, kind)
        return item

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
