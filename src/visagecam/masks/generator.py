# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

import argparse
import logging
from pathlib import Path

from visagecam.masks.catalog import ACCESSORIES, ANCHORS, DESIGNS
from visagecam.masks.storage import write_mask

log = logging.getLogger(__name__)

GENERATOR_VERSION = "4"
MASK_ORDER = list(DESIGNS)
ACCESSORY_ORDER = list(ACCESSORIES)


def _current(directory: Path, ids) -> bool:
    marker = directory / ".version"
    return (
        all((directory / f"{i}.json").exists() for i in ids)
        and marker.exists()
        and marker.read_text(encoding="utf-8") == GENERATOR_VERSION
    )


def generate(directory: Path, only: list[str] | None = None) -> list[Path]:
    written = []
    for mask_id, (name, builder) in DESIGNS.items():
        if only and mask_id not in only:
            continue
        log.info("Generando mascara %s", mask_id)
        written.append(write_mask(directory, mask_id, name, builder(), ANCHORS))
    (directory / ".version").write_text(GENERATOR_VERSION, encoding="utf-8")
    return written


def generate_accessories(directory: Path, only: list[str] | None = None) -> list[Path]:
    written = []
    for acc_id, spec in ACCESSORIES.items():
        if only and acc_id not in only:
            continue
        log.info("Generando accesorio %s", acc_id)
        written.append(
            write_mask(
                directory,
                acc_id,
                spec.name,
                spec.builder(),
                [],
                kind="accessory",
                slot=spec.slot,
                pivot=spec.pivot,
                width_ratio=spec.width_ratio,
            )
        )
    (directory / ".version").write_text(GENERATOR_VERSION, encoding="utf-8")
    return written


def ensure_masks(directory: Path) -> None:
    if _current(directory, DESIGNS):
        return
    directory.mkdir(parents=True, exist_ok=True)
    generate(directory)


def ensure_accessories(directory: Path) -> None:
    if _current(directory, ACCESSORIES):
        return
    directory.mkdir(parents=True, exist_ok=True)
    generate_accessories(directory)


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera las mascaras y accesorios originales")
    parser.add_argument("--out", type=Path, default=Path("masks_out"))
    parser.add_argument("--only", nargs="*", default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for path in generate(args.out, args.only) + generate_accessories(args.out / "accessories", args.only):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
