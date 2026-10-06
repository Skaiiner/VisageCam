# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

import math
from collections.abc import Callable
from dataclasses import dataclass

import cv2
import numpy as np

CATEGORIES = (
    ("all", "Todos"),
    ("warp", "Deformar imagen"),
    ("style", "Color y estilo"),
)

SEPIA = np.array(
    [[0.131, 0.534, 0.272], [0.168, 0.686, 0.349], [0.189, 0.769, 0.393]],
    dtype=np.float32,
)
EMBOSS = np.array([[-2, -1, 0], [-1, 1, 1], [0, 1, 2]], dtype=np.float32)
MAX_CACHED_MAPS = 12


def _weight(strength: float) -> float:
    return float(np.clip(strength, 0.0, 1.0))


def _blend(base: np.ndarray, top: np.ndarray, weight: float) -> np.ndarray:
    w = _weight(weight)
    if w >= 0.999:
        return top
    return cv2.addWeighted(base, 1.0 - w, top, w, 0)


def _gray3(frame: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)


def _radial(width: int, height: int):
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    cx, cy = (width - 1) / 2.0, (height - 1) / 2.0
    dx, dy = xs - cx, ys - cy
    r = np.sqrt(dx * dx + dy * dy) / math.hypot(cx, cy)
    return xs, ys, cx, cy, dx, dy, r


def _fisheye(width: int, height: int, s: float):
    _, _, cx, cy, dx, dy, r = _radial(width, height)
    factor = np.clip(1.0 - 0.55 * min(s, 1.6) * (1.0 - r * r), 0.2, 1.0)
    return cx + dx * factor, cy + dy * factor


def _pinch(width: int, height: int, s: float):
    _, _, cx, cy, dx, dy, r = _radial(width, height)
    factor = 1.0 + 0.7 * min(s, 1.6) * (1.0 - r * r)
    return cx + dx * factor, cy + dy * factor


def _swirl(width: int, height: int, s: float):
    _, _, cx, cy, dx, dy, r = _radial(width, height)
    theta = 3.2 * min(s, 1.5) * np.clip(1.0 - r * 1.4, 0.0, 1.0) ** 2
    cos, sin = np.cos(theta), np.sin(theta)
    return cx + dx * cos + dy * sin, cy - dx * sin + dy * cos


def _wave_h(width: int, height: int, s: float):
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    return xs + 10.0 * s * np.sin(2 * np.pi * ys / (height / 5.0)), ys


def _wave_v(width: int, height: int, s: float):
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    return xs, ys + 10.0 * s * np.sin(2 * np.pi * xs / (width / 6.0))


def _mirror_h(width: int, height: int, s: float):
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    cx = (width - 1) / 2.0
    return np.where(xs > cx, 2 * cx - xs, xs), ys


def _mirror_v(width: int, height: int, s: float):
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    cy = (height - 1) / 2.0
    return xs, np.where(ys > cy, 2 * cy - ys, ys)


def _kaleido(width: int, height: int, s: float):
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    cx, cy = (width - 1) / 2.0, (height - 1) / 2.0
    return cx - np.abs(xs - cx), cy - np.abs(ys - cy)


def _zoom(width: int, height: int, s: float):
    _, _, cx, cy, dx, dy, _ = _radial(width, height)
    factor = 1.0 + 0.3 * min(s, 2.0)
    return cx + dx / factor, cy + dy / factor


def _tiles(width: int, height: int, s: float):
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    return (xs * 2.0) % width, (ys * 2.0) % height


WARPS: dict[str, Callable[[int, int, float], tuple[np.ndarray, np.ndarray]]] = {
    "fisheye": _fisheye,
    "pinch": _pinch,
    "swirl": _swirl,
    "wave_h": _wave_h,
    "wave_v": _wave_v,
    "mirror_h": _mirror_h,
    "mirror_v": _mirror_v,
    "kaleido": _kaleido,
    "zoom": _zoom,
    "tiles": _tiles,
}


def _grain(state: dict, shape: tuple[int, int], sigma: float) -> np.ndarray:
    key = ("grain", *shape)
    bank = state.get(key)
    if bank is None:
        height, width = shape
        small = state["rng"].normal(0, 1.0, (max(2, height // 3), max(2, width // 3))).astype(np.float32)
        bank = cv2.resize(small, (width, height), interpolation=cv2.INTER_LINEAR)
        state[key] = bank
    offset = int(state["rng"].integers(0, shape[0]))
    return np.roll(bank, offset, axis=0) * sigma


def _vignette(shape: tuple[int, int], power: float = 1.0) -> np.ndarray:
    height, width = shape
    kx = cv2.getGaussianKernel(width, width * 0.55)
    ky = cv2.getGaussianKernel(height, height * 0.55)
    mask = (ky @ kx.T).astype(np.float32)
    mask = (mask / mask.max()) ** power
    return mask[..., None]


def _channel_gain(frame: np.ndarray, blue: float, green: float, red: float) -> np.ndarray:
    ramp = np.arange(256, dtype=np.float32)[:, None]
    lut = np.clip(ramp * np.array([blue, green, red], dtype=np.float32), 0, 255).astype(np.uint8)
    return cv2.LUT(frame, lut[:, None, :])


def _bw(frame, s, state):
    return _blend(frame, _gray3(frame), s)


def _sepia(frame, s, state):
    return _blend(frame, cv2.transform(frame, SEPIA), s)


def _negative(frame, s, state):
    return _blend(frame, 255 - frame, s)


def _posterize(frame, s, state):
    levels = int(np.clip(10 - 4 * s, 2, 8))
    step = 256 // levels
    return ((frame // step) * step + step // 2).astype(np.uint8)


def _neon(frame, s, state):
    height, width = frame.shape[:2]
    gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (5, 5), 0)

    edges = cv2.dilate(cv2.Canny(gray, 50, 130), np.ones((3, 3), np.uint8))
    key = ("neon", width, height)
    if key not in state:
        hue = np.tile(np.linspace(0, 179, width, dtype=np.uint8), (height, 1))
        hsv = np.dstack([hue, np.full_like(hue, 255), np.full_like(hue, 255)])
        state[key] = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    lines = cv2.bitwise_and(state[key], state[key], mask=edges)
    glow = cv2.resize(
        cv2.GaussianBlur(
            cv2.resize(lines, (width // 3, lines.shape[0] // 3), interpolation=cv2.INTER_AREA), (0, 0), 2
        ),
        (lines.shape[1], lines.shape[0]),
        interpolation=cv2.INTER_LINEAR,
    )
    base = cv2.convertScaleAbs(frame, alpha=0.22)
    return cv2.add(cv2.add(base, lines), cv2.convertScaleAbs(glow, alpha=1.4 * min(s, 1.5)))


def _cartoon(frame, s, state):
    height, width = frame.shape[:2]
    small = cv2.resize(frame, (width // 2, height // 2), interpolation=cv2.INTER_AREA)
    smooth = cv2.bilateralFilter(small, 7, 45, 7)
    smooth = cv2.resize(smooth, (width, height), interpolation=cv2.INTER_LINEAR)
    smooth = (smooth // 24 * 24 + 12).astype(np.uint8)
    gray = cv2.medianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 5)
    edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 7)
    toon = cv2.bitwise_and(smooth, cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR))
    return _blend(frame, toon, s)


def _sketch(frame, s, state):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(255 - gray, (21, 21), 0)
    dodge = cv2.divide(gray, 255 - blur, scale=256)
    return _blend(frame, cv2.cvtColor(dodge, cv2.COLOR_GRAY2BGR), s)


def _pixelate(frame, s, state):
    height, width = frame.shape[:2]
    block = int(6 + 10 * s)
    small = cv2.resize(frame, (max(2, width // block), max(2, height // block)), interpolation=cv2.INTER_AREA)
    return cv2.resize(small, (width, height), interpolation=cv2.INTER_NEAREST)


def _thermal(frame, s, state):
    gray = cv2.equalizeHist(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    return _blend(frame, cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO), s)


def _vhs(frame, s, state):
    shift = int(2 + 4 * s)
    out = frame.copy()
    out[..., 0] = np.roll(frame[..., 0], shift, axis=1)
    out[..., 2] = np.roll(frame[..., 2], -shift, axis=1)
    out = cv2.GaussianBlur(out, (5, 1), 0)
    out[::3] = cv2.convertScaleAbs(out[::3], alpha=0.82)
    grain = cv2.convertScaleAbs(_grain(state, out.shape[:2], 7.0) + 128, alpha=1.0, beta=-128)
    return cv2.add(out, cv2.cvtColor(grain, cv2.COLOR_GRAY2BGR))


def _vintage(frame, s, state):
    toned = _blend(frame, cv2.transform(frame, SEPIA), 0.45)
    key = ("vig8", *frame.shape[:2])
    mask8 = state.get(key)
    if mask8 is None:
        mask8 = (0.45 + 0.55 * _vignette(frame.shape[:2], 0.6)[..., 0]) * 255.0
        mask8 = cv2.cvtColor(mask8.astype(np.uint8), cv2.COLOR_GRAY2BGR)
        state[key] = mask8
    faded = cv2.convertScaleAbs(toned, alpha=0.88, beta=22)
    shaded = cv2.multiply(faded, mask8, scale=1.0 / 255.0)
    grain = cv2.convertScaleAbs(_grain(state, frame.shape[:2], 8.0 * min(s, 1.5)) + 128, beta=-128)
    return cv2.add(shaded, cv2.cvtColor(grain, cv2.COLOR_GRAY2BGR))


def _glow(frame, s, state):
    height, width = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    bright = cv2.bitwise_and(frame, frame, mask=(gray > 150).astype(np.uint8) * 255)
    tiny = cv2.resize(bright, (width // 4, height // 4), interpolation=cv2.INTER_AREA)
    halo = cv2.resize(cv2.GaussianBlur(tiny, (0, 0), 4), (width, height), interpolation=cv2.INTER_LINEAR)
    soft = cv2.GaussianBlur(frame, (0, 0), 3)
    return cv2.addWeighted(cv2.addWeighted(frame, 0.7, soft, 0.3, 0), 1.0, halo, 0.9 * min(s, 1.5), 0)


def _cool(frame, s, state):
    return _blend(frame, _channel_gain(frame, 1.28, 1.02, 0.82), s)


def _warm(frame, s, state):
    return _blend(frame, _channel_gain(frame, 0.8, 1.0, 1.25), s)


def _nightvision(frame, s, state):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    boosted = cv2.convertScaleAbs(gray, alpha=1.5, beta=25)
    grain = cv2.convertScaleAbs(_grain(state, gray.shape, 13.0) + 128, beta=-128)
    key = ("vig1", *frame.shape[:2])
    mask1 = state.get(key)
    if mask1 is None:
        mask1 = ((0.35 + 0.65 * _vignette(frame.shape[:2], 0.6)[..., 0]) * 255.0).astype(np.uint8)
        state[key] = mask1
    value = cv2.multiply(cv2.add(boosted, grain), mask1, scale=1.0 / 255.0)
    out = cv2.merge([cv2.convertScaleAbs(value, alpha=0.25), value, cv2.convertScaleAbs(value, alpha=0.3)])
    return _blend(frame, out, s)


def _glitch(frame, s, state):
    rng = state["rng"]
    out = frame.copy()
    height = frame.shape[0]
    for _ in range(3 + int(3 * s)):
        y0 = int(rng.integers(0, max(1, height - 20)))
        thickness = int(rng.integers(6, max(8, height // 10)))
        shift = int(rng.integers(-70, 70) * min(s, 1.5))
        out[y0 : y0 + thickness] = np.roll(out[y0 : y0 + thickness], shift, axis=1)
    out[..., 2] = np.roll(out[..., 2], int(6 * s), axis=1)
    out[..., 0] = np.roll(out[..., 0], -int(6 * s), axis=1)
    return out


def _emboss(frame, s, state):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    relief = np.clip(cv2.filter2D(gray, cv2.CV_32F, EMBOSS) + 128, 0, 255).astype(np.uint8)
    return _blend(frame, cv2.cvtColor(relief, cv2.COLOR_GRAY2BGR), s)


def _contrast(frame, s, state):
    return cv2.convertScaleAbs(frame, alpha=1.0 + 0.6 * s, beta=-35 * s)


STYLES: dict[str, Callable] = {
    "bw": _bw,
    "sepia": _sepia,
    "negative": _negative,
    "posterize": _posterize,
    "neon": _neon,
    "cartoon": _cartoon,
    "sketch": _sketch,
    "pixelate": _pixelate,
    "thermal": _thermal,
    "vhs": _vhs,
    "vintage": _vintage,
    "glow": _glow,
    "cool": _cool,
    "warm": _warm,
    "nightvision": _nightvision,
    "glitch": _glitch,
    "emboss": _emboss,
    "contrast": _contrast,
}


@dataclass(frozen=True)
class CameraEffect:
    name: str
    category: str


EFFECTS: dict[str, CameraEffect] = {
    "fisheye": CameraEffect("Ojo de pez", "warp"),
    "pinch": CameraEffect("Pellizco", "warp"),
    "swirl": CameraEffect("Remolino", "warp"),
    "wave_h": CameraEffect("Ola horizontal", "warp"),
    "wave_v": CameraEffect("Ola vertical", "warp"),
    "mirror_h": CameraEffect("Espejo horizontal", "warp"),
    "mirror_v": CameraEffect("Espejo vertical", "warp"),
    "kaleido": CameraEffect("Caleidoscopio", "warp"),
    "zoom": CameraEffect("Zoom", "warp"),
    "tiles": CameraEffect("Cuatro camaras", "warp"),
    "bw": CameraEffect("Blanco y negro", "style"),
    "sepia": CameraEffect("Sepia", "style"),
    "negative": CameraEffect("Negativo", "style"),
    "posterize": CameraEffect("Cartel", "style"),
    "neon": CameraEffect("Neon", "style"),
    "cartoon": CameraEffect("Dibujo animado", "style"),
    "sketch": CameraEffect("Boceto", "style"),
    "pixelate": CameraEffect("Pixelado", "style"),
    "thermal": CameraEffect("Termico", "style"),
    "vhs": CameraEffect("VHS", "style"),
    "vintage": CameraEffect("Vintage", "style"),
    "glow": CameraEffect("Resplandor", "style"),
    "cool": CameraEffect("Frio", "style"),
    "warm": CameraEffect("Calido", "style"),
    "nightvision": CameraEffect("Vision nocturna", "style"),
    "glitch": CameraEffect("Glitch", "style"),
    "emboss": CameraEffect("Relieve", "style"),
    "contrast": CameraEffect("Alto contraste", "style"),
}


def effects_in(category: str) -> list[str]:
    return [eid for eid, effect in EFFECTS.items() if category == "all" or effect.category == category]


class CameraEffectRenderer:
    def __init__(self) -> None:
        self._maps: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}
        self._state: dict = {"rng": np.random.default_rng(7)}

    def apply(self, frame: np.ndarray, effect_id: str, strength: float = 1.0) -> np.ndarray:
        strength = float(np.clip(strength, 0.3, 2.0))
        warp = WARPS.get(effect_id)
        if warp is not None:
            return self._warp(frame, effect_id, warp, strength)
        style = STYLES.get(effect_id)
        if style is not None:
            return style(frame, strength, self._state)
        return frame

    def _warp(self, frame: np.ndarray, effect_id: str, builder, strength: float) -> np.ndarray:
        height, width = frame.shape[:2]
        key = (effect_id, width, height, round(strength, 1))
        maps = self._maps.get(key)
        if maps is None:
            map_x, map_y = builder(width, height, round(strength, 1))
            maps = (map_x.astype(np.float32), map_y.astype(np.float32))
            if len(self._maps) >= MAX_CACHED_MAPS:
                self._maps.pop(next(iter(self._maps)))
            self._maps[key] = maps
        return cv2.remap(frame, maps[0], maps[1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


class CameraGrader:
    @staticmethod
    def active(settings) -> bool:
        return any(
            abs(getattr(settings, key)) > 0.01
            for key in ("grade_brightness", "grade_contrast", "grade_saturation", "grade_temperature")
        )

    def apply(
        self, frame: np.ndarray, brightness: float, contrast: float, saturation: float, temperature: float
    ) -> np.ndarray:
        alpha = 1.0 + (0.8 if contrast >= 0 else 0.6) * contrast
        beta = 70.0 * brightness
        gains = np.array([1.0 - 0.25 * temperature, 1.0, 1.0 + 0.25 * temperature], dtype=np.float32)
        ramp = np.arange(256, dtype=np.float32)[:, None]
        lut = np.clip((ramp * alpha + beta) * gains, 0, 255).astype(np.uint8)
        out = cv2.LUT(frame, lut[:, None, :])
        if abs(saturation) > 0.01:
            hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV)
            hsv[..., 1] = cv2.convertScaleAbs(hsv[..., 1], alpha=max(0.0, 1.0 + saturation))
            out = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        return out
