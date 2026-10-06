# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

import math

import numpy as np

from visagecam.masks.geometry import EYE_L, EYE_R, SIZE
from visagecam.masks.painter import Canvas, Color, catmull_rom, linear, radial
from visagecam.masks.shapes import circle, ring


def _eye_holes(c: Canvas, widen: float = 1.0):
    left = c.ellipse(EYE_L, (78 * widen, 56 * widen), angle=-6)
    right = c.ellipse(EYE_R, (78 * widen, 56 * widen), angle=6)
    return left, right


def _base_shape(c: Canvas, brow: float = 236, cheek: float = 560, flare: float = 40):
    pts = [
        (512, brow - 30),
        (512 + 170, brow),
        (512 + 260, brow + 40),
        (512 + 300, 380),
        (512 + 300 + flare, 470),
        (512 + 210, cheek),
        (512 + 70, cheek - 40),
        (512, cheek - 70),
        (512 - 70, cheek - 40),
        (512 - 210, cheek),
        (512 - 300 - flare, 470),
        (512 - 300, 380),
        (512 - 260, brow + 40),
        (512 - 170, brow),
    ]
    return c.spline(pts, samples=10)


def venetian_gold() -> np.ndarray:
    c = Canvas(SIZE)
    gold: Color = (222, 182, 96)
    deep: Color = (120, 84, 28)
    shape = _base_shape(c)
    left, right = _eye_holes(c)
    body = shape - left - right
    c.shadow(body, 0, 10, 12, 0.5, clip=False)
    c.paint(
        body,
        radial((248, 214, 140), deep, (512, 400), 420, 1.2),
        bevel=0.8,
        bevel_radius=16,
        ao=0.35,
        streak=0.1,
    )
    for cx, sgn in ((EYE_L[0], -1), (EYE_R[0], 1)):
        c.paint(
            ring(c, (cx, 430), 100, 90),
            linear(gold, deep, (cx - 90, 360), (cx + 90, 500)),
            bevel=0.9,
            bevel_radius=6,
            clip=True,
        )
        for k in range(14):
            a = math.pi * (0.1 + 0.8 * k / 13)
            r = 118 + 10 * math.sin(k * 1.7)
            c.paint(
                circle(c, (cx + r * math.cos(a) * 0.85, 430 + r * math.sin(a) * 0.62), 5),
                gold,
                bevel=0.6,
                bevel_radius=2,
                clip=True,
            )
    swirl_pts = catmull_rom(
        [(512 - 140, 300), (512 - 60, 340), (512, 300), (512 + 60, 340), (512 + 140, 300)], False, 14
    )
    c.paint(
        c.stroke(swirl_pts, 10),
        linear(gold, (255, 240, 200), (300, 0), (700, 0)),
        bevel=0.8,
        bevel_radius=4,
        clip=True,
    )
    for cx in (270, SIZE - 270):
        fan = [
            (cx, 470),
            (cx + (30 if cx < 512 else -30), 560),
            (cx, 640),
            (cx - (30 if cx < 512 else -30), 560),
        ]
        c.paint(
            c.poly(fan),
            linear(gold, deep, (cx, 470), (cx, 640)),
            bevel=0.6,
            bevel_radius=5,
            clip=False,
            opacity=0.9,
        )
    c.paint(
        c.stroke(catmull_rom([(512 - 300, 420), (512 - 340, 470), (512 - 300, 520)], False, 10), 8),
        gold,
        bevel=0.6,
        bevel_radius=3,
        clip=False,
    )
    c.paint(
        c.stroke(catmull_rom([(512 + 300, 420), (512 + 340, 470), (512 + 300, 520)], False, 10), 8),
        gold,
        bevel=0.6,
        bevel_radius=3,
        clip=False,
    )
    return c.to_bgra()


def butterfly() -> np.ndarray:
    c = Canvas(SIZE)
    teal: Color = (210, 150, 40)
    violet: Color = (150, 70, 190)
    for sgn in (-1, 1):

        def sx(x, s=sgn):
            return 512 + s * (x - 512)

        upper = c.spline(
            [
                (sx(512), 260),
                (sx(640), 180),
                (sx(780), 200),
                (sx(860), 300),
                (sx(820), 400),
                (sx(700), 420),
                (sx(600), 380),
                (sx(520), 340),
            ]
        )
        c.shadow(upper, 0, 6, 8, 0.4, clip=False)
        c.paint(
            upper, radial((255, 210, 120), teal, (sx(700), 280), 220), bevel=0.5, bevel_radius=10, ao=0.25
        )
        lower = c.spline(
            [
                (sx(520), 360),
                (sx(600), 420),
                (sx(680), 500),
                (sx(660), 600),
                (sx(560), 620),
                (sx(500), 540),
            ]
        )
        c.paint(
            lower, radial((230, 140, 220), violet, (sx(600), 480), 180), bevel=0.5, bevel_radius=8, ao=0.25
        )
        for k in range(5):
            a = math.radians(30 + k * 25)
            r = 90
            spot = c.ellipse((sx(700) + r * math.cos(a) * sgn, 280 + r * math.sin(a)), (16, 10))
            c.paint(spot, (255, 255, 255), opacity=0.5, clip=True)
    body = c.spline([(512, 240), (534, 320), (528, 460), (512, 560), (496, 460), (490, 320)])
    c.paint(body, linear((60, 40, 30), (30, 20, 16), (490, 240), (534, 560)), bevel=0.6, bevel_radius=6)
    for cx, sgn in ((EYE_L[0], -1), (EYE_R[0], 1)):
        c.erase(c.ellipse((cx, 430), (76, 54), angle=sgn * -6), feather=2)
        c.paint(ring(c, (cx, 430), 82, 76), (40, 24, 18), opacity=0.7, clip=False)
    for sgn in (-1, 1):
        c.paint(c.stroke([(512 + sgn * 6, 244), (512 + sgn * 40, 190)], 4), (40, 26, 20), clip=False)
    return c.to_bgra()


def feather_noir() -> np.ndarray:
    c = Canvas(SIZE)
    black: Color = (26, 24, 26)
    charcoal: Color = (54, 50, 54)
    shape = _base_shape(c, brow=250, cheek=540, flare=20)
    left, right = _eye_holes(c, 0.95)
    body = shape - left - right
    c.shadow(body, 0, 10, 12, 0.55, clip=False)
    c.paint(body, radial((70, 64, 68), black, (512, 400), 400, 1.2), bevel=0.6, bevel_radius=14, ao=0.4)
    c.strands(
        body,
        3200,
        lambda x, y: math.atan2(y - 340, x - 512),
        (16, 40),
        [black, charcoal, (90, 84, 88)],
        1.4,
        curl=0.2,
    )
    for cx, sgn in ((EYE_L[0], -1), (EYE_R[0], 1)):
        c.paint(ring(c, (cx, 430), 92, 82), (18, 16, 18), bevel=0.5, bevel_radius=4, clip=True)
    for sgn in (-1, 1):
        base = (512 + sgn * 290, 390)
        for k in range(5):
            length = 260 + k * 70
            spread = -0.55 + k * 0.22
            dx, dy = sgn * (0.62 + 0.12 * k), -0.82 + spread * 0.12
            norm = math.hypot(dx, dy)
            dx, dy = dx / norm, dy / norm
            tip = (base[0] + dx * length, base[1] + dy * length)
            mid = ((base[0] + tip[0]) / 2 + sgn * 30 * math.sin(k), (base[1] + tip[1]) / 2 - 10)
            quill = c.stroke([base, mid, tip], 7, smooth=True)
            c.paint(quill, (46, 42, 46), bevel=0.4, bevel_radius=2, clip=False)
            nx, ny = -dy, dx
            for t in range(8, 96, 9):
                px = base[0] + (tip[0] - base[0]) * t / 100.0
                py = base[1] + (tip[1] - base[1]) * t / 100.0
                width = 34 * (1.0 - t / 130.0)
                barb = c.poly([(px, py), (px + nx * width, py + ny * width), (px + dx * 22, py + dy * 22)])
                c.paint(barb.blurred(2.5), [black, charcoal][t % 2], opacity=0.9, clip=False)
    return c.to_bgra()


def harlequin() -> np.ndarray:
    c = Canvas(SIZE)
    purple: Color = (150, 40, 120)
    gold: Color = (230, 180, 60)
    shape = _base_shape(c, brow=230, cheek=580, flare=50)
    left, right = _eye_holes(c)
    body = shape - left - right
    c.shadow(body, 0, 10, 12, 0.5, clip=False)
    c.paint(body, purple, bevel=0.5, bevel_radius=12, ao=0.3)
    diamond_size = 70
    for row in range(-2, 3):
        for col in range(-3, 4):
            cx = 512 + col * diamond_size
            cy = 400 + row * diamond_size
            if (row + col) % 2 == 0:
                continue
            d = c.poly(
                [
                    (cx, cy - diamond_size / 2),
                    (cx + diamond_size / 2, cy),
                    (cx, cy + diamond_size / 2),
                    (cx - diamond_size / 2, cy),
                ]
            )
            c.paint(d, gold, opacity=0.92, clip=True)
    for cx, sgn in ((EYE_L[0], -1), (EYE_R[0], 1)):
        c.paint(ring(c, (cx, 430), 100, 88), (30, 12, 24), bevel=0.4, bevel_radius=5, clip=True)
    for sgn in (-1, 1):
        bell_x = 512 + sgn * 320
        stick = c.stroke([(512 + sgn * 260, 420), (bell_x, 360)], 8)
        c.paint(stick, gold, bevel=0.5, bevel_radius=3, clip=False)
        bell = circle(c, (bell_x, 350), 22)
        c.paint(
            bell,
            radial((255, 230, 140), (170, 120, 30), (bell_x - 6, 342), 26),
            bevel=0.6,
            bevel_radius=5,
            clip=False,
        )
    return c.to_bgra()


def cat_eye_lace() -> np.ndarray:
    c = Canvas(SIZE)
    black: Color = (20, 18, 20)
    pink: Color = (210, 70, 120)
    for cx, sgn in ((EYE_L[0], -1), (EYE_R[0], 1)):
        wing = c.spline(
            [
                (cx - sgn * 130, 420),
                (cx - sgn * 60, 372),
                (cx + sgn * 40, 358),
                (cx + sgn * 140, 330),
                (cx + sgn * 170, 400),
                (cx + sgn * 90, 470),
                (cx - sgn * 10, 494),
                (cx - sgn * 100, 486),
            ]
        )
        c.shadow(wing, 0, 6, 8, 0.45, clip=False)
        c.paint(wing, radial((60, 54, 58), black, (cx, 420), 220), bevel=0.55, bevel_radius=10, ao=0.35)
        lace_hole = c.ellipse((cx, 430), (76, 52), angle=sgn * -8)
        c.erase(lace_hole, feather=2)
        for k in range(10):
            a = math.radians(k * 36)
            hole = circle(c, (cx + sgn * 150 + 24 * math.cos(a), 400 + 24 * math.sin(a)), 6)
            c.erase(hole, feather=1)
        ear = c.poly([(cx + sgn * 120, 340), (cx + sgn * 180, 280), (cx + sgn * 170, 360)])
        c.paint(ear, black, bevel=0.5, bevel_radius=4, clip=False)
        gem = circle(c, (cx - sgn * 40, 380), 10)
        c.paint(
            gem,
            radial((255, 180, 210), pink, (cx - sgn * 43, 377), 12),
            bevel=0.6,
            bevel_radius=3,
            clip=False,
        )
    bridge = c.stroke([(EYE_L[0] + 90, 420), (512, 400), (EYE_R[0] - 90, 420)], 14)
    c.paint(bridge, black, bevel=0.5, bevel_radius=4, clip=False)
    return c.to_bgra()
