# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

import math

import numpy as np


def similarity(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    src = np.asarray(src, dtype=np.float64)
    dst = np.asarray(dst, dtype=np.float64)
    sc = src.mean(axis=0)
    dc = dst.mean(axis=0)
    s = src - sc
    d = dst - dc
    a = float((s * d).sum())
    b = float((s[:, 0] * d[:, 1] - s[:, 1] * d[:, 0]).sum())
    denom = float((s * s).sum()) or 1.0
    k = math.hypot(a, b) / denom
    theta = math.atan2(b, a)
    cos, sin = k * math.cos(theta), k * math.sin(theta)
    rot = np.array([[cos, -sin], [sin, cos]])
    t = dc - rot @ sc
    return np.hstack([rot, t[:, None]])


def affine_fit(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    design = np.hstack([np.asarray(src, dtype=np.float64), np.ones((len(src), 1))])
    solution, *_ = np.linalg.lstsq(design, np.asarray(dst, dtype=np.float64), rcond=None)
    return solution.T


def to3(m: np.ndarray) -> np.ndarray:
    out = np.eye(3)
    out[:2, :] = m
    return out


def adjustment(center, scale: float, rotation_deg: float, offset) -> np.ndarray:
    cx, cy = float(center[0]), float(center[1])
    rad = math.radians(rotation_deg)
    cos, sin = math.cos(rad) * scale, math.sin(rad) * scale
    m = np.array(
        [
            [cos, -sin, cx + offset[0] - cos * cx + sin * cy],
            [sin, cos, cy + offset[1] - sin * cx - cos * cy],
            [0.0, 0.0, 1.0],
        ]
    )
    return m


def apply_points(m3: np.ndarray, pts: np.ndarray) -> np.ndarray:
    return (pts @ m3[:2, :2].T + m3[:2, 2]).astype(np.float32)
