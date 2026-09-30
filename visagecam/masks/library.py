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


class MaskLibrary:
    def __init__(self, root: Path) -> None:
        self.builtin_dir = root / "builtin"
        self.custom_dir = root / "custom"
        self._masks: dict[str, Mask] = {}

    def load(self) -> None:
        generator.ensure_masks(self.builtin_dir)
        self.custom_dir.mkdir(parents=True, exist_ok=True)
        self._masks.clear()
        for directory, builtin in ((self.builtin_dir, True), (self.custom_dir, False)):
            for json_path in sorted(directory.glob("*.json")):
                try:
                    mask = read_mask(json_path, builtin)
                except Exception:
                    log.exception("No se pudo cargar la mascara %s", json_path.name)
                    continue
                self._masks[mask.mask_id] = mask
        log.info("%d mascaras cargadas", len(self._masks))

    def all(self) -> list[Mask]:
        builtin = [m for m in self._masks.values() if m.builtin]
        custom = [m for m in self._masks.values() if not m.builtin]
        order = {mask_id: i for i, mask_id in enumerate(generator.MASK_ORDER)}
        builtin.sort(key=lambda m: order.get(m.mask_id, len(order)))
        return builtin + custom

    def get(self, mask_id: str) -> Mask | None:
        return self._masks.get(mask_id)

    def import_image(self, path: Path) -> Mask:
        bgra = load_image_bgra(path)
        bgr = np.ascontiguousarray(bgra[:, :, :3])
        landmarks = detect_static_face(bgr)
        has_alpha = bool((bgra[:, :, 3] < 250).any())
        if landmarks is None and not has_alpha:
            alpha = remove_background(bgr)
            if alpha is not None:
                bgra[:, :, 3] = alpha
                log.info("Fondo eliminado automaticamente de %s", path.name)
        slug = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-") or "imagen"
        mask_id = f"custom-{slug}-{int(time.time())}"
        write_mask(self.custom_dir, mask_id, path.stem, bgra, [], landmarks)
        mask = read_mask(self.custom_dir / f"{mask_id}.json", False)
        self._masks[mask.mask_id] = mask
        log.info(
            "Imagen importada como %s (%s)", mask_id, "rostro" if landmarks is not None else "superposicion"
        )
        return mask

    def remove(self, mask_id: str) -> bool:
        mask = self._masks.get(mask_id)
        if mask is None or mask.builtin:
            return False
        for suffix in (".json", ".png"):
            try:
                (self.custom_dir / f"{mask_id}{suffix}").unlink()
            except FileNotFoundError:
                pass
        del self._masks[mask_id]
        return True

    def export(self, mask_id: str, target: Path) -> None:
        source = self.builtin_dir if self._masks[mask_id].builtin else self.custom_dir
        for suffix in (".json", ".png"):
            shutil.copy2(source / f"{mask_id}{suffix}", target / f"{mask_id}{suffix}")
