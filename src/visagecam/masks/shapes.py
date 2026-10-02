# Copyright (c) 2026 Skain. Todos los derechos reservados.

import math

import numpy as np

from visagecam.masks.painter import Canvas, Color, Shape, catmull_rom


def rrect(x0: float, y0: float, x1: float, y1: float, r: float, n: int = 10) -> list[tuple[float, float]]:
    pts = []
    for cx, cy, a0 in (
        (x1 - r, y0 + r, -90),
        (x1 - r, y1 - r, 0),
        (x0 + r, y1 - r, 90),
        (x0 + r, y0 + r, 180),
    ):
        for k in range(n + 1):
            a = math.radians(a0 + 90.0 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def tapered(c: Canvas, pts, w0: float, w1: float = 0.0) -> Shape:
    path = catmull_rom(pts, False, 10)
    tangent = np.gradient(path, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True) + 1e-9
    normal = np.stack([-tangent[:, 1], tangent[:, 0]], axis=1)
    t = np.linspace(0.0, 1.0, len(path))[:, None]
    half = (w0 + (w1 - w0) * t**0.85) / 2.0
    return c.poly(np.vstack([path + normal * half, (path - normal * half)[::-1]]))


def dashed(
    c: Canvas,
    pts,
    color: Color,
    dash: float = 16,
    gap: float = 10,
    width: float = 4,
    smooth: bool = True,
    opacity: float = 1.0,
    clip: bool = False,
) -> None:
    path = catmull_rom(pts, False, 12) if smooth and len(pts) > 2 else np.asarray(pts, dtype=np.float64)
    seg = np.hypot(*np.diff(path, axis=0).T)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    total = cum[-1]
    s = 0.0
    while s < total:
        e = min(s + dash, total)
        samples = np.linspace(s, e, 4)
        stroke = np.stack([np.interp(samples, cum, path[:, 0]), np.interp(samples, cum, path[:, 1])], axis=1)
        c.paint(
            c.stroke(stroke, width, smooth=False),
            color,
            bevel=0.5,
            bevel_radius=1.5,
            opacity=opacity,
            clip=clip,
        )
        s += dash + gap


def noise_shape(c: Canvas, base: Shape, scale: float, threshold: float, softness: float = 0.6) -> Shape:
    field = c.noise(scale)[base.y0 : base.y1, base.x0 : base.x1]
    m = np.clip((field - threshold) / softness, 0.0, 1.0).astype(np.float32) * base.m
    return Shape(base.x0, base.y0, m)


def circle(c: Canvas, center, r: float) -> Shape:
    return c.ellipse(center, (r, r))


def ring(c: Canvas, center, r_out: float, r_in: float) -> Shape:
    return circle(c, center, r_out) - circle(c, center, r_in)
