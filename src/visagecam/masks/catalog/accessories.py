# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from visagecam.masks.painter import Canvas, Color, catmull_rom, linear, radial
from visagecam.masks.shapes import circle, ring, rrect

SIZE = 1024


@dataclass(frozen=True)
class AccessorySpec:
    name: str
    slot: str
    builder: Callable[[], np.ndarray]
    pivot: tuple[float, float] | None = None
    width_ratio: float | None = None


def top_hat() -> np.ndarray:
    c = Canvas(SIZE)
    brim = c.ellipse((512, 800), (440, 78))
    c.shadow(brim, 0, 14, 16, 0.5, clip=False)
    c.paint(
        brim, linear((58, 58, 64), (18, 18, 22), (512, 720), (512, 880)), bevel=0.5, bevel_radius=14, ao=0.35
    )
    c.paint(c.ellipse((512, 792), (300, 42)).blurred(10), (0, 0, 0), opacity=0.55, clip=True)

    body = c.poly([(300, 220), (724, 220), (742, 792), (282, 792)]) + c.ellipse((512, 792), (230, 50))
    c.paint(
        body,
        linear((14, 14, 18), (78, 78, 86), (282, 0), (742, 0)),
        bevel=0.35,
        bevel_radius=16,
        ao=0.3,
        grain=0.05,
    )
    c.paint(
        c.poly([(360, 240), (400, 240), (410, 790), (350, 790)]).blurred(14),
        (220, 222, 232),
        opacity=0.22,
        clip=True,
    )
    c.paint(
        c.poly([(660, 240), (690, 240), (700, 790), (670, 790)]).blurred(12),
        (150, 152, 170),
        opacity=0.14,
        clip=True,
    )

    band = c.poly([(288, 690), (736, 690), (740, 772), (284, 772)]) + c.ellipse((512, 772), (228, 44))
    band = band - c.ellipse((512, 690), (230, 46))
    band = band + c.ellipse((512, 690), (0.1, 0.1))
    c.paint(
        band,
        linear((150, 26, 44), (86, 10, 24), (512, 690), (512, 800)),
        bevel=0.5,
        bevel_radius=8,
        ao=0.3,
        clip=True,
    )
    buckle = c.poly([(470, 700), (554, 700), (554, 780), (470, 780)])
    c.paint(
        buckle - c.poly([(486, 716), (538, 716), (538, 764), (486, 764)]),
        linear((250, 220, 130), (150, 110, 40), (470, 700), (554, 780)),
        bevel=0.8,
        bevel_radius=4,
        clip=True,
    )

    top = c.ellipse((512, 220), (212, 44))
    c.paint(
        top, linear((84, 84, 92), (30, 30, 36), (300, 190), (724, 250)), bevel=0.4, bevel_radius=10, ao=0.3
    )
    c.paint(c.ellipse((470, 214), (110, 12)).blurred(8), (255, 255, 255), opacity=0.2, clip=True)
    return c.to_bgra()


def party_hat() -> np.ndarray:
    c = Canvas(SIZE)
    cone = c.poly([(512, 90), (300, 880), (724, 880)]) + c.ellipse((512, 880), (212, 40))
    c.shadow(cone, 6, 10, 12, 0.4, clip=False)
    c.paint(
        cone, linear((255, 90, 150), (200, 40, 110), (300, 0), (724, 0)), bevel=0.5, bevel_radius=22, ao=0.3
    )
    colors = [(255, 214, 70), (60, 190, 240), (255, 255, 255)]
    for i in range(7):
        y0 = 190 + i * 96
        stripe = c.poly([(200, y0 + 110), (824, y0 - 60), (824, y0 - 20), (200, y0 + 150)])
        c.paint(stripe, colors[i % 3], opacity=0.88, clip=True)
    c.paint(cone, linear((255, 255, 255), (0, 0, 0), (300, 0), (724, 0)), opacity=0.0)
    c.paint(
        c.poly([(480, 120), (520, 120), (400, 880), (340, 880)]).blurred(20),
        (255, 255, 255),
        opacity=0.22,
        clip=True,
    )
    c.paint(
        c.poly([(560, 200), (600, 200), (680, 880), (640, 880)]).blurred(18),
        (60, 0, 30),
        opacity=0.25,
        clip=True,
    )
    rim = c.stroke([(300, 880), (400, 916), (512, 924), (624, 916), (724, 880)], 16)
    c.paint(rim, (255, 214, 70), bevel=0.6, bevel_radius=5)
    ball = c.ellipse((512, 74), (58, 58))
    c.paint(ball, radial((255, 250, 200), (250, 190, 40), (490, 52), 70), bevel=0.4, bevel_radius=8)
    c.strands(
        ball,
        900,
        lambda x, y: math.atan2(y - 74, x - 512),
        (10, 30),
        [(255, 224, 90), (255, 250, 200), (250, 180, 30)],
        1.6,
    )
    return c.to_bgra()


def crown() -> np.ndarray:
    c = Canvas(SIZE)
    gold_a: Color = (255, 226, 120)
    gold_b: Color = (176, 118, 28)
    body = c.poly(
        [
            (250, 830),
            (232, 330),
            (382, 540),
            (512, 250),
            (642, 540),
            (792, 330),
            (774, 830),
        ]
    )
    c.shadow(body, 0, 12, 14, 0.45, clip=False)
    c.paint(
        body, linear(gold_a, gold_b, (300, 260), (700, 840)), bevel=0.7, bevel_radius=14, ao=0.3, streak=0.1
    )
    inner = c.poly([(300, 760), (300, 470), (382, 610), (512, 380), (642, 610), (724, 470), (724, 760)])
    c.paint(inner, (120, 20, 40), opacity=0.5, clip=True)
    for cx, cy in ((232, 330), (512, 250), (792, 330)):
        orb = c.ellipse((cx, cy), (36, 36))
        c.shadow(orb, 2, 5, 4, 0.5, clip=False)
        c.paint(
            orb, radial((255, 246, 190), (190, 128, 30), (cx - 10, cy - 12), 46), bevel=0.4, bevel_radius=5
        )
    band = c.poly([(240, 700), (784, 700), (774, 830), (250, 830)])
    c.paint(
        band, linear((255, 214, 100), (150, 96, 20), (0, 700), (0, 830)), bevel=0.8, bevel_radius=6, clip=True
    )
    gems = [
        ((512, 766), (200, 20, 50)),
        ((392, 766), (40, 110, 220)),
        ((632, 766), (40, 110, 220)),
        ((312, 766), (30, 170, 90)),
        ((712, 766), (30, 170, 90)),
    ]
    for (gx, gy), color in gems:
        seat = c.ellipse((gx, gy), (32, 32))
        c.paint(seat, (120, 80, 20), bevel=-0.6, bevel_radius=4)
        gem = c.ellipse((gx, gy), (24, 24))
        c.paint(
            gem,
            radial(tuple(min(255, v + 90) for v in color), color, (gx - 8, gy - 8), 32),
            bevel=0.6,
            bevel_radius=5,
        )
        c.paint(c.ellipse((gx - 8, gy - 9), (7, 5)).blurred(1), (255, 255, 255), opacity=0.8, clip=True)
    return c.to_bgra()


def sunglasses() -> np.ndarray:
    c = Canvas(SIZE)
    dark: Color = (18, 18, 22)
    lens_l = [(90, 330), (130, 300), (400, 300), (440, 340), (420, 470), (360, 530), (200, 530), (110, 470)]
    lens_r = [(SIZE - x, y) for x, y in lens_l]
    arms = c.stroke([(80, 335), (20, 330)], 22) + c.stroke([(SIZE - 80, 335), (SIZE - 20, 330)], 22)
    c.paint(arms, dark, bevel=0.5, bevel_radius=6)
    bridge = c.stroke([(430, 350), (512, 328), (594, 350)], 30)
    c.paint(bridge, dark, bevel=0.6, bevel_radius=6)
    for pts in (lens_l, lens_r):
        frame = c.spline(pts)
        c.shadow(frame, 0, 8, 8, 0.4, clip=False)
        c.paint(frame, dark, bevel=0.7, bevel_radius=8, ao=0.2)
    for pts in (lens_l, lens_r):
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        inner = [(cx + (x - cx) * 0.86, cy + (y - cy) * 0.82) for x, y in pts]
        lens = c.spline(inner)
        c.paint(
            lens,
            linear((40, 60, 90), (8, 12, 22), (0, 300), (0, 520)),
            opacity=0.86,
            bevel=-0.4,
            bevel_radius=8,
        )
        glare = c.poly(
            [(cx - 90, cy - 70), (cx - 30, cy - 70), (cx - 110, cy + 60), (cx - 150, cy + 60)]
        ).blurred(3)
        c.paint(glare, (255, 255, 255), opacity=0.32, clip=True)
        c.paint(c.ellipse((cx + 40, cy + 40), (60, 20)).blurred(10), (140, 180, 255), opacity=0.16, clip=True)
    return c.to_bgra()


def mustache() -> np.ndarray:
    c = Canvas(SIZE)
    half = [
        (512, 300),
        (596, 278),
        (690, 286),
        (780, 262),
        (852, 206),
        (884, 148),
        (900, 170),
        (896, 232),
        (846, 306),
        (760, 356),
        (650, 376),
        (560, 372),
        (512, 392),
    ]
    right = c.spline(half)
    left = c.spline([(SIZE - x, y) for x, y in half])
    shape = right + left
    c.shadow(shape, 0, 8, 8, 0.35, clip=False)
    c.paint(
        shape, linear((68, 42, 26), (30, 16, 10), (0, 260), (0, 390)), bevel=0.5, bevel_radius=10, ao=0.35
    )
    dark = [(24, 12, 8), (44, 26, 16), (62, 38, 24), (84, 56, 36)]
    c.strands(
        right,
        2600,
        lambda x, y: math.atan2(0.15 * (y - 330) + 0.04 * (x - 512) * -1, 1),
        (26, 64),
        dark,
        1.5,
        curl=0.12,
    )
    c.strands(
        left,
        2600,
        lambda x, y: math.atan2(0.15 * (y - 330) + 0.04 * (x - 512), -1),
        (26, 64),
        dark,
        1.5,
        curl=-0.12,
    )
    return c.to_bgra()


def headphones() -> np.ndarray:
    c = Canvas(SIZE)
    angles = np.linspace(math.pi, 2 * math.pi, 40)
    arc = [(512 + 396 * math.cos(a), 600 + 470 * math.sin(a)) for a in angles]
    band = c.stroke(arc, 54, smooth=False)
    c.shadow(band, 0, 10, 10, 0.4, clip=False)
    c.paint(band, linear((70, 74, 84), (20, 22, 28), (0, 130), (0, 320)), bevel=0.7, bevel_radius=10, ao=0.2)
    cushion_arc = [
        (512 + 380 * math.cos(a), 600 + 452 * math.sin(a))
        for a in np.linspace(math.pi * 1.22, math.pi * 1.78, 24)
    ]
    c.paint(c.stroke(cushion_arc, 34, smooth=False), (230, 90, 60), bevel=0.5, bevel_radius=8, clip=True)
    for cx, sgn in ((104, 1), (SIZE - 104, -1)):
        cup = c.ellipse((cx, 610), (96, 142))
        c.shadow(cup, sgn * 4, 12, 12, 0.5, clip=False)
        c.paint(
            cup,
            linear((72, 76, 88), (16, 18, 24), (cx - 90, 500), (cx + 90, 740)),
            bevel=0.8,
            bevel_radius=16,
            ao=0.3,
        )
        c.paint(
            c.ellipse((cx - sgn * 6, 610), (58, 92)),
            radial((60, 200, 230), (10, 90, 130), (cx - 20, 570), 110, 1.2),
            bevel=0.6,
            bevel_radius=8,
        )
        c.paint(c.ellipse((cx - sgn * 8, 566), (26, 30)).blurred(6), (255, 255, 255), opacity=0.35, clip=True)
        pad = c.ellipse((cx + sgn * 62, 610), (34, 118))
        c.paint(
            pad, linear((60, 42, 40), (24, 16, 16), (cx, 500), (cx, 740)), bevel=0.6, bevel_radius=10, ao=0.4
        )
    return c.to_bgra()


def beanie() -> np.ndarray:
    c = Canvas(SIZE)
    dome = c.ellipse((512, 420), (330, 300))
    c.shadow(dome, 0, 10, 12, 0.45, clip=False)
    c.paint(
        dome,
        radial((150, 60, 70), (70, 24, 34), (430, 320), 380, 1.1),
        bevel=0.55,
        bevel_radius=18,
        ao=0.35,
        streak=0.1,
    )
    c.strands(
        dome,
        2600,
        lambda x, y: math.atan2(y - 420, x - 512),
        (14, 30),
        [(190, 80, 90), (120, 44, 54), (70, 24, 34)],
        1.3,
    )
    cuff = c.poly(rrect(198, 540, 826, 680, 40))
    c.paint(
        cuff, linear((130, 50, 60), (60, 20, 28), (198, 540), (826, 680)), bevel=0.6, bevel_radius=10, ao=0.3
    )
    for y in range(556, 664, 18):
        c.paint(c.stroke([(214, y), (810, y)], 5), (40, 14, 20), opacity=0.5, clip=True)
    pom = circle(c, (512, 150), 58)
    c.paint(pom, radial((230, 230, 232), (170, 170, 176), (496, 134), 60), bevel=0.4, bevel_radius=8)
    c.strands(
        pom, 900, lambda x, y: math.atan2(y - 150, x - 512), (10, 30), [(255, 255, 255), (210, 210, 214)], 1.6
    )
    return c.to_bgra()


def flower_crown() -> np.ndarray:
    c = Canvas(SIZE)
    petal_colors = [(235, 150, 190), (250, 200, 120), (200, 140, 230), (150, 200, 240)]
    band = c.stroke([(190, 600), (350, 520), (512, 500), (674, 520), (834, 600)], 26)
    c.paint(band, linear((110, 150, 70), (60, 96, 40), (190, 500), (834, 600)), bevel=0.6, bevel_radius=6)
    positions = [(230, 574), (350, 508), (460, 480), (512, 470), (564, 480), (674, 508), (794, 574)]
    for i, (px, py) in enumerate(positions):
        color = petal_colors[i % len(petal_colors)]
        for k in range(6):
            a = k * math.pi / 3
            petal = c.ellipse(
                (px + 26 * math.cos(a), py + 26 * math.sin(a) * 0.8), (22, 14), angle=math.degrees(a)
            )
            c.paint(
                petal,
                radial(tuple(min(255, v + 30) for v in color), color, (px, py), 30),
                bevel=0.4,
                bevel_radius=4,
            )
        c.paint(
            circle(c, (px, py), 14),
            radial((255, 235, 150), (220, 180, 60), (px - 4, py - 4), 16),
            bevel=0.5,
            bevel_radius=3,
        )
    for lx, ly in [(280, 560), (420, 500), (600, 500), (740, 560)]:
        leaf = c.ellipse((lx, ly + 34), (12, 26), angle=20)
        c.paint(
            leaf, linear((120, 170, 80), (70, 110, 46), (lx, ly), (lx, ly + 60)), bevel=0.4, bevel_radius=3
        )
    return c.to_bgra()


def monocle() -> np.ndarray:
    c = Canvas(SIZE)
    gold: Color = (220, 180, 90)
    ring1 = ring(c, (560, 430), 96, 80)
    c.shadow(ring(c, (560, 430), 96, 0), 0, 5, 6, 0.4, clip=False)
    c.paint(ring1, linear((250, 220, 150), (150, 110, 40), (470, 340), (650, 520)), bevel=0.8, bevel_radius=8)
    c.paint(circle(c, (560, 430), 78), radial((220, 236, 245), (160, 190, 205), (540, 410), 90), opacity=0.25)
    c.paint(c.ellipse((534, 402), (22, 12), angle=-30).blurred(3), (255, 255, 255), opacity=0.55, clip=True)
    chain = catmull_rom([(636, 470), (700, 560), (680, 680), (560, 760)], False, 14)
    c.paint(c.stroke(chain, 6), gold, bevel=0.6, bevel_radius=2)
    for t in range(0, len(chain), 6):
        c.paint(circle(c, tuple(chain[t]), 7), gold, bevel=0.5, bevel_radius=2)
    return c.to_bgra()


def bandana() -> np.ndarray:
    c = Canvas(SIZE)
    red: Color = (190, 40, 40)
    band = c.poly(rrect(170, 300, 854, 560, 40))
    c.shadow(band, 0, 8, 10, 0.45, clip=False)
    c.paint(
        band,
        linear((215, 60, 60), (140, 24, 24), (170, 300), (854, 560)),
        bevel=0.55,
        bevel_radius=12,
        ao=0.3,
    )
    for row in range(4):
        for col in range(9):
            x = 210 + col * 82 + (20 if row % 2 else 0)
            y = 340 + row * 56
            if not (190 < x < 840 and 310 < y < 550):
                continue
            c.paint(c.ellipse((x, y), (12, 12)), (255, 255, 255), opacity=0.85, clip=True)
    for sgn in (-1, 1):
        tail = c.poly([(512 + sgn * 320, 420), (512 + sgn * 420, 470), (512 + sgn * 320, 520)])
        c.paint(tail, red, bevel=0.5, bevel_radius=6, clip=False)
    return c.to_bgra()


ACCESSORIES: dict[str, AccessorySpec] = {
    "top_hat": AccessorySpec("Sombrero de copa", "head", top_hat, width_ratio=1.3),
    "party_hat": AccessorySpec("Gorro de fiesta", "head", party_hat, width_ratio=0.62),
    "crown": AccessorySpec("Corona", "head", crown, width_ratio=0.95),
    "beanie": AccessorySpec("Gorro de lana", "head", beanie, width_ratio=1.05),
    "flower_crown": AccessorySpec("Corona de flores", "head", flower_crown, width_ratio=1.15),
    "sunglasses": AccessorySpec("Gafas de sol", "eyes", sunglasses, pivot=(512, 415), width_ratio=1.0),
    "monocle": AccessorySpec("Monoculo", "eyes", monocle, pivot=(560, 430), width_ratio=0.5),
    "mustache": AccessorySpec("Bigote", "mouth", mustache, pivot=(512, 335), width_ratio=0.62),
    "bandana": AccessorySpec("Panuelo", "mouth", bandana, pivot=(512, 430), width_ratio=1.1),
    "headphones": AccessorySpec("Auriculares", "ears", headphones, pivot=(512, 610), width_ratio=1.32),
}
