# Copyright (c) 2026 Skain. Todos los derechos reservados.

from collections.abc import Callable

import numpy as np

from visagecam.masks.catalog.accessories import ACCESSORIES, AccessorySpec
from visagecam.masks.catalog.creatures import alien, bear, cat_astronaut, dragon, fox, phoenix, tribal_wolf
from visagecam.masks.catalog.masquerade import butterfly, cat_eye_lace, feather_noir, harlequin, venetian_gold
from visagecam.masks.catalog.robots import chrome_knight, robot
from visagecam.masks.geometry import ANCHORS

DESIGNS: dict[str, tuple[str, Callable[[], np.ndarray]]] = {
    "fox": ("Zorro", fox),
    "robot": ("Robot retro", robot),
    "dragon": ("Dragon", dragon),
    "cat_astronaut": ("Gato astronauta", cat_astronaut),
    "alien": ("Alienigena", alien),
    "bear": ("Oso vintage", bear),
    "chrome_knight": ("Caballero cromado", chrome_knight),
    "phoenix": ("Fenix", phoenix),
    "tribal_wolf": ("Lobo tribal", tribal_wolf),
    "venetian_gold": ("Veneciana dorada", venetian_gold),
    "butterfly": ("Mariposa", butterfly),
    "feather_noir": ("Pluma negra", feather_noir),
    "harlequin": ("Arlequin", harlequin),
    "cat_eye_lace": ("Ojos de gata", cat_eye_lace),
}

__all__ = ["ACCESSORIES", "ANCHORS", "DESIGNS", "AccessorySpec"]
