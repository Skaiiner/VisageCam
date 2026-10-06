# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YEAR = 2026
HEADER = "# Copyright (c) {year} {owner}. Todos los derechos reservados."
HEADER_PATTERN = re.compile(r"^# Copyright \(c\) \d{4} .+\. Todos los derechos reservados\.$")
SOURCES = ("src", "tests", "scripts")


def python_files() -> list[Path]:
    files = []
    for folder in SOURCES:
        files.extend(sorted((ROOT / folder).rglob("*.py")))
    return [f for f in files if "egg-info" not in str(f)]


def apply_header(path: Path, owner: str, year: int) -> bool:
    text = path.read_text(encoding="utf-8")
    header = HEADER.format(year=year, owner=owner)
    lines = text.splitlines()
    if lines and HEADER_PATTERN.match(lines[0]):
        if lines[0] == header:
            return False
        lines[0] = header
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True
    body = text.lstrip("\n")
    path.write_text(header + ("\n\n" + body if body else "\n"), encoding="utf-8")
    return True


def replace_in(path: Path, pattern: str, replacement: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    updated = re.sub(pattern, replacement, text, flags=re.M)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Fija el titular de los derechos de autor del proyecto")
    parser.add_argument("owner", help="nombre del titular, por ejemplo: Skaiiner")
    parser.add_argument("--year", type=int, default=YEAR)
    args = parser.parse_args()
    changed = [str(f.relative_to(ROOT)) for f in python_files() if apply_header(f, args.owner, args.year)]
    notice = f"Copyright (c) {args.year} {args.owner}. Todos los derechos reservados."
    replace_in(ROOT / "LICENSE", r"^Copyright \(c\) \d{4} .+\. Todos los derechos reservados\.$", notice)
    replace_in(
        ROOT / "pyproject.toml", r'^authors = \[\{ name = ".*?"', f'authors = [{{ name = "{args.owner}"'
    )
    replace_in(
        ROOT / "src" / "visagecam" / "__init__.py", r'^__author__ = ".*"$', f'__author__ = "{args.owner}"'
    )
    replace_in(
        ROOT / "src" / "visagecam" / "__init__.py",
        r'^__copyright__ = ".*"$',
        f'__copyright__ = "Copyright (c) {args.year} {args.owner}"',
    )
    print(f"{len(changed)} archivos actualizados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
