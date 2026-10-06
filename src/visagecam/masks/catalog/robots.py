# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

import math

import numpy as np

from visagecam.masks.geometry import EYE_L, EYE_R, NOSE, SIZE
from visagecam.masks.painter import Canvas, Color, linear, radial
from visagecam.masks.shapes import circle, noise_shape, ring, rrect


def robot() -> np.ndarray:
    c = Canvas(SIZE)
    chrome: Color = (226, 232, 236)

    stalk = c.stroke([(512, 160), (512, 60)], 16)
    c.paint(stalk, linear((250, 250, 255), (120, 130, 140), (500, 0), (526, 0)), bevel=0.6, bevel_radius=4)
    bulb = circle(c, (512, 44), 36)
    c.paint(circle(c, (512, 44), 70).blurred(14), (255, 60, 40), opacity=0.35)
    c.paint(bulb, radial((255, 210, 190), (190, 20, 20), (500, 32), 46), bevel=0.5, bevel_radius=6)
    c.paint(c.ellipse((500, 30), (12, 8)).blurred(2), (255, 255, 255), opacity=0.8, clip=True)

    for sgn, cx in ((1, 96), (-1, SIZE - 96)):
        cyl = c.poly(rrect(cx - 56, 380, cx + 56, 580, 26))
        c.shadow(cyl, 0, 8, 8, 0.45, clip=False)
        c.paint(
            cyl,
            linear((110, 118, 126), (250, 252, 255), (cx - 56, 0), (cx + 56, 0)),
            bevel=0.6,
            bevel_radius=8,
            ao=0.3,
        )
        for k in range(5):
            y = 410 + k * 34
            c.paint(c.stroke([(cx - 44, y), (cx + 44, y)], 6), (40, 46, 54), opacity=0.7, clip=True)

    body = c.poly(rrect(150, 130, 874, 960, 110))
    c.shadow(body, 0, 14, 20, 0.55, clip=False)
    c.paint(
        body,
        linear((196, 224, 216), (92, 130, 126), (150, 130), (874, 960)),
        bevel=0.7,
        bevel_radius=26,
        ao=0.4,
        streak=0.09,
        grain=0.03,
    )
    rust = noise_shape(c, body, 9, 0.9)
    c.paint(rust, (150, 84, 40), opacity=0.55, clip=True)
    c.paint(noise_shape(c, body, 3, 1.5), (110, 60, 30), opacity=0.4, clip=True)
    for y in (312, 700):
        c.paint(c.stroke([(160, y), (864, y)], 5), (30, 46, 46), opacity=0.8, clip=True)
        c.paint(c.stroke([(160, y + 5), (864, y + 5)], 3), (240, 250, 248), opacity=0.35, clip=True)
    for x, y in [
        (190, 170),
        (834, 170),
        (190, 920),
        (834, 920),
        (190, 330),
        (834, 330),
        (190, 690),
        (834, 690),
    ]:
        rv = circle(c, (x, y), 13)
        c.shadow(rv, 1, 3, 2, 0.5)
        c.paint(rv, radial((250, 252, 255), (110, 118, 124), (x - 4, y - 5), 18), bevel=0.4, bevel_radius=3)

    for lx, color in ((424, (255, 70, 60)), (512, (255, 190, 50)), (600, (80, 230, 120))):
        c.paint(circle(c, (lx, 232), 30).blurred(8), color, opacity=0.5)
        lamp = circle(c, (lx, 232), 17)
        c.paint(ring(c, (lx, 232), 24, 15), chrome, bevel=0.6, bevel_radius=3)
        c.paint(
            lamp,
            radial(tuple(min(255, v + 80) for v in color), color, (lx - 5, 226), 22),
            bevel=0.4,
            bevel_radius=3,
        )

    visor = c.poly(rrect(184, 340, 840, 522, 60))
    c.paint(
        visor, linear((34, 44, 50), (12, 16, 20), (0, 340), (0, 522)), bevel=-0.5, bevel_radius=10, ao=0.4
    )
    for ex in (EYE_L[0], EYE_R[0]):
        c.paint(
            ring(c, (ex, 430), 98, 74),
            linear((250, 252, 255), (100, 108, 116), (ex - 90, 340), (ex + 90, 520)),
            bevel=0.9,
            bevel_radius=6,
        )
        c.paint(ring(c, (ex, 430), 80, 72), (20, 26, 30), opacity=0.8, clip=True)
        for k in range(8):
            a = k * math.pi / 4
            rv = circle(c, (ex + 88 * math.cos(a), 430 + 88 * math.sin(a)), 4.5)
            c.paint(rv, (40, 46, 52), bevel=0.4, bevel_radius=1.5)
        c.erase(circle(c, (ex, 430), 72), feather=1.5)

    grille = c.poly(rrect(350, 704, 674, 834, 26))
    c.paint(grille, (18, 22, 26), bevel=-0.7, bevel_radius=6)
    for i in range(7):
        x = 372 + i * 46
        c.paint(
            c.poly(rrect(x, 720, x + 26, 818, 10)),
            linear((240, 246, 248), (110, 120, 128), (x, 0), (x + 26, 0)),
            bevel=0.7,
            bevel_radius=4,
            clip=True,
        )
    speaker = circle(c, NOSE, 44)
    c.paint(ring(c, NOSE, 54, 44), chrome, bevel=0.8, bevel_radius=5)
    c.paint(speaker, (22, 28, 32), bevel=-0.5, bevel_radius=6)
    for r in (34, 24, 14):
        c.paint(ring(c, NOSE, r, r - 4), (110, 122, 130), opacity=0.9)
    c.paint(circle(c, NOSE, 6), (200, 210, 216))
    return c.to_bgra()


def chrome_knight() -> np.ndarray:
    c = Canvas(SIZE)
    gold: Color = (210, 178, 110)
    steel: Color = (200, 202, 208)
    dark: Color = (28, 30, 36)
    cyan: Color = (255, 224, 140)

    dome = c.spline(
        [
            (512, 70),
            (700, 96),
            (824, 210),
            (880, 360),
            (866, 500),
            (900, 540),
            (852, 610),
            (812, 760),
            (700, 900),
            (512, 960),
            (324, 900),
            (212, 760),
            (172, 610),
            (124, 540),
            (158, 500),
            (144, 360),
            (200, 210),
            (324, 96),
        ]
    )
    c.shadow(dome, 0, 14, 18, 0.55, clip=False)
    c.paint(
        dome,
        radial((225, 205, 175), (110, 96, 78), (460, 360), 560, 1.1),
        bevel=0.75,
        bevel_radius=26,
        ao=0.4,
        streak=0.12,
    )
    for x in (512, 452, 572, 392, 632):
        rib = c.poly(rrect(x - 26, 90, x + 26, 560, 18))
        c.paint(
            rib,
            linear((235, 200, 140), (150, 118, 62), (x - 26, 0), (x + 26, 0)),
            bevel=0.8,
            bevel_radius=8,
            ao=0.3,
            clip=True,
        )
        c.paint(c.stroke([(x, 130), (x, 520)], 4), cyan, opacity=0.85, clip=True)

    crest = c.poly(rrect(472, 120, 552, 300, 30))
    c.paint(crest, linear(gold, (140, 108, 52), (472, 120), (552, 300)), bevel=0.9, bevel_radius=10, ao=0.3)
    gem = circle(c, (512, 190), 34)
    c.paint(circle(c, (512, 190), 54).blurred(10), cyan, opacity=0.5, clip=False)
    c.paint(gem, radial((255, 250, 210), (200, 140, 40), (500, 178), 40), bevel=0.6, bevel_radius=6)
    for y in (232, 250, 268):
        c.paint(c.stroke([(494, y), (530, y)], 4), (60, 44, 20), opacity=0.7, clip=True)

    brow = c.poly(rrect(214, 300, 810, 400, 40))
    c.paint(brow, linear(gold, (120, 92, 42), (214, 300), (810, 400)), bevel=0.85, bevel_radius=14, ao=0.35)

    visor = c.poly(rrect(196, 330, 828, 560, 80))
    c.paint(
        visor,
        linear((150, 156, 168), (60, 64, 74), (196, 330), (828, 560)),
        bevel=0.6,
        bevel_radius=16,
        ao=0.4,
    )
    for ex, sgn in ((EYE_L[0], -1), (EYE_R[0], 1)):
        socket = c.spline(
            [
                (ex - sgn * 96, 398),
                (ex, 366),
                (ex + sgn * 118, 384),
                (ex + sgn * 132, 440),
                (ex + sgn * 88, 486),
                (ex - sgn * 20, 480),
            ]
        )
        c.paint(socket, dark, bevel=-0.5, bevel_radius=6, clip=True)
        c.paint(
            ring(c, (ex, 430), 108, 96),
            linear(gold, (150, 116, 54), (ex - 100, 380), (ex + 100, 480)),
            bevel=0.8,
            bevel_radius=6,
            clip=True,
        )
        for k in range(10):
            a = math.pi * (0.15 + 0.7 * k / 9)
            c.paint(
                circle(c, (ex + 100 * math.cos(a), 430 + 55 * math.sin(a)), 3), cyan, opacity=0.7, clip=True
            )
        c.erase(
            c.spline(
                [
                    (ex - sgn * 78, 402),
                    (ex, 378),
                    (ex + sgn * 96, 394),
                    (ex + sgn * 104, 436),
                    (ex + sgn * 70, 470),
                    (ex - sgn * 10, 464),
                ]
            ),
            feather=1.5,
        )

    cheek = c.spline([(190, 560), (360, 620), (350, 760), (240, 860), (150, 800), (140, 660)])
    c.paint(
        cheek,
        radial((220, 200, 172), (120, 104, 84), (220, 660), 300),
        bevel=0.5,
        bevel_radius=14,
        ao=0.3,
        clip=False,
    )
    cheek2 = c.spline(
        [
            (SIZE - 190, 560),
            (SIZE - 360, 620),
            (SIZE - 350, 760),
            (SIZE - 240, 860),
            (SIZE - 150, 800),
            (SIZE - 140, 660),
        ]
    )
    c.paint(
        cheek2,
        radial((220, 200, 172), (120, 104, 84), (SIZE - 220, 660), 300),
        bevel=0.5,
        bevel_radius=14,
        ao=0.3,
        clip=False,
    )
    for cx in (220, SIZE - 220):
        c.paint(c.stroke([(cx, 600), (cx, 820)], 5), cyan, opacity=0.55, clip=False)

    nose = c.poly(rrect(468, 470, 556, 700, 28))
    c.paint(
        nose,
        linear(steel, (110, 112, 120), (468, 470), (556, 700)),
        bevel=0.6,
        bevel_radius=10,
        ao=0.35,
        clip=False,
    )
    c.erase(c.poly(rrect(492, 560, 532, 690, 16)), feather=2)

    jaw = c.spline(
        [
            (200, 760),
            (300, 900),
            (450, 972),
            (512, 990),
            (574, 972),
            (724, 900),
            (824, 760),
            (700, 820),
            (512, 862),
            (324, 820),
        ]
    )
    c.paint(
        jaw,
        linear((190, 176, 152), (96, 84, 68), (300, 760), (700, 990)),
        bevel=0.55,
        bevel_radius=14,
        ao=0.35,
        clip=False,
    )
    for k in range(7):
        x = 380 + k * 44
        c.paint(c.stroke([(x, 840), (x, 900)], 4), (60, 52, 40), opacity=0.5, clip=False)
    return c.to_bgra()
