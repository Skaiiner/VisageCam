import argparse
import logging
from pathlib import Path

from visagecam.masks.designs import ANCHORS, DESIGNS
from visagecam.masks.storage import write_mask

log = logging.getLogger(__name__)

GENERATOR_VERSION = "3"
MASK_ORDER = list(DESIGNS)

def generate(directory: Path, only: list[str] | None = None) -> list[Path]:
    written = []
    for mask_id, (name, builder) in DESIGNS.items():
        if only and mask_id not in only:
            continue
        log.info("Generando mascara %s", mask_id)
        written.append(write_mask(directory, mask_id, name, builder(), ANCHORS))
    (directory / ".version").write_text(GENERATOR_VERSION, encoding="utf-8")
    return written


def ensure_masks(directory: Path) -> None:
    marker = directory / ".version"
    complete = all((directory / f"{mask_id}.json").exists() for mask_id in DESIGNS)
    if complete and marker.exists() and marker.read_text(encoding="utf-8") == GENERATOR_VERSION:
        return
    directory.mkdir(parents=True, exist_ok=True)
    generate(directory)


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera las mascaras originales de VisageCam")
    parser.add_argument("--out", type=Path, default=Path("masks_out"))
    parser.add_argument("--only", nargs="*", default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for path in generate(args.out, args.only):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
