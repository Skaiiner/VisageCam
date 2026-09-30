import math
from typing import Callable

from visagecam.masks.model import Anchor

SIZE = 1024

EYE_L = (397.0, 430.0)
EYE_R = (627.0, 430.0)
NOSE = (512.0, 614.0)
MOUTH = (512.0, 759.0)
CHIN = (512.0, 855.0)
FOREHEAD = (512.0, 177.0)

ANCHORS = [
    Anchor("eye_left", (33, 133, 159, 145), EYE_L),
    Anchor("eye_right", (362, 263, 386, 374), EYE_R),
    Anchor("nose_tip", (1,), NOSE),
    Anchor("mouth", (13, 14), MOUTH),
    Anchor("chin", (152,), CHIN),
    Anchor("forehead", (10,), FOREHEAD),
]


def mirror(points):
    return [(SIZE - x, y) for x, y in points]


def outward(cx: float, cy: float, bias: float = 0.35) -> Callable[[float, float], float]:
    def fn(x: float, y: float) -> float:
        return math.atan2(y - cy + bias * 90, x - cx)

    return fn
