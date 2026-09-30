import math
from typing import Callable

import numpy as np

from visagecam.masks.geometry import ANCHORS, EYE_L, EYE_R, SIZE, outward  # noqa: F401
from visagecam.masks.painter import Canvas, Color, linear, radial

def fox() -> np.ndarray:
    c = Canvas(SIZE)
    orange: Color = (222, 104, 30)
    deep: Color = (150, 58, 18)
    cream: Color = (250, 240, 220)
    dark: Color = (34, 22, 20)

    for side in (1, -1):
        def sx(x, s=side):
            return x if s == -1 else SIZE - x

        outer = c.poly([(sx(228), 330), (sx(150), 30), (sx(440), 190)])
        c.shadow(outer, 0, 6, 8, 0.4, clip=False)
        c.paint(outer, linear((235, 120, 40), (150, 60, 20), (sx(200), 40), (sx(330), 300)), bevel=0.5, bevel_radius=12, ao=0.35)
        tip = c.poly([(sx(150), 30), (sx(196), 150), (sx(262), 130)])
        c.paint(tip, dark, clip=True, opacity=0.95)
        inner = c.poly([(sx(268), 290), (sx(200), 110), (sx(400), 210)])
        c.paint(inner, linear((248, 214, 190), (120, 60, 50), (sx(230), 120), (sx(330), 290)), bevel=-0.5, bevel_radius=8, ao=0.55)
        c.strands(inner, 700, lambda x, y, s=side: math.atan2(-1, (x - 300) * 0.02), (20, 46), [(252, 228, 205), (236, 190, 165)], 1.2)
        c.strands(outer, 1500, lambda x, y, s=side: math.atan2(-1, 0.4 * (1 if s == 1 else -1)), (22, 60), [orange, (238, 130, 46), deep], 1.3)

    head_pts = [
        (512, 140), (650, 152), (752, 228), (806, 340), (862, 468), (936, 600), (866, 632),
        (896, 704), (806, 730), (762, 812), (652, 892), (512, 950), (372, 892), (262, 812),
        (218, 730), (128, 704), (158, 632), (88, 600), (162, 468), (218, 340), (272, 228), (372, 152),
    ]
    head = c.spline(head_pts)
    c.shadow(head, 0, 10, 14, 0.45, clip=False)
    c.paint(head, radial((240, 128, 44), (176, 72, 22), (512, 380), 520, 1.1), bevel=0.55, bevel_radius=26, ao=0.4, grain=0.05, grain_scale=3)

    lower = c.spline([
        (40, 540), (240, 528), (388, 590), (470, 668), (512, 680), (554, 668),
        (636, 590), (784, 528), (984, 540), (984, 1010), (40, 1010),
    ])
    white = (head * lower).blurred(3)
    c.paint(white, linear((252, 246, 232), (214, 200, 178), (512, 560), (512, 940)), bevel=0.35, bevel_radius=16, ao=0.25, clip=True)
    c.strands(head * lower, 3200, outward(512, 560, 0.6), (26, 70), [cream, (244, 232, 210), (226, 210, 186)], 1.5)
    c.strands(head - lower, 3800, outward(512, 400, 0.5), (24, 64), [orange, (240, 138, 52), deep, (200, 90, 28)], 1.5)

    stripe = c.spline([(512, 206), (556, 290), (540, 420), (512, 560), (484, 420), (468, 290)])
    c.paint(stripe.blurred(10), (248, 226, 190), opacity=0.32, clip=True)

    for ex, sgn in ((EYE_L[0], -1), (EYE_R[0], 1)):
        wing = c.spline([
            (ex - sgn * 92, 458 - 8), (ex - sgn * 40, 372), (ex + sgn * 34, 366),
            (ex + sgn * 118, 402), (ex + sgn * 148, 388), (ex + sgn * 126, 448),
            (ex + sgn * 60, 492), (ex - sgn * 40, 486),
        ])
        c.paint(wing.blurred(2), dark, opacity=0.95, clip=True)
        brow = c.spline([(ex - sgn * 80, 326), (ex, 296), (ex + sgn * 90, 314), (ex, 336)])
        c.paint(brow.blurred(4), cream, clip=True, opacity=0.9)
        socket = c.ellipse((ex, 430), (66, 44), angle=sgn * 8)
        c.paint(socket.blurred(8), (60, 28, 16), opacity=0.5, clip=True)
        c.erase(c.ellipse((ex, 430), (60, 40), angle=sgn * 8), feather=2)

    for sgn in (-1, 1):
        for i, (dx, dy) in enumerate([(150, 640), (180, 690), (160, 736)]):
            c.paint(c.ellipse((512 + sgn * dx, dy), (4.5, 4.5)), (90, 60, 50), clip=True, opacity=0.8)
        for k in range(3):
            y0 = 660 + k * 30
            c.paint(c.stroke([(512 + sgn * 190, y0), (512 + sgn * 330, y0 + (k - 1) * 34)], 2.2), (250, 250, 240), clip=False, opacity=0.9)

    nose = c.spline([(512, 590), (560, 606), (566, 636), (512, 676), (458, 636), (464, 606)])
    c.shadow(nose, 0, 5, 5, 0.5)
    c.paint(nose, radial((70, 60, 62), (10, 8, 10), (500, 610), 60, 0.9), bevel=0.7, bevel_radius=6, ao=0.2)
    c.paint(c.ellipse((494, 608), (18, 8), angle=-12).blurred(2), (220, 225, 235), opacity=0.7, clip=True)
    mouth = c.stroke([(512, 676), (512, 716), (470, 742), (430, 730)], 4.5)
    mouth2 = c.stroke([(512, 716), (554, 742), (594, 730)], 4.5)
    c.paint(mouth + mouth2, (60, 26, 24), clip=True, opacity=0.9)
    return c.to_bgra()




from visagecam.masks.designs_more import alien, bear, cat_astronaut, dragon, robot  # noqa: E402
from visagecam.masks.designs_scifi import DESIGNS_SCIFI  # noqa: E402
from visagecam.masks.half_masks import DESIGNS_HALF  # noqa: E402

DESIGNS: dict[str, tuple[str, Callable[[], np.ndarray]]] = {
    "fox": ("Zorro", fox),
    "robot": ("Robot retro", robot),
    "dragon": ("Dragon", dragon),
    "cat_astronaut": ("Gato astronauta", cat_astronaut),
    "alien": ("Alienigena", alien),
    "bear": ("Oso vintage", bear),
    **DESIGNS_SCIFI,
    **DESIGNS_HALF,
}
