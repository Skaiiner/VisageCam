# Copyright (c) 2026 Skain. Todos los derechos reservados.

from collections.abc import Callable
from dataclasses import dataclass

from visagecam.backgrounds import BackgroundLibrary
from visagecam.config import Settings
from visagecam.masks.library import MaskLibrary
from visagecam.processing.engine import Engine
from visagecam.ui.widgets import AsyncRunner


@dataclass
class Context:
    settings: Settings
    library: MaskLibrary
    backgrounds: BackgroundLibrary
    engine: Engine
    runner: AsyncRunner
    notify: Callable[[str, str], None]
    save: Callable[[], None]

    def set(self, key: str, value) -> None:
        setattr(self.settings, key, value)
        self.save()

    def set_person2(self, key: str, value) -> None:
        setattr(self.settings.person2, key, value)
        self.save()
