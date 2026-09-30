import math

import numpy as np

from visagecam.masks.geometry import EYE_L, EYE_R, NOSE, SIZE
from visagecam.masks.painter import Canvas, Color, linear, radial
from visagecam.masks.shapes import circle, dashed, ring, rrect


def chrome_knight() -> np.ndarray:
    c = Canvas(SIZE)
    gold: Color = (210, 178, 110)
    steel: Color = (200, 202, 208)
    dark: Color = (28, 30, 36)
    cyan: Color = (255, 224, 140)

    dome = c.spline([
        (512, 70), (700, 96), (824, 210), (880, 360), (866, 500), (900, 540),
        (852, 610), (812, 760), (700, 900), (512, 960), (324, 900), (212, 760),
        (172, 610), (124, 540), (158, 500), (144, 360), (200, 210), (324, 96),
    ])
    c.shadow(dome, 0, 14, 18, 0.55, clip=False)
    c.paint(dome, radial((225, 205, 175), (110, 96, 78), (460, 360), 560, 1.1), bevel=0.75, bevel_radius=26, ao=0.4, streak=0.12)
    for x in (512, 452, 572, 392, 632):
        rib = c.poly(rrect(x - 26, 90, x + 26, 560, 18))
        c.paint(rib, linear((235, 200, 140), (150, 118, 62), (x - 26, 0), (x + 26, 0)), bevel=0.8, bevel_radius=8, ao=0.3, clip=True)
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
    c.paint(visor, linear((150, 156, 168), (60, 64, 74), (196, 330), (828, 560)), bevel=0.6, bevel_radius=16, ao=0.4)
    for ex, sgn in ((EYE_L[0], -1), (EYE_R[0], 1)):
        socket = c.spline([
            (ex - sgn * 96, 398), (ex, 366), (ex + sgn * 118, 384), (ex + sgn * 132, 440),
            (ex + sgn * 88, 486), (ex - sgn * 20, 480),
        ])
        c.paint(socket, dark, bevel=-0.5, bevel_radius=6, clip=True)
        c.paint(ring(c, (ex, 430), 108, 96), linear(gold, (150, 116, 54), (ex - 100, 380), (ex + 100, 480)), bevel=0.8, bevel_radius=6, clip=True)
        for k in range(10):
            a = math.pi * (0.15 + 0.7 * k / 9)
            c.paint(circle(c, (ex + 100 * math.cos(a), 430 + 55 * math.sin(a)), 3), cyan, opacity=0.7, clip=True)
        c.erase(c.spline([(ex - sgn * 78, 402), (ex, 378), (ex + sgn * 96, 394), (ex + sgn * 104, 436), (ex + sgn * 70, 470), (ex - sgn * 10, 464)]), feather=1.5)

    cheek = c.spline([(190, 560), (360, 620), (350, 760), (240, 860), (150, 800), (140, 660)])
    c.paint(cheek, radial((220, 200, 172), (120, 104, 84), (220, 660), 300), bevel=0.5, bevel_radius=14, ao=0.3, clip=False)
    cheek2 = c.spline([(SIZE - 190, 560), (SIZE - 360, 620), (SIZE - 350, 760), (SIZE - 240, 860), (SIZE - 150, 800), (SIZE - 140, 660)])
    c.paint(cheek2, radial((220, 200, 172), (120, 104, 84), (SIZE - 220, 660), 300), bevel=0.5, bevel_radius=14, ao=0.3, clip=False)
    for cx in (220, SIZE - 220):
        c.paint(c.stroke([(cx, 600), (cx, 820)], 5), cyan, opacity=0.55, clip=False)

    nose = c.poly(rrect(468, 470, 556, 700, 28))
    c.paint(nose, linear(steel, (110, 112, 120), (468, 470), (556, 700)), bevel=0.6, bevel_radius=10, ao=0.35, clip=False)
    c.erase(c.poly(rrect(492, 560, 532, 690, 16)), feather=2)

    jaw = c.spline([(200, 760), (300, 900), (450, 972), (512, 990), (574, 972), (724, 900), (824, 760), (700, 820), (512, 862), (324, 820)])
    c.paint(jaw, linear((190, 176, 152), (96, 84, 68), (300, 760), (700, 990)), bevel=0.55, bevel_radius=14, ao=0.35, clip=False)
    for k in range(7):
        x = 380 + k * 44
        c.paint(c.stroke([(x, 840), (x, 900)], 4), (60, 52, 40), opacity=0.5, clip=False)
    return c.to_bgra()


def phoenix() -> np.ndarray:
    c = Canvas(SIZE)
    fire_a: Color = (255, 150, 40)
    fire_b: Color = (200, 30, 20)
    gold: Color = (255, 205, 90)

    for sgn in (-1, 1):
        def sx(x, s=sgn):
            return x if s == -1 else SIZE - x

        plume = c.poly([
            (sx(230), 420), (sx(30), 210), (sx(70), 120), (sx(160), 40), (sx(190), 130),
            (sx(260), 60), (sx(300), 160), (sx(360), 110), (sx(370), 230), (sx(300), 330),
        ])
        c.shadow(plume, 0, 8, 10, 0.4, clip=False)
        c.paint(plume, linear(gold, fire_a, (sx(360), 60), (sx(70), 330)), bevel=0.5, bevel_radius=10, ao=0.3)
        c.strands(plume, 2200, lambda x, y, s=sgn: math.atan2(y - 260, (x - 512) * s * -1), (26, 70), [fire_a, gold, fire_b], 1.6, curl=0.1)

    head_pts = [
        (512, 130), (660, 168), (770, 280), (820, 430), (798, 590), (900, 560), (846, 660),
        (874, 760), (780, 780), (742, 890), (630, 960), (512, 984), (394, 960), (282, 890),
        (244, 780), (150, 760), (178, 660), (124, 560), (226, 590), (204, 430), (254, 280), (364, 168),
    ]
    head = c.spline(head_pts, samples=8)
    c.shadow(head, 0, 12, 16, 0.5, clip=False)
    c.paint(head, radial((255, 224, 160), fire_b, (500, 420), 560, 1.1), bevel=0.6, bevel_radius=26, ao=0.4)
    c.strands(head, 6000, lambda x, y: math.atan2(y - 420, x - 512), (14, 30), [fire_a, gold, (170, 30, 20)], 1.3, curl=0.15)

    crest = c.poly([(512, 150), (478, 90), (512, 60), (546, 90)])
    c.paint(crest, gold, bevel=0.6, bevel_radius=4, clip=True)

    beak = c.spline([(512, 640), (600, 660), (620, 700), (512, 780), (404, 700), (424, 660)], samples=8)
    c.shadow(beak, 0, 5, 5, 0.5, clip=False)
    c.paint(beak, linear((255, 214, 120), (200, 140, 30), (420, 640), (600, 780)), bevel=0.7, bevel_radius=8, ao=0.25)
    c.paint(c.stroke([(512, 700), (512, 660)], 3), (140, 90, 20), opacity=0.6, clip=True)

    for ex, sgn in ((EYE_L[0], -1), (EYE_R[0], 1)):
        brow = c.spline([(ex - sgn * 90, 360), (ex, 322), (ex + sgn * 100, 340), (ex + sgn * 150, 300)])
        c.paint(brow, linear(gold, fire_a, (0, 320), (0, 380)), bevel=0.7, bevel_radius=6, clip=True)
        c.paint(ring(c, (ex, 430), 92, 70), linear((90, 30, 16), (40, 10, 8), (ex - 80, 380), (ex + 80, 480)), bevel=0.6, bevel_radius=8, clip=True)
        c.erase(circle(c, (ex, 430), 68), feather=2)

    NOSE
    return c.to_bgra()


def tribal_wolf() -> np.ndarray:
    c = Canvas(SIZE)
    wood: Color = (92, 60, 38)
    bone: Color = (232, 218, 188)
    red: Color = (168, 34, 30)

    head_pts = [
        (512, 110), (668, 150), (780, 260), (842, 420), (820, 560), (886, 600), (826, 680),
        (852, 800), (760, 830), (706, 930), (600, 984), (512, 1000), (424, 984), (318, 930),
        (264, 830), (172, 800), (198, 680), (138, 600), (204, 560), (182, 420), (244, 260), (356, 150),
    ]
    head = c.spline(head_pts, samples=8)
    c.shadow(head, 0, 14, 16, 0.55, clip=False)
    c.paint(head, radial((150, 100, 64), (58, 36, 22), (490, 420), 560, 1.1), bevel=0.6, bevel_radius=24, ao=0.45, grain=0.08, grain_scale=4)
    c.paint(head - c.spline(head_pts, samples=8).blurred(60), (30, 18, 12), opacity=0.5, clip=True)

    for sgn in (-1, 1):
        ear = c.poly([(512 + sgn * 140, 210), (512 + sgn * 90, 30), (512 + sgn * 260, 130)])
        c.paint(ear, linear(wood, (50, 30, 18), (512, 30), (512 + sgn * 260, 210)), bevel=0.6, bevel_radius=8, ao=0.3)
        c.paint(c.poly([(512 + sgn * 150, 190), (512 + sgn * 116, 70), (512 + sgn * 220, 140)]), (60, 30, 20), opacity=0.6, clip=True)

    for x, y in [(430, 780), (512, 800), (594, 780)]:
        fang = c.poly([(x - 18, y), (x + 18, y), (x, y + 56)])
        c.paint(fang, bone, bevel=0.5, bevel_radius=4, clip=True)

    for ex, sgn in ((EYE_L[0], -1), (EYE_R[0], 1)):
        mark = c.poly([(ex - sgn * 120, 340), (ex + sgn * 60, 300), (ex + sgn * 150, 400), (ex - sgn * 10, 520), (ex - sgn * 130, 480)])
        c.paint(mark, red, opacity=0.85, bevel=0.3, bevel_radius=6, clip=True)
        dashed(c, [(ex - sgn * 100, 380), (ex + sgn * 30, 350)], bone, 14, 8, 4, clip=True)
        c.paint(ring(c, (ex, 430), 80, 68), (20, 14, 10), bevel=-0.5, bevel_radius=6, clip=True)
        c.erase(circle(c, (ex, 430), 66), feather=2)

    for k in range(6):
        y = 560 + k * 60
        dashed(c, [(180 + k * 8, y), (260, y - 20)], bone, 16, 10, 3, clip=True, opacity=0.6)
        dashed(c, [(SIZE - 180 - k * 8, y), (SIZE - 260, y - 20)], bone, 16, 10, 3, clip=True, opacity=0.6)

    nose = c.spline([(512, 640), (560, 668), (566, 706), (512, 748), (458, 706), (464, 668)], samples=8)
    c.paint(nose, radial((40, 26, 22), (10, 6, 6), (500, 680), 60), bevel=0.6, bevel_radius=6)
    return c.to_bgra()


DESIGNS_SCIFI = {
    "chrome_knight": ("Caballero cromado", chrome_knight),
    "phoenix": ("Fenix", phoenix),
    "tribal_wolf": ("Lobo tribal", tribal_wolf),
}
