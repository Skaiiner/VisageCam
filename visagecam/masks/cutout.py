import cv2
import numpy as np


def _border_pixels(bgr: np.ndarray) -> np.ndarray:
    return np.concatenate([bgr[0], bgr[-1], bgr[:, 0], bgr[:, -1]]).astype(np.float32)


def _flood_cutout(bgr: np.ndarray) -> np.ndarray | None:
    border = _border_pixels(bgr)
    if float(border.std(axis=0).max()) > 14.0:
        return None
    height, width = bgr.shape[:2]
    padded = cv2.copyMakeBorder(bgr, 1, 1, 1, 1, cv2.BORDER_REPLICATE)
    fill = np.zeros((height + 4, width + 4), dtype=np.uint8)
    tolerance = (22, 22, 22)
    cv2.floodFill(
        padded,
        fill,
        (0, 0),
        (0, 0, 0),
        tolerance,
        tolerance,
        cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (255 << 8),
    )
    background = fill[2:-2, 2:-2] > 0
    return np.where(background, 0, 255).astype(np.uint8)


def _grabcut(bgr: np.ndarray) -> np.ndarray:
    height, width = bgr.shape[:2]
    scale = min(1.0, 512.0 / max(height, width))
    small = cv2.resize(bgr, (max(2, int(width * scale)), max(2, int(height * scale))), interpolation=cv2.INTER_AREA)
    sh, sw = small.shape[:2]
    mask = np.zeros((sh, sw), np.uint8)
    rect = (max(1, int(sw * 0.04)), max(1, int(sh * 0.04)), int(sw * 0.92), int(sh * 0.92))
    bg_model = np.zeros((1, 65), np.float64)
    fg_model = np.zeros((1, 65), np.float64)
    cv2.grabCut(small, mask, rect, bg_model, fg_model, 4, cv2.GC_INIT_WITH_RECT)
    result = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    return cv2.resize(result, (width, height), interpolation=cv2.INTER_LINEAR)


def _refine(alpha: np.ndarray) -> np.ndarray:
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, kernel)
    alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, kernel)
    count, labels, stats, _ = cv2.connectedComponentsWithStats((alpha > 127).astype(np.uint8), 8)
    if count > 1:
        keep = np.zeros_like(alpha)
        limit = stats[1:, cv2.CC_STAT_AREA].max() * 0.02
        for label in range(1, count):
            if stats[label, cv2.CC_STAT_AREA] >= limit:
                keep[labels == label] = 255
        alpha = keep
    alpha = cv2.erode(alpha, np.ones((3, 3), np.uint8))
    return cv2.GaussianBlur(alpha, (0, 0), 1.6)


def remove_background(bgr: np.ndarray) -> np.ndarray | None:
    alpha = _flood_cutout(bgr)
    if alpha is None:
        alpha = _grabcut(bgr)
    alpha = _refine(alpha)
    coverage = float((alpha > 127).mean())
    if coverage < 0.03 or coverage > 0.97:
        return None
    return alpha
