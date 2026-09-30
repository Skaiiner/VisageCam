import math

import cv2
import numpy as np

from visagecam.config import Settings
from visagecam.masks.model import Mask
from visagecam.processing.blend import blend_premultiplied
from visagecam.processing.landmarks import (
    EYE_LEFT,
    EYE_RIGHT,
    FACE_EDGE_LEFT,
    FACE_EDGE_RIGHT,
    FACE_OVAL,
    FOREHEAD,
    STABLE_POINTS,
    face_roll,
    face_width,
    group_center,
)
from visagecam.processing.face_warp import FaceWarpRenderer
from visagecam.processing.transforms import adjustment, affine_fit, apply_points, similarity, to3

SLOT_WIDTH = {"head": 1.15, "eyes": 1.05, "mouth": 0.55, "ears": 1.3, "free": 1.6}
UPPER_LIP = (0,)


class OverlayRenderer:
    def __init__(self) -> None:
        self._pyramids: dict[str, list[np.ndarray]] = {}
        self._luma: float | None = None

    def reset(self) -> None:
        self._luma = None

    def _pyramid(self, mask: Mask) -> list[np.ndarray]:
        levels = self._pyramids.get(mask.mask_id)
        if levels is None or levels[0].shape != mask.image.shape:
            alpha = mask.image[:, :, 3:4].astype(np.float32) / 255.0
            pre = np.dstack([mask.image[:, :, :3].astype(np.float32) * alpha, alpha * 255.0])
            levels = [pre.astype(np.uint8)]
            while min(levels[-1].shape[:2]) >= 256 and len(levels) < 4:
                last = levels[-1]
                levels.append(cv2.resize(last, (last.shape[1] // 2, last.shape[0] // 2), interpolation=cv2.INTER_AREA))
            self._pyramids[mask.mask_id] = levels
        return levels

    @staticmethod
    def _slot_target(slot: str, landmarks: np.ndarray, up: np.ndarray, fw: float) -> np.ndarray:
        if slot == "head":
            return group_center(landmarks, FOREHEAD) - up * (0.04 * fw)
        if slot == "eyes":
            return (group_center(landmarks, EYE_LEFT) + group_center(landmarks, EYE_RIGHT)) / 2.0
        if slot == "mouth":
            return group_center(landmarks, UPPER_LIP) + up * (0.05 * fw)
        if slot == "ears":
            return (landmarks[FACE_EDGE_LEFT] + landmarks[FACE_EDGE_RIGHT]) / 2.0
        return landmarks[FACE_OVAL].mean(axis=0)

    @classmethod
    def _base(cls, mask: Mask, landmarks: np.ndarray, canon: np.ndarray | None = None) -> np.ndarray:
        if canon is not None:
            sim = similarity(canon[STABLE_POINTS], landmarks[STABLE_POINTS])
            aff = affine_fit(canon[STABLE_POINTS], landmarks[STABLE_POINTS])
            ratio = abs(np.linalg.det(aff[:, :2])) / max(abs(np.linalg.det(sim[:, :2])), 1e-9)
            return to3(aff if 0.55 < ratio < 1.8 else sim)
        if mask.anchors:
            src = np.array([a.point for a in mask.anchors], dtype=np.float64)
            dst = np.array([group_center(landmarks, a.landmarks) for a in mask.anchors], dtype=np.float64)
            return to3(similarity(src, dst))
        bx, by, bw, bh = mask.content_box
        fw = face_width(landmarks)
        roll = face_roll(landmarks)
        up = np.array([math.sin(roll), -math.cos(roll)])
        slot = mask.slot if mask.slot in SLOT_WIDTH else "free"
        target = cls._slot_target(slot, landmarks, up, fw)
        ratio = mask.width_ratio or SLOT_WIDTH[slot]
        scale = ratio * fw / max(bw, 1)
        if mask.pivot is not None:
            px, py = mask.pivot
        elif slot == "head":
            px, py = bx + bw / 2.0, by + bh
        else:
            px, py = bx + bw / 2.0, by + bh / 2.0
        cos, sin = math.cos(roll) * scale, math.sin(roll) * scale
        return np.array(
            [
                [cos, -sin, target[0] - cos * px + sin * py],
                [sin, cos, target[1] - sin * px - cos * py],
                [0.0, 0.0, 1.0],
            ]
        )

    def _light_gain(self, frame: np.ndarray, landmarks: np.ndarray, mask: Mask, amount: float) -> float:
        if amount <= 0.01:
            return 1.0
        pts = landmarks[FACE_OVAL]
        x0, y0 = np.maximum(pts.min(axis=0).astype(int), 0)
        x1, y1 = pts.max(axis=0).astype(int)
        crop = frame[y0 : max(y1, y0 + 2), x0 : max(x1, x0 + 2)]
        if crop.size == 0:
            return 1.0
        small = cv2.resize(crop, (24, 24), interpolation=cv2.INTER_AREA)
        luma = float(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).mean())
        self._luma = luma if self._luma is None else 0.85 * self._luma + 0.15 * luma
        ratio = (self._luma + 20.0) / (mask.mean_luma + 20.0)
        return float(np.clip(ratio ** (0.8 * amount), 0.55, 1.5))

    @staticmethod
    def _merge_face(warped: np.ndarray, x0: int, y0: int, layer) -> np.ndarray:
        lh, lw = layer.alpha.shape
        fx0, fy0 = max(layer.x0, x0), max(layer.y0, y0)
        fx1, fy1 = min(layer.x0 + lw, x0 + warped.shape[1]), min(layer.y0 + lh, y0 + warped.shape[0])
        if fx1 <= fx0 or fy1 <= fy0:
            return warped
        sl_l = (slice(fy0 - layer.y0, fy1 - layer.y0), slice(fx0 - layer.x0, fx1 - layer.x0))
        sl_w = (slice(fy0 - y0, fy1 - y0), slice(fx0 - x0, fx1 - x0))
        cover = layer.cover[sl_l][..., None]
        inner = layer.inner[sl_l]
        face = np.dstack([layer.bgr[sl_l].astype(np.float32) * inner[..., None], inner * 255.0])
        merged = warped[sl_w].astype(np.float32) * (1.0 - cover) + face * cover
        out = warped.copy()
        out[sl_w] = np.clip(merged, 0, 255).astype(np.uint8)
        return out

    def draw(
        self,
        frame: np.ndarray,
        mask: Mask,
        landmarks: np.ndarray,
        settings: Settings,
        adjust: tuple[float, float, float, float] | None = None,
        opacity: float | None = None,
        expression: tuple[FaceWarpRenderer, np.ndarray] | None = None,
    ) -> None:
        height, width = frame.shape[:2]
        fw = face_width(landmarks)
        if adjust is None:
            adjust = (settings.mask_scale, settings.mask_rotation, settings.mask_offset_x, settings.mask_offset_y)
        if opacity is None:
            opacity = float(np.clip(settings.mask_opacity, 0.0, 1.0))
        canon = expression[1] if expression is not None else None
        base = self._base(mask, landmarks, canon)
        center = landmarks[FACE_OVAL].mean(axis=0)
        roll = face_roll(landmarks)
        right = np.array([math.cos(roll), math.sin(roll)])
        down = np.array([-math.sin(roll), math.cos(roll)])
        offset = (right * adjust[2] + down * adjust[3]) * fw
        adj = adjustment(center, adjust[0], adjust[1], offset)
        full = adj @ base
        scale = math.sqrt(abs(np.linalg.det(full[:2, :2])))
        levels = self._pyramid(mask)
        level = int(np.clip(math.floor(math.log2(1.0 / max(scale, 1e-3))), 0, len(levels) - 1))
        image = levels[level]
        factor = 0.5**level
        m = full @ np.diag([1.0 / factor, 1.0 / factor, 1.0])

        h, w = image.shape[:2]
        corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float64)
        moved = corners @ m[:2, :2].T + m[:2, 2]
        x0 = int(max(0, math.floor(moved[:, 0].min())))
        y0 = int(max(0, math.floor(moved[:, 1].min())))
        x1 = int(min(width, math.ceil(moved[:, 0].max())))
        y1 = int(min(height, math.ceil(moved[:, 1].max())))
        if x1 - x0 < 4 or y1 - y0 < 4:
            return
        shift = m.copy()
        shift[0, 2] -= x0
        shift[1, 2] -= y0
        warped = cv2.warpAffine(
            image,
            shift[:2],
            (x1 - x0, y1 - y0),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )
        softness = float(np.clip(settings.edge_softness, 0.0, 1.0))
        if softness > 0.35:
            warped = cv2.GaussianBlur(warped, (0, 0), 0.4 + softness)
        if expression is not None:
            dst = apply_points(adj, landmarks[:468])
            layer = expression[0].render(frame, mask.mask_id + "#expr", mask.image, canon, dst, landmarks, settings, False)
            if layer is not None:
                warped = self._merge_face(warped, x0, y0, layer)
        gain = self._light_gain(frame, landmarks, mask, float(settings.light_match))
        alpha = warped[:, :, 3].astype(np.float32) / 255.0 * opacity
        pre = warped[:, :, :3].astype(np.float32) * (gain * opacity)
        blend_premultiplied(frame, x0, y0, pre, alpha)
