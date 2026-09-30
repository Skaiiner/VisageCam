import math
from dataclasses import dataclass
from typing import Callable, Sequence

import cv2
import numpy as np

Color = tuple[float, float, float]
ColorSource = Color | Callable[[np.ndarray, np.ndarray], np.ndarray]


def catmull_rom(points: Sequence[tuple[float, float]], closed: bool = True, samples: int = 14) -> np.ndarray:
    pts = np.asarray(points, dtype=np.float64)
    count = len(pts)
    out = []
    segments = count if closed else count - 1
    for i in range(segments):
        if closed:
            p0, p1, p2, p3 = pts[(i - 1) % count], pts[i], pts[(i + 1) % count], pts[(i + 2) % count]
        else:
            p0 = pts[max(i - 1, 0)]
            p1 = pts[i]
            p2 = pts[i + 1]
            p3 = pts[min(i + 2, count - 1)]
        for t in np.linspace(0.0, 1.0, samples, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(
                0.5
                * (
                    2 * p1
                    + (-p0 + p2) * t
                    + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t3
                )
            )
    if not closed:
        out.append(pts[-1])
    return np.array(out)


def linear(c0: Color, c1: Color, p0: tuple[float, float], p1: tuple[float, float]) -> ColorSource:
    a = np.array(c0, dtype=np.float32)
    b = np.array(c1, dtype=np.float32)
    d = np.array(p1, dtype=np.float32) - np.array(p0, dtype=np.float32)
    length2 = float(d @ d) or 1.0

    def fn(xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
        t = ((xs - p0[0]) * d[0] + (ys - p0[1]) * d[1]) / length2
        t = np.clip(t, 0.0, 1.0)[..., None]
        return a + (b - a) * t

    return fn


def radial(c_in: Color, c_out: Color, center: tuple[float, float], radius: float,
           squash: float = 1.0) -> ColorSource:
    a = np.array(c_in, dtype=np.float32)
    b = np.array(c_out, dtype=np.float32)

    def fn(xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
        d = np.sqrt((xs - center[0]) ** 2 + ((ys - center[1]) / squash) ** 2) / radius
        t = np.clip(d, 0.0, 1.0)[..., None]
        return a + (b - a) * t

    return fn


@dataclass
class Shape:
    x0: int
    y0: int
    m: np.ndarray

    @property
    def x1(self) -> int:
        return self.x0 + self.m.shape[1]

    @property
    def y1(self) -> int:
        return self.y0 + self.m.shape[0]

    def blurred(self, sigma: float) -> "Shape":
        if sigma <= 0:
            return self
        pad = int(sigma * 3) + 1
        m = cv2.copyMakeBorder(self.m, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
        m = cv2.GaussianBlur(m, (0, 0), sigma)
        return Shape(self.x0 - pad, self.y0 - pad, m)

    def _merge(self, other: "Shape", fn) -> "Shape":
        x0, y0 = min(self.x0, other.x0), min(self.y0, other.y0)
        x1, y1 = max(self.x1, other.x1), max(self.y1, other.y1)
        a = np.zeros((y1 - y0, x1 - x0), np.float32)
        b = np.zeros_like(a)
        a[self.y0 - y0 : self.y1 - y0, self.x0 - x0 : self.x1 - x0] = self.m
        b[other.y0 - y0 : other.y1 - y0, other.x0 - x0 : other.x1 - x0] = other.m
        return Shape(x0, y0, fn(a, b))

    def __add__(self, other: "Shape") -> "Shape":
        return self._merge(other, np.maximum)

    def __sub__(self, other: "Shape") -> "Shape":
        return self._merge(other, lambda a, b: a * (1.0 - b))

    def __mul__(self, other: "Shape") -> "Shape":
        return self._merge(other, lambda a, b: a * b)


class Canvas:
    def __init__(self, size: int = 1024, supersample: int = 2, seed: int = 7) -> None:
        self.size = size
        self.ss = supersample
        self.n = size * supersample
        self.pre = np.zeros((self.n, self.n, 3), np.float32)
        self.a = np.zeros((self.n, self.n), np.float32)
        self.rng = np.random.default_rng(seed)
        self._noise: dict[float, np.ndarray] = {}

    def _raster(self, pts: np.ndarray, draw: Callable[[np.ndarray, np.ndarray], None], margin: float = 4) -> Shape:
        p = pts * self.ss
        x0 = int(max(0, math.floor(p[:, 0].min() - margin)))
        y0 = int(max(0, math.floor(p[:, 1].min() - margin)))
        x1 = int(min(self.n, math.ceil(p[:, 0].max() + margin)))
        y1 = int(min(self.n, math.ceil(p[:, 1].max() + margin)))
        if x1 <= x0 or y1 <= y0:
            return Shape(0, 0, np.zeros((1, 1), np.float32))
        layer = np.zeros((y1 - y0, x1 - x0), np.uint8)
        local = p - np.array([x0, y0])
        draw(layer, local)
        return Shape(x0, y0, layer.astype(np.float32) / 255.0)

    def poly(self, pts) -> Shape:
        arr = np.asarray(pts, dtype=np.float64)

        def draw(layer, local):
            cv2.fillPoly(layer, [np.round(local * 16).astype(np.int32)], 255, cv2.LINE_AA, 4)

        return self._raster(arr, draw)

    def spline(self, pts, samples: int = 14) -> Shape:
        return self.poly(catmull_rom(pts, True, samples))

    def ellipse(self, center, radii, angle: float = 0.0) -> Shape:
        cx, cy = center
        rx, ry = radii
        r = max(rx, ry)
        box = np.array([[cx - r, cy - r], [cx + r, cy + r]], dtype=np.float64)

        def draw(layer, local):
            c = (local[0] + local[1]) / 2.0
            cv2.ellipse(
                layer,
                (int(round(c[0] * 16)), int(round(c[1] * 16))),
                (int(round(rx * self.ss * 16)), int(round(ry * self.ss * 16))),
                angle,
                0,
                360,
                255,
                -1,
                cv2.LINE_AA,
                4,
            )

        return self._raster(box, draw)

    def stroke(self, pts, width: float, closed: bool = False, smooth: bool = True) -> Shape:
        arr = np.asarray(pts, dtype=np.float64)
        if smooth and len(arr) > 2:
            arr = catmull_rom(arr, closed, 10)
        pad = width

        def draw(layer, local):
            cv2.polylines(
                layer,
                [np.round(local * 16).astype(np.int32)],
                closed,
                255,
                max(1, int(round(width * self.ss))),
                cv2.LINE_AA,
                4,
            )

        return self._raster(arr, draw, margin=pad * self.ss + 4)

    def _grid(self, shape: Shape) -> tuple[np.ndarray, np.ndarray]:
        xs = (np.arange(shape.x0, shape.x1, dtype=np.float32) + 0.5) / self.ss
        ys = (np.arange(shape.y0, shape.y1, dtype=np.float32) + 0.5) / self.ss
        return np.meshgrid(xs, ys)

    def noise(self, scale: float) -> np.ndarray:
        if scale not in self._noise:
            field = self.rng.standard_normal((self.n, self.n)).astype(np.float32)
            field = cv2.GaussianBlur(field, (0, 0), scale * self.ss)
            field /= float(field.std()) or 1.0
            self._noise[scale] = field
        return self._noise[scale]

    def paint(
        self,
        shape: Shape,
        color: ColorSource,
        *,
        opacity: float = 1.0,
        bevel: float = 0.0,
        bevel_radius: float = 10.0,
        ao: float = 0.0,
        light: tuple[float, float] = (-0.7, -0.7),
        grain: float = 0.0,
        grain_scale: float = 2.0,
        streak: float = 0.0,
        clip: bool = False,
        below: bool = False,
    ) -> None:
        fitted = self._fit(shape)
        if fitted is None:
            return
        shape = fitted
        xs, ys = self._grid(shape)
        if callable(color):
            col = color(xs, ys).astype(np.float32)
        else:
            col = np.empty(xs.shape + (3,), np.float32)
            col[:] = np.array(color, dtype=np.float32)
        sl = (slice(shape.y0, shape.y1), slice(shape.x0, shape.x1))
        m = shape.m
        if bevel or ao:
            r = bevel_radius * self.ss
            pad = int(r * 3) + 1
            padded = cv2.copyMakeBorder(m, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
            h = cv2.GaussianBlur(padded, (0, 0), r)
            gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3) / 8.0
            gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3) / 8.0
            h = h[pad:-pad, pad:-pad]
            gx = gx[pad:-pad, pad:-pad]
            gy = gy[pad:-pad, pad:-pad]
            shade = np.clip(-(gx * light[0] + gy * light[1]) * r * 2.6, -1.0, 1.0)
            if bevel:
                lit = np.where(shade > 0, shade * 0.9, shade * 0.75)
                col *= (1.0 + bevel * lit)[..., None]
            if ao:
                depth = np.clip((h - 0.5) * 2.2, 0.0, 1.0)
                col *= (1.0 - ao * (1.0 - depth))[..., None]
        if grain:
            col *= (1.0 + grain * self.noise(grain_scale)[sl])[..., None]
        if streak:
            col *= (1.0 + streak * self.noise(0.8)[sl] * np.linspace(0.6, 1.0, m.shape[0])[:, None])[..., None]
        col = np.clip(col, 0.0, 255.0)
        a = m * opacity
        if clip:
            a = a * self.a[sl]
        if below:
            room = a * (1.0 - self.a[sl])
            self.pre[sl] += col * room[..., None]
            self.a[sl] += room
            return
        self.pre[sl] = col * a[..., None] + self.pre[sl] * (1.0 - a[..., None])
        self.a[sl] = a + self.a[sl] * (1.0 - a)

    def shadow(self, shape: Shape, dx: float, dy: float, blur: float, opacity: float,
               clip: bool = True, color: Color = (0, 0, 0)) -> None:
        moved = Shape(shape.x0 + int(dx * self.ss), shape.y0 + int(dy * self.ss), shape.m)
        self.paint(moved.blurred(blur * self.ss), color, opacity=opacity, clip=clip)

    def _fit(self, shape: Shape) -> Shape | None:
        x0, y0 = max(shape.x0, 0), max(shape.y0, 0)
        x1, y1 = min(shape.x1, self.n), min(shape.y1, self.n)
        if x1 <= x0 or y1 <= y0 or shape.m.size <= 1:
            return None
        return Shape(x0, y0, shape.m[y0 - shape.y0 : y1 - shape.y0, x0 - shape.x0 : x1 - shape.x0])

    def erase(self, shape: Shape, feather: float = 0.0) -> None:
        soft = shape.blurred(feather * self.ss) if feather else shape
        fitted = self._fit(soft)
        if fitted is None:
            return
        sl = (slice(fitted.y0, fitted.y1), slice(fitted.x0, fitted.x1))
        self.pre[sl] *= (1.0 - fitted.m)[..., None]
        self.a[sl] *= 1.0 - fitted.m

    def strands(
        self,
        shape: Shape,
        count: int,
        direction: Callable[[float, float], float],
        length: tuple[float, float],
        colors: Sequence[Color],
        width: float = 1.4,
        opacity: float = 1.0,
        curl: float = 0.0,
    ) -> None:
        h, w = shape.m.shape
        layer = np.zeros((h, w, 4), np.uint8)
        ys, xs = np.nonzero(shape.m > 0.5)
        if len(xs) == 0:
            return
        picks = self.rng.integers(0, len(xs), count)
        palette = np.array(colors, dtype=np.float32)
        for k in picks:
            px, py = xs[k], ys[k]
            dxs = (px + shape.x0) / self.ss
            dys = (py + shape.y0) / self.ss
            angle = direction(dxs, dys) + self.rng.normal(0, 0.22)
            ln = self.rng.uniform(*length) * self.ss
            c = palette[self.rng.integers(0, len(palette))] * self.rng.uniform(0.86, 1.12)
            c = np.clip(c, 0, 255)
            end = (px + math.cos(angle) * ln, py + math.sin(angle) * ln)
            mid = ((px + end[0]) / 2 + math.cos(angle + 1.57) * ln * curl, (py + end[1]) / 2 + math.sin(angle + 1.57) * ln * curl)
            pts = np.array([[px, py], mid, end], dtype=np.float64)
            pts = np.round(pts * 16).astype(np.int32)
            col = (float(c[2]), float(c[1]), float(c[0]), 255.0)
            cv2.polylines(layer, [pts], False, col, max(1, int(round(width * self.ss * self.rng.uniform(0.6, 1.1)))), cv2.LINE_AA, 4)
        alpha = layer[:, :, 3].astype(np.float32) / 255.0 * shape.m * opacity
        rgb = layer[:, :, 2::-1].astype(np.float32)
        sl = (slice(shape.y0, shape.y1), slice(shape.x0, shape.x1))
        strand_a = layer[:, :, 3].astype(np.float32) / 255.0
        safe = np.maximum(strand_a, 1e-3)[..., None]
        straight = rgb / safe
        self.pre[sl] = straight * alpha[..., None] + self.pre[sl] * (1.0 - alpha[..., None])
        self.a[sl] = alpha + self.a[sl] * (1.0 - alpha)

    def to_bgra(self) -> np.ndarray:
        rgba = np.dstack([self.pre, self.a[..., None]])
        small = cv2.resize(rgba, (self.size, self.size), interpolation=cv2.INTER_AREA)
        alpha = small[:, :, 3:4]
        rgb = np.where(alpha > 1e-4, small[:, :, :3] / np.maximum(alpha, 1e-4), 0.0)
        out = np.dstack([np.clip(rgb, 0, 255), np.clip(alpha * 255.0, 0, 255)]).astype(np.uint8)
        return np.ascontiguousarray(out[:, :, [2, 1, 0, 3]])
