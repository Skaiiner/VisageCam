# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

import logging
import os
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

APP_NAME = "VisageCam"
ASSETS = Path(__file__).resolve().parent / "assets"

SCRIPT = (
    "$shell = New-Object -ComObject WScript.Shell;"
    "$link = $shell.CreateShortcut($env:VC_LINK);"
    "$link.TargetPath = $env:VC_TARGET;"
    "$link.Arguments = $env:VC_ARGS;"
    "$link.WorkingDirectory = $env:VC_WORKDIR;"
    "$link.IconLocation = $env:VC_ICON;"
    "$link.Description = $env:VC_DESC;"
    "$link.Save()"
)


def icon_path() -> Path:
    return ASSETS / "visagecam.ico"


def start_menu_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def desktop_dir() -> Path:
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        folder = result.stdout.strip()
        if folder:
            return Path(folder)
    except (OSError, subprocess.SubprocessError):
        log.exception("No se pudo localizar el escritorio")
    return Path.home() / "Desktop"


def launcher() -> tuple[str, str]:
    interpreter = Path(sys.executable)
    windowless = interpreter.with_name("pythonw.exe")
    target = windowless if windowless.exists() else interpreter
    return str(target), "-m visagecam"


def create_shortcut(directory: Path, name: str = APP_NAME) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    link = directory / f"{name}.lnk"
    target, arguments = launcher()
    env = dict(os.environ)
    env.update(
        VC_LINK=str(link),
        VC_TARGET=target,
        VC_ARGS=arguments,
        VC_WORKDIR=str(Path.home()),
        VC_ICON=f"{icon_path()},0",
        VC_DESC="Camara virtual con mascaras, accesorios y fondos",
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", SCRIPT],
        env=env,
        check=True,
        capture_output=True,
        timeout=30,
    )
    if not link.exists():
        raise OSError(f"No se pudo crear {link}")
    return link


def install(
    desktop: bool = False, start_menu: Path | None = None, desktop_folder: Path | None = None
) -> list[Path]:
    created = [create_shortcut(start_menu or start_menu_dir())]
    if desktop:
        created.append(create_shortcut(desktop_folder or desktop_dir()))
    return created


def remove(start_menu: Path | None = None, desktop_folder: Path | None = None) -> list[Path]:
    removed = []
    for folder in (start_menu or start_menu_dir(), desktop_folder or desktop_dir()):
        link = folder / f"{APP_NAME}.lnk"
        if link.exists():
            link.unlink()
            removed.append(link)
    return removed
