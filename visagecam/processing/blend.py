import numpy as np


def blend_alpha(frame: np.ndarray, x: int, y: int, color: np.ndarray, alpha: np.ndarray) -> None:
    h, w = alpha.shape
    roi = frame[y : y + h, x : x + w]
    a = (alpha * 256.0 + 0.5).astype(np.uint16)[..., None]
    mixed = color.astype(np.uint16) * a + roi.astype(np.uint16) * (256 - a)
    roi[:] = (mixed >> 8).astype(np.uint8)


def blend_premultiplied(frame: np.ndarray, x: int, y: int, pre: np.ndarray, alpha: np.ndarray) -> None:
    h, w = alpha.shape
    roi = frame[y : y + h, x : x + w]
    a = (alpha * 256.0 + 0.5).astype(np.uint16)[..., None]
    limited = np.minimum(np.clip(pre, 0, 255), a).astype(np.uint16)
    mixed = (limited << 8) + roi.astype(np.uint16) * (256 - a)
    roi[:] = (mixed >> 8).astype(np.uint8)
