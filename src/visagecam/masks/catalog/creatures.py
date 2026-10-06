# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

import math

import numpy as np

from visagecam.masks.geometry import EYE_L, EYE_R, NOSE, SIZE, outward
from visagecam.masks.painter import Canvas, Color, linear, radial
from visagecam.masks.shapes import circle, dashed, noise_shape, ring, rrect, tapered


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
        c.paint(
            outer,
            linear((235, 120, 40), (150, 60, 20), (sx(200), 40), (sx(330), 300)),
            bevel=0.5,
            bevel_radius=12,
            ao=0.35,
        )
        tip = c.poly([(sx(150), 30), (sx(196), 150), (sx(262), 130)])
        c.paint(tip, dark, clip=True, opacity=0.95)
        inner = c.poly([(sx(268), 290), (sx(200), 110), (sx(400), 210)])
        c.paint(
            inner,
            linear((248, 214, 190), (120, 60, 50), (sx(230), 120), (sx(330), 290)),
            bevel=-0.5,
            bevel_radius=8,
            ao=0.55,
        )
        c.strands(
            inner,
            700,
            lambda x, y, s=side: math.atan2(-1, (x - 300) * 0.02),
            (20, 46),
            [(252, 228, 205), (236, 190, 165)],
            1.2,
        )
        c.strands(
            outer,
            1500,
            lambda x, y, s=side: math.atan2(-1, 0.4 * (1 if s == 1 else -1)),
            (22, 60),
            [orange, (238, 130, 46), deep],
            1.3,
        )

    head_pts = [
        (512, 140),
        (650, 152),
        (752, 228),
        (806, 340),
        (862, 468),
        (936, 600),
        (866, 632),
        (896, 704),
        (806, 730),
        (762, 812),
        (652, 892),
        (512, 950),
        (372, 892),
        (262, 812),
        (218, 730),
        (128, 704),
        (158, 632),
        (88, 600),
        (162, 468),
        (218, 340),
        (272, 228),
        (372, 152),
    ]
    head = c.spline(head_pts)
    c.shadow(head, 0, 10, 14, 0.45, clip=False)
    c.paint(
        head,
        radial((240, 128, 44), (176, 72, 22), (512, 380), 520, 1.1),
        bevel=0.55,
        bevel_radius=26,
        ao=0.4,
        grain=0.05,
        grain_scale=3,
    )

    lower = c.spline(
        [
            (40, 540),
            (240, 528),
            (388, 590),
            (470, 668),
            (512, 680),
            (554, 668),
            (636, 590),
            (784, 528),
            (984, 540),
            (984, 1010),
            (40, 1010),
        ]
    )
    white = (head * lower).blurred(3)
    c.paint(
        white,
        linear((252, 246, 232), (214, 200, 178), (512, 560), (512, 940)),
        bevel=0.35,
        bevel_radius=16,
        ao=0.25,
        clip=True,
    )
    c.strands(
        head * lower, 3200, outward(512, 560, 0.6), (26, 70), [cream, (244, 232, 210), (226, 210, 186)], 1.5
    )
    c.strands(
        head - lower,
        3800,
        outward(512, 400, 0.5),
        (24, 64),
        [orange, (240, 138, 52), deep, (200, 90, 28)],
        1.5,
    )

    stripe = c.spline([(512, 206), (556, 290), (540, 420), (512, 560), (484, 420), (468, 290)])
    c.paint(stripe.blurred(10), (248, 226, 190), opacity=0.32, clip=True)

    for ex, sgn in ((EYE_L[0], -1), (EYE_R[0], 1)):
        wing = c.spline(
            [
                (ex - sgn * 92, 458 - 8),
                (ex - sgn * 40, 372),
                (ex + sgn * 34, 366),
                (ex + sgn * 118, 402),
                (ex + sgn * 148, 388),
                (ex + sgn * 126, 448),
                (ex + sgn * 60, 492),
                (ex - sgn * 40, 486),
            ]
        )
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
            c.paint(
                c.stroke([(512 + sgn * 190, y0), (512 + sgn * 330, y0 + (k - 1) * 34)], 2.2),
                (250, 250, 240),
                clip=False,
                opacity=0.9,
            )

    nose = c.spline([(512, 590), (560, 606), (566, 636), (512, 676), (458, 636), (464, 606)])
    c.shadow(nose, 0, 5, 5, 0.5)
    c.paint(nose, radial((70, 60, 62), (10, 8, 10), (500, 610), 60, 0.9), bevel=0.7, bevel_radius=6, ao=0.2)
    c.paint(c.ellipse((494, 608), (18, 8), angle=-12).blurred(2), (220, 225, 235), opacity=0.7, clip=True)
    mouth = c.stroke([(512, 676), (512, 716), (470, 742), (430, 730)], 4.5)
    mouth2 = c.stroke([(512, 716), (554, 742), (594, 730)], 4.5)
    c.paint(mouth + mouth2, (60, 26, 24), clip=True, opacity=0.9)
    return c.to_bgra()


def bear() -> np.ndarray:
    c = Canvas(SIZE)
    fur = [(146, 98, 58), (170, 118, 70), (118, 76, 44), (188, 136, 84)]
    cream = [(230, 204, 158), (244, 222, 178), (208, 180, 134)]
    thread: Color = (238, 216, 176)

    for cx in (232, SIZE - 232):
        ear = circle(c, (cx, 196), 128)
        c.shadow(ear, 0, 8, 10, 0.5, clip=False)
        c.paint(
            ear,
            radial((176, 122, 74), (108, 68, 40), (cx - 30, 160), 150),
            bevel=0.6,
            bevel_radius=16,
            ao=0.35,
        )
        c.strands(ear, 1800, lambda x, y, cx=cx: math.atan2(y - 196, x - cx), (10, 26), fur, 1.5, curl=0.25)
        inner = circle(c, (cx, 200), 76)
        c.paint(
            inner, radial((214, 176, 126), (160, 118, 78), (cx, 200), 80), bevel=-0.5, bevel_radius=12, ao=0.3
        )
        c.strands(inner, 700, lambda x, y, cx=cx: math.atan2(y - 200, x - cx), (8, 18), cream, 1.4, curl=0.2)
        c.paint(ring(c, (cx, 200), 84, 78), (90, 56, 32), opacity=0.7)
        for k in range(18):
            a = k * math.pi / 9
            dashed(
                c,
                [
                    (cx + 100 * math.cos(a), 196 + 100 * math.sin(a)),
                    (cx + 100 * math.cos(a + 0.22), 196 + 100 * math.sin(a + 0.22)),
                ],
                thread,
                12,
                100,
                3.6,
                smooth=False,
                opacity=0.9,
                clip=True,
            )

    head_pts = [
        (512, 130),
        (700, 162),
        (824, 296),
        (872, 470),
        (852, 664),
        (760, 826),
        (620, 926),
        (512, 954),
        (404, 926),
        (264, 826),
        (172, 664),
        (152, 470),
        (200, 296),
        (324, 162),
    ]
    head = c.spline(head_pts)
    c.shadow(head, 0, 12, 16, 0.5, clip=False)
    c.paint(
        head,
        radial((182, 130, 80), (116, 74, 44), (500, 380), 560, 1.1),
        bevel=0.6,
        bevel_radius=30,
        ao=0.45,
        grain=0.05,
        grain_scale=3,
    )
    c.strands(head, 7000, lambda x, y: math.atan2(y - 420, x - 512) + 0.1, (14, 34), fur, 1.5, curl=0.3)
    worn = noise_shape(c, head, 10, 1.0)
    c.paint(worn, (196, 154, 104), opacity=0.35, clip=True)

    muzzle = c.ellipse((512, 724), (208, 178))
    c.shadow(muzzle, 0, 6, 8, 0.4)
    c.paint(
        muzzle,
        radial((240, 220, 176), (204, 172, 124), (500, 690), 230),
        bevel=0.55,
        bevel_radius=20,
        ao=0.3,
        clip=True,
    )
    c.strands(muzzle, 3600, lambda x, y: math.atan2(y - 660, x - 512), (10, 26), cream, 1.4, curl=0.3)

    dashed(
        c,
        [(512, 150), (512, 250), (512, 380), (512, 500)],
        (226, 200, 154),
        18,
        12,
        4.5,
        opacity=0.85,
        clip=True,
    )
    for y in range(180, 520, 30):
        c.paint(c.stroke([(500, y - 5), (524, y + 5)], 3.4), (226, 200, 154), opacity=0.75, clip=True)

    nose = c.spline([(512, 640), (566, 660), (582, 690), (512, 738), (442, 690), (458, 660)], samples=8)
    c.shadow(nose, 0, 4, 4, 0.45)
    c.paint(nose, radial((90, 60, 50), (24, 14, 12), (496, 660), 90), bevel=0.7, bevel_radius=8, ao=0.2)
    for k in range(9):
        y = 652 + k * 9
        c.paint(
            c.stroke([(470 + abs(k - 4) * 4, y), (554 - abs(k - 4) * 4, y)], 2.4),
            (70, 46, 38),
            opacity=0.7,
            clip=True,
        )
    c.paint(c.ellipse((494, 660), (16, 7), angle=-14).blurred(2), (210, 200, 196), opacity=0.5, clip=True)
    dashed(c, [(512, 738), (512, 776), (470, 808), (430, 800)], (60, 36, 28), 14, 5, 6, opacity=0.95)
    dashed(c, [(512, 776), (554, 808), (594, 800)], (60, 36, 28), 14, 5, 6, opacity=0.95)

    for ex, sgn in ((EYE_L[0], -1), (EYE_R[0], 1)):
        rim = c.ellipse((ex, 430), (78, 56))
        c.paint(rim, (52, 32, 22), bevel=0.6, bevel_radius=8, ao=0.2)
        for k in range(24):
            a = k * math.pi / 12
            dashed(
                c,
                [
                    (ex + 70 * math.cos(a), 430 + 49 * math.sin(a)),
                    (ex + 70 * math.cos(a + 0.16), 430 + 49 * math.sin(a + 0.16)),
                ],
                thread,
                10,
                100,
                3.4,
                smooth=False,
                opacity=0.85,
            )
        brow = [(ex - sgn * 60, 340), (ex, 322), (ex + sgn * 60, 334)]
        c.paint(c.stroke(brow, 6), (52, 32, 22), opacity=0.85, clip=True)
        c.erase(c.ellipse((ex, 430), (62, 42)), feather=1.5)

    patch = c.poly([(662, 560), (782, 540), (800, 660), (680, 682)])
    c.shadow(patch, 2, 4, 3, 0.5)
    c.paint(patch, (156, 60, 52), bevel=0.4, bevel_radius=4, clip=True)
    for k in range(6):
        t = k / 5
        c.paint(
            c.stroke([(662 + 18 * t * 5.5, 560 + 122 * t * 0.9), (782 + 18 * t * 0.5, 540 + 120 * t)], 5),
            (232, 200, 150),
            opacity=0.5,
            clip=True,
        )
        c.paint(
            c.stroke([(662 + 24 * k, 560 - 3 * k), (680 + 24 * k, 682 - 3 * k)], 5),
            (232, 200, 150),
            opacity=0.4,
            clip=True,
        )
    dashed(c, [(662, 560), (782, 540), (800, 660), (680, 682), (662, 560)], thread, 12, 8, 3.4, smooth=False)

    bow_c = (512, 978)
    for sgn in (-1, 1):
        wing = c.poly([bow_c, (bow_c[0] + sgn * 96, bow_c[1] - 40), (bow_c[0] + sgn * 96, bow_c[1] + 40)])
        c.paint(
            wing,
            linear((200, 50, 60), (110, 20, 30), (bow_c[0], 0), (bow_c[0] + sgn * 96, 0)),
            bevel=0.6,
            bevel_radius=6,
            ao=0.3,
        )
    c.paint(
        circle(c, bow_c, 24),
        radial((230, 80, 80), (130, 24, 34), (bow_c[0] - 6, bow_c[1] - 6), 30),
        bevel=0.6,
        bevel_radius=5,
    )
    return c.to_bgra()


def dragon() -> np.ndarray:
    c = Canvas(SIZE)
    green_a: Color = (66, 176, 120)
    green_b: Color = (10, 64, 56)
    gold: Color = (240, 190, 70)

    for sgn in (-1, 1):

        def sx(x, s=sgn):
            return x if s == -1 else SIZE - x

        frill = c.poly(
            [
                (sx(190), 470),
                (sx(20), 360),
                (sx(70), 470),
                (sx(0), 560),
                (sx(84), 610),
                (sx(30), 700),
                (sx(170), 690),
            ]
        )
        c.paint(
            frill,
            linear((250, 120, 60), (120, 20, 40), (sx(190), 500), (sx(0), 500)),
            bevel=0.5,
            bevel_radius=10,
            ao=0.4,
            opacity=0.95,
        )
        for k in range(4):
            c.paint(
                c.stroke([(sx(180), 500 + k * 44), (sx(40 + 10 * k), 390 + k * 78)], 4),
                gold,
                opacity=0.8,
                clip=True,
            )
        horn = tapered(c, [(sx(330), 250), (sx(250), 150), (sx(160), 80), (sx(90), 10)], 84, 4)
        c.shadow(horn, 0, 8, 8, 0.4, clip=False)
        c.paint(
            horn,
            linear((255, 248, 226), (150, 120, 84), (sx(340), 250), (sx(90), 10)),
            bevel=0.8,
            bevel_radius=10,
            ao=0.3,
        )
        for t in np.linspace(0.12, 0.85, 8):
            px = sx(330) + (sx(90) - sx(330)) * t
            py = 250 + (10 - 250) * t
            c.paint(
                c.stroke([(px - 40, py + 22 * (1 - t)), (px + 40, py - 22 * (1 - t))], 3),
                (110, 84, 56),
                opacity=0.5,
                clip=True,
            )

    for x, h in ((512, 130), (452, 96), (572, 96), (392, 66), (632, 66)):
        spike = tapered(c, [(x, 170), (x, 150 - h * 0.5), (x + (x - 512) * 0.1, 150 - h)], 52, 2)
        c.paint(
            spike,
            linear((250, 240, 214), (130, 100, 70), (x, 150 - h), (x, 170)),
            bevel=0.7,
            bevel_radius=6,
            ao=0.2,
        )

    head_pts = [
        (512, 112),
        (660, 142),
        (780, 232),
        (840, 360),
        (880, 470),
        (952, 560),
        (890, 604),
        (934, 692),
        (850, 722),
        (800, 822),
        (680, 912),
        (512, 962),
        (344, 912),
        (224, 822),
        (174, 722),
        (90, 692),
        (134, 604),
        (72, 560),
        (144, 470),
        (184, 360),
        (244, 232),
        (364, 142),
    ]
    head = c.spline(head_pts, samples=8)
    c.shadow(head, 0, 12, 16, 0.5, clip=False)
    c.paint(head, radial(green_a, green_b, (512, 420), 520, 1.1), bevel=0.6, bevel_radius=24, ao=0.4)
    for row in range(0, 30):
        y = 110 + row * 30
        for col in range(0, 27):
            x = 70 + col * 36 + (18 if row % 2 else 0)
            if not (60 < x < 964):
                continue
            shade = 0.55 + 0.45 * math.sin(col * 0.8 + row * 0.5) * 0.5 + 0.2 * (1 - row / 30)
            base = tuple(v * shade for v in (70, 170, 110))
            scale = c.ellipse((x, y), (19.5, 17))
            c.paint(
                scale,
                radial(tuple(min(255, v * 1.5) for v in base), base, (x - 5, y - 6), 26),
                bevel=0.9,
                bevel_radius=3.5,
                ao=0.35,
                clip=True,
                opacity=0.96,
            )
    c.paint(head - c.ellipse((512, 470), (340, 420)).blurred(80), (2, 18, 14), opacity=0.6, clip=True)

    for ex, sgn in ((EYE_L[0], -1), (EYE_R[0], 1)):
        brow = tapered(
            c, [(ex - sgn * 92, 372), (ex, 336), (ex + sgn * 100, 352), (ex + sgn * 168, 310)], 58, 8
        )
        c.shadow(brow, 0, 8, 6, 0.5)
        c.paint(
            brow,
            linear((44, 130, 96), (8, 44, 40), (0, 330), (0, 400)),
            bevel=0.9,
            bevel_radius=8,
            ao=0.3,
            clip=True,
        )
        c.paint(
            c.ellipse((ex, 430), (84, 58), angle=sgn * 8),
            linear((250, 210, 100), (120, 70, 20), (ex - 80, 380), (ex + 80, 480)),
            bevel=0.8,
            bevel_radius=6,
        )
        c.paint(c.ellipse((ex, 430), (70, 46), angle=sgn * 8), (20, 8, 6), opacity=0.6)
        c.erase(c.ellipse((ex, 430), (62, 39), angle=sgn * 8), feather=1.5)

    snout = c.ellipse((512, 650), (120, 82))
    c.paint(
        snout,
        radial((110, 210, 150), (26, 100, 78), (500, 630), 140),
        bevel=0.7,
        bevel_radius=14,
        ao=0.3,
        clip=True,
    )
    for nx, sgn in ((472, -1), (552, 1)):
        nostril = c.ellipse((nx, 654), (20, 11), angle=sgn * -25)
        c.paint(
            c.ellipse((nx, 654), (30, 18), angle=sgn * -25).blurred(6),
            (255, 120, 30),
            opacity=0.55,
            clip=True,
        )
        c.paint(nostril, (10, 6, 6), bevel=-0.5, bevel_radius=3)
        c.paint(c.ellipse((nx, 657), (11, 5), angle=sgn * -25), (255, 160, 60), opacity=0.7, clip=True)

    lip = [(390, 738), (450, 770), (512, 782), (574, 770), (634, 738)]
    c.paint(c.stroke(lip, 8), (8, 30, 26), clip=True)
    for i, x in enumerate(np.linspace(408, 616, 8)):
        y = 744 + 40 * (1 - abs(x - 512) / 130) if abs(x - 512) < 130 else 742
        h = 30 if i % 2 == 0 else 20
        fang = tapered(c, [(x, y), (x, y + h * 0.5), (x, y + h)], 15, 1)
        c.paint(fang, linear((255, 252, 240), (200, 190, 160), (x, y), (x, y + h)), bevel=0.5, bevel_radius=2)
    return c.to_bgra()


def alien() -> np.ndarray:
    c = Canvas(SIZE)
    skin_a: Color = (168, 222, 110)
    skin_b: Color = (54, 116, 66)

    for sgn in (-1, 1):

        def sx(x, s=sgn):
            return x if s == -1 else SIZE - x

        stalk = tapered(c, [(sx(410), 120), (sx(370), 60), (sx(320), 26)], 14, 8)
        c.paint(stalk, (90, 150, 80), bevel=0.5, bevel_radius=3)
        c.paint(circle(c, (sx(312), 22), 26).blurred(8), (230, 255, 120), opacity=0.5)
        c.paint(
            circle(c, (sx(312), 22), 17),
            radial((250, 255, 200), (120, 200, 60), (sx(306), 16), 22),
            bevel=0.4,
            bevel_radius=3,
        )
        ear = c.poly([(sx(210), 420), (sx(40), 350), (sx(30), 470), (sx(90), 610), (sx(200), 640)])
        c.paint(
            ear,
            linear((150, 206, 110), (60, 120, 70), (sx(200), 500), (sx(30), 500)),
            bevel=0.6,
            bevel_radius=12,
            ao=0.35,
        )
        c.paint(
            c.poly([(sx(190), 470), (sx(76), 410), (sx(76), 490), (sx(120), 580), (sx(186), 590)]),
            (90, 150, 80),
            bevel=-0.5,
            bevel_radius=8,
            opacity=0.7,
        )

    head_pts = [
        (512, 50),
        (690, 92),
        (816, 226),
        (856, 400),
        (838, 566),
        (782, 742),
        (680, 884),
        (512, 966),
        (344, 884),
        (242, 742),
        (186, 566),
        (168, 400),
        (208, 226),
        (334, 92),
    ]
    head = c.spline(head_pts)
    c.shadow(head, 0, 12, 18, 0.5, clip=False)
    c.paint(
        head,
        radial(skin_a, skin_b, (490, 360), 560, 1.15),
        bevel=0.7,
        bevel_radius=34,
        ao=0.45,
        grain=0.05,
        grain_scale=2.5,
    )
    for _ in range(420):
        x = c.rng.uniform(190, 830)
        y = c.rng.uniform(80, 950)
        r = c.rng.uniform(2.5, 7)
        c.paint(
            c.ellipse((x, y), (r, r * 0.85)),
            (60, 110, 60),
            opacity=0.35,
            bevel=0.5,
            bevel_radius=1.5,
            clip=True,
        )
    for sgn in (-1, 1):
        for k in range(4):
            vein = c.stroke(
                [
                    (512 + sgn * (150 + k * 30), 250 + k * 40),
                    (512 + sgn * (250 + k * 24), 290 + k * 60),
                    (512 + sgn * (300 + k * 18), 360 + k * 72),
                ],
                2.4,
            )
            c.paint(vein, (44, 100, 80), opacity=0.5, clip=True)
    for k in range(3):
        c.paint(
            c.stroke([(400, 190 + k * 22), (512, 178 + k * 22), (624, 190 + k * 22)], 3),
            (60, 116, 70),
            opacity=0.55,
            clip=True,
        )

    eye_c = (512, 420)
    socket = c.ellipse(eye_c, (250, 168))
    c.paint(socket.blurred(20), (20, 60, 40), opacity=0.6, clip=True)
    eyeball = c.ellipse(eye_c, (222, 138))
    c.paint(
        eyeball,
        radial((250, 246, 214), (196, 176, 108), (500, 396), 250, 0.75),
        bevel=0.4,
        bevel_radius=22,
        ao=0.6,
    )
    for k in range(18):
        a = c.rng.uniform(0, 2 * math.pi)
        r0 = c.rng.uniform(120, 160)
        pts = [
            (512 + r0 * math.cos(a), 420 + r0 * 0.66 * math.sin(a)),
            (512 + (r0 - 40) * math.cos(a + 0.08), 420 + (r0 - 40) * 0.66 * math.sin(a + 0.08)),
            (512 + (r0 - 84) * math.cos(a), 420 + (r0 - 84) * 0.66 * math.sin(a)),
        ]
        c.paint(c.stroke(pts, 1.8), (190, 50, 50), opacity=0.5, clip=True)
    iris = circle(c, eye_c, 98)
    c.paint(iris, radial((255, 220, 60), (150, 30, 10), eye_c, 100), bevel=0.3, bevel_radius=10)
    c.paint(ring(c, eye_c, 98, 86), (90, 20, 6), opacity=0.7)
    for k in range(36):
        a = k * math.pi / 18
        c.paint(
            c.stroke(
                [
                    (512 + 42 * math.cos(a), 420 + 42 * math.sin(a)),
                    (512 + 86 * math.cos(a), 420 + 86 * math.sin(a)),
                ],
                2,
            ),
            (255, 230, 120),
            opacity=0.35,
            clip=True,
        )
    pupil = c.ellipse(eye_c, (22, 66))
    c.paint(pupil, (4, 4, 6), bevel=-0.4, bevel_radius=6)
    c.paint(c.ellipse((470, 372), (30, 20), angle=-30).blurred(2), (255, 255, 255), opacity=0.92, clip=False)
    c.paint(c.ellipse((560, 470), (14, 8), angle=-30).blurred(2), (255, 255, 255), opacity=0.5, clip=False)
    upper = c.spline(
        [(276, 400), (360, 296), (512, 262), (664, 296), (748, 400), (664, 330), (512, 300), (360, 330)]
    )
    c.paint(
        upper,
        linear((120, 176, 90), (56, 112, 66), (0, 260), (0, 400)),
        bevel=0.8,
        bevel_radius=12,
        ao=0.3,
        clip=True,
    )
    lower = c.spline(
        [(290, 450), (400, 552), (512, 566), (624, 552), (734, 450), (640, 520), (512, 534), (384, 520)]
    )
    c.paint(
        lower,
        linear((100, 160, 84), (60, 116, 70), (0, 470), (0, 566)),
        bevel=0.6,
        bevel_radius=10,
        ao=0.25,
        clip=True,
    )

    for nx in (490, 534):
        c.paint(
            c.ellipse((nx, 652), (5, 12), angle=(-1 if nx < 512 else 1) * -12),
            (24, 60, 40),
            bevel=-0.5,
            bevel_radius=2,
            clip=True,
        )
    mouth = c.stroke([(410, 770), (462, 782), (512, 786), (562, 782), (614, 770)], 5)
    c.paint(mouth, (30, 70, 44), clip=True)
    c.paint(
        c.stroke([(410, 776), (462, 788), (512, 792), (562, 788), (614, 776)], 3),
        (190, 240, 150),
        opacity=0.4,
        clip=True,
    )
    return c.to_bgra()


def cat_astronaut() -> np.ndarray:
    c = Canvas(SIZE)
    fur: Color = (150, 160, 178)
    center = (512, 520)

    for sgn in (-1, 1):

        def sx(x, s=sgn):
            return x if s == -1 else SIZE - x

        ear = c.poly([(sx(150), 300), (sx(140), 30), (sx(380), 150)])
        c.shadow(ear, 0, 6, 8, 0.4, clip=False)
        c.paint(
            ear,
            linear((176, 186, 204), (110, 120, 140), (sx(150), 40), (sx(300), 300)),
            bevel=0.6,
            bevel_radius=10,
            ao=0.3,
        )
        inner = c.poly([(sx(190), 260), (sx(176), 84), (sx(330), 168)])
        c.paint(
            inner,
            linear((250, 190, 200), (200, 110, 130), (sx(180), 100), (sx(260), 260)),
            bevel=-0.4,
            bevel_radius=8,
        )
        c.strands(
            ear,
            500,
            lambda x, y: math.atan2(-1, 0.3 * sgn),
            (14, 34),
            [fur, (190, 198, 214), (120, 130, 150)],
            1.1,
        )

    collar = c.poly(rrect(290, 890, 734, 1018, 38))
    c.paint(
        collar, linear((150, 156, 170), (70, 74, 88), (0, 890), (0, 1018)), bevel=0.6, bevel_radius=8, ao=0.3
    )
    for k in range(9):
        x = 320 + k * 46
        c.paint(c.stroke([(x, 900), (x - 6, 1010)], 4), (50, 54, 66), opacity=0.7, clip=True)

    helmet = ring(c, center, 470, 394)
    c.shadow(circle(c, center, 470), 0, 12, 16, 0.5, clip=False)
    c.paint(
        helmet,
        linear((255, 255, 255), (150, 160, 178), (200, 60), (820, 980)),
        bevel=0.9,
        bevel_radius=26,
        ao=0.3,
        grain=0.02,
    )
    c.paint(ring(c, center, 401, 394), (60, 70, 96), opacity=0.55)
    c.paint(ring(c, center, 466, 460), (255, 255, 255), opacity=0.4)

    for sgn in (-1, 1):
        px = 512 + sgn * 466
        pod = (
            c.poly(rrect(px - 34, 440, px + 34, 600, 22))
            if False
            else c.poly(rrect(512 + sgn * 442 - 32, 450, 512 + sgn * 442 + 32, 590, 22))
        )
        c.paint(
            pod,
            linear((210, 216, 228), (100, 108, 126), (0, 450), (0, 590)),
            bevel=0.7,
            bevel_radius=6,
            ao=0.3,
            clip=False,
        )
        c.paint(circle(c, (512 + sgn * 442, 520), 9), (255, 90, 70), bevel=0.4, bevel_radius=3)

    glass = circle(c, center, 396)
    c.paint(glass, radial((170, 210, 255), (60, 110, 190), center, 396), opacity=0.09)
    crescent = c.ellipse(center, (382, 382)) - c.ellipse((566, 580), (382, 382))
    c.paint(crescent.blurred(5), (255, 255, 255), opacity=0.24, clip=False)
    c.paint(c.ellipse((300, 250), (62, 26), angle=-42).blurred(6), (255, 255, 255), opacity=0.5, clip=False)
    c.paint(c.ellipse((760, 820), (110, 16), angle=-38).blurred(8), (200, 230, 255), opacity=0.25, clip=False)

    for k, dy in enumerate((-30, 0, 30)):
        stripe = tapered(c, [(512 + dy * 1.6, 200), (512 + dy * 1.2, 230), (512 + dy * 1.0, 262)], 14, 3)
        c.paint(stripe.blurred(1.5), (70, 76, 96), opacity=0.55, clip=False)

    for sgn in (-1, 1):
        for k in range(3):
            y0 = 646 + k * 24
            whisker = c.stroke(
                [
                    (512 + sgn * 74, y0),
                    (512 + sgn * 210, y0 + (k - 1) * 30 - 10),
                    (512 + sgn * 340, y0 + (k - 1) * 58 - 16),
                ],
                3,
            )
            c.paint(whisker, (250, 252, 255), opacity=0.9, clip=False)
    nose = c.spline([(512, 632), (540, 598), (484, 598)], samples=8)
    c.shadow(nose, 0, 4, 3, 0.4, clip=False)
    c.paint(nose, radial((255, 200, 210), (210, 100, 130), (504, 606), 46), bevel=0.6, bevel_radius=4)
    c.paint(c.stroke([(512, 632), (512, 656)], 5), (150, 70, 90), clip=False)
    c.paint(c.stroke([(512, 656), (486, 680), (452, 672)], 5), (150, 70, 90), clip=False)
    c.paint(c.stroke([(512, 656), (538, 680), (572, 672)], 5), (150, 70, 90), clip=False)

    patch_c = (214, 826)
    c.paint(circle(c, patch_c, 40), (24, 46, 130), bevel=0.6, bevel_radius=5)
    c.paint(ring(c, patch_c, 40, 33), (240, 60, 60), bevel=0.4, bevel_radius=3)
    c.paint(c.ellipse((patch_c[0], patch_c[1] + 8), (13, 10)), (255, 255, 255))
    for dx, dy in ((-16, -7), (-6, -16), (6, -16), (16, -7)):
        c.paint(c.ellipse((patch_c[0] + dx, patch_c[1] + dy), (5, 6.5)), (255, 255, 255))
    c.paint(
        tapered(c, [(800, 180), (842, 110), (856, 70)], 12, 8), (200, 206, 216), bevel=0.6, bevel_radius=3
    )
    c.paint(circle(c, (858, 62), 16).blurred(6), (255, 70, 60), opacity=0.5)
    c.paint(
        circle(c, (858, 62), 11),
        radial((255, 190, 170), (220, 30, 30), (854, 58), 14),
        bevel=0.4,
        bevel_radius=3,
    )
    return c.to_bgra()


def phoenix() -> np.ndarray:
    c = Canvas(SIZE)
    fire_a: Color = (255, 150, 40)
    fire_b: Color = (200, 30, 20)
    gold: Color = (255, 205, 90)

    for sgn in (-1, 1):

        def sx(x, s=sgn):
            return x if s == -1 else SIZE - x

        plume = c.poly(
            [
                (sx(230), 420),
                (sx(30), 210),
                (sx(70), 120),
                (sx(160), 40),
                (sx(190), 130),
                (sx(260), 60),
                (sx(300), 160),
                (sx(360), 110),
                (sx(370), 230),
                (sx(300), 330),
            ]
        )
        c.shadow(plume, 0, 8, 10, 0.4, clip=False)
        c.paint(plume, linear(gold, fire_a, (sx(360), 60), (sx(70), 330)), bevel=0.5, bevel_radius=10, ao=0.3)
        c.strands(
            plume,
            2200,
            lambda x, y, s=sgn: math.atan2(y - 260, (x - 512) * s * -1),
            (26, 70),
            [fire_a, gold, fire_b],
            1.6,
            curl=0.1,
        )

    head_pts = [
        (512, 130),
        (660, 168),
        (770, 280),
        (820, 430),
        (798, 590),
        (900, 560),
        (846, 660),
        (874, 760),
        (780, 780),
        (742, 890),
        (630, 960),
        (512, 984),
        (394, 960),
        (282, 890),
        (244, 780),
        (150, 760),
        (178, 660),
        (124, 560),
        (226, 590),
        (204, 430),
        (254, 280),
        (364, 168),
    ]
    head = c.spline(head_pts, samples=8)
    c.shadow(head, 0, 12, 16, 0.5, clip=False)
    c.paint(head, radial((255, 224, 160), fire_b, (500, 420), 560, 1.1), bevel=0.6, bevel_radius=26, ao=0.4)
    c.strands(
        head,
        6000,
        lambda x, y: math.atan2(y - 420, x - 512),
        (14, 30),
        [fire_a, gold, (170, 30, 20)],
        1.3,
        curl=0.15,
    )

    crest = c.poly([(512, 150), (478, 90), (512, 60), (546, 90)])
    c.paint(crest, gold, bevel=0.6, bevel_radius=4, clip=True)

    beak = c.spline([(512, 640), (600, 660), (620, 700), (512, 780), (404, 700), (424, 660)], samples=8)
    c.shadow(beak, 0, 5, 5, 0.5, clip=False)
    c.paint(
        beak,
        linear((255, 214, 120), (200, 140, 30), (420, 640), (600, 780)),
        bevel=0.7,
        bevel_radius=8,
        ao=0.25,
    )
    c.paint(c.stroke([(512, 700), (512, 660)], 3), (140, 90, 20), opacity=0.6, clip=True)

    for ex, sgn in ((EYE_L[0], -1), (EYE_R[0], 1)):
        brow = c.spline([(ex - sgn * 90, 360), (ex, 322), (ex + sgn * 100, 340), (ex + sgn * 150, 300)])
        c.paint(brow, linear(gold, fire_a, (0, 320), (0, 380)), bevel=0.7, bevel_radius=6, clip=True)
        c.paint(
            ring(c, (ex, 430), 92, 70),
            linear((90, 30, 16), (40, 10, 8), (ex - 80, 380), (ex + 80, 480)),
            bevel=0.6,
            bevel_radius=8,
            clip=True,
        )
        c.erase(circle(c, (ex, 430), 68), feather=2)

    NOSE
    return c.to_bgra()


def tribal_wolf() -> np.ndarray:
    c = Canvas(SIZE)
    wood: Color = (92, 60, 38)
    bone: Color = (232, 218, 188)
    red: Color = (168, 34, 30)

    head_pts = [
        (512, 110),
        (668, 150),
        (780, 260),
        (842, 420),
        (820, 560),
        (886, 600),
        (826, 680),
        (852, 800),
        (760, 830),
        (706, 930),
        (600, 984),
        (512, 1000),
        (424, 984),
        (318, 930),
        (264, 830),
        (172, 800),
        (198, 680),
        (138, 600),
        (204, 560),
        (182, 420),
        (244, 260),
        (356, 150),
    ]
    head = c.spline(head_pts, samples=8)
    c.shadow(head, 0, 14, 16, 0.55, clip=False)
    c.paint(
        head,
        radial((150, 100, 64), (58, 36, 22), (490, 420), 560, 1.1),
        bevel=0.6,
        bevel_radius=24,
        ao=0.45,
        grain=0.08,
        grain_scale=4,
    )
    c.paint(head - c.spline(head_pts, samples=8).blurred(60), (30, 18, 12), opacity=0.5, clip=True)

    for sgn in (-1, 1):
        ear = c.poly([(512 + sgn * 140, 210), (512 + sgn * 90, 30), (512 + sgn * 260, 130)])
        c.paint(
            ear,
            linear(wood, (50, 30, 18), (512, 30), (512 + sgn * 260, 210)),
            bevel=0.6,
            bevel_radius=8,
            ao=0.3,
        )
        c.paint(
            c.poly([(512 + sgn * 150, 190), (512 + sgn * 116, 70), (512 + sgn * 220, 140)]),
            (60, 30, 20),
            opacity=0.6,
            clip=True,
        )

    for x, y in [(430, 780), (512, 800), (594, 780)]:
        fang = c.poly([(x - 18, y), (x + 18, y), (x, y + 56)])
        c.paint(fang, bone, bevel=0.5, bevel_radius=4, clip=True)

    for ex, sgn in ((EYE_L[0], -1), (EYE_R[0], 1)):
        mark = c.poly(
            [
                (ex - sgn * 120, 340),
                (ex + sgn * 60, 300),
                (ex + sgn * 150, 400),
                (ex - sgn * 10, 520),
                (ex - sgn * 130, 480),
            ]
        )
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
