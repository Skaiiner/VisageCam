# Copyright (c) 2026 Skain. Todos los derechos reservados.

import cv2
import numpy as np


def to_u8(alpha: np.ndarray) -> np.ndarray:
    if alpha.dtype == np.uint8:
        return alpha
    return np.clip(alpha * 255.0 + 0.5, 0, 255).astype(np.uint8)


def mix(base: np.ndarray, top: np.ndarray, alpha8: np.ndarray) -> np.ndarray:
    a3 = cv2.merge([alpha8, alpha8, alpha8])
    inv = cv2.merge([255 - alpha8] * 3)
    return cv2.add(cv2.multiply(top, a3, scale=1.0 / 255.0), cv2.multiply(base, inv, scale=1.0 / 255.0))


def blend_alpha(frame: np.ndarray, x: int, y: int, color: np.ndarray, alpha: np.ndarray) -> None:
    a8 = to_u8(alpha)
    h, w = a8.shape
    roi = frame[y : y + h, x : x + w]
    roi[:] = mix(np.ascontiguousarray(roi), np.ascontiguousarray(color), a8)


def blend_premultiplied(frame: np.ndarray, x: int, y: int, pre8: np.ndarray, alpha8: np.ndarray) -> None:
    h, w = alpha8.shape
    roi = frame[y : y + h, x : x + w]
    inv = cv2.merge([255 - alpha8] * 3)
    base = cv2.multiply(np.ascontiguousarray(roi), inv, scale=1.0 / 255.0)
    roi[:] = cv2.add(base, np.minimum(pre8, alpha8[..., None]))
