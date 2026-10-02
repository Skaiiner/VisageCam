# Copyright (c) 2026 Skain. Todos los derechos reservados.

import math
from dataclasses import dataclass

import cv2
import numpy as np

from visagecam.config import Settings
from visagecam.masks.model import Mask
from visagecam.processing.blend import blend_alpha
from visagecam.processing.landmarks import (
    EYE_RING_LEFT,
    EYE_RING_RIGHT,
    FACE_OVAL,
    LIPS_INNER,
    face_width,
    mesh_triangles,
    mouth_open_ratio,
)
from visagecam.processing.transforms import adjustment, apply_points


@dataclass
class FaceLayer:
    x0: int
    y0: int
    bgr: np.ndarray
    alpha: np.ndarray
    cover: np.ndarray
    inner: np.ndarray


class FaceTexture:
    def __init__(self, image: np.ndarray, points: np.ndarray) -> None:
        points = points.astype(np.float32)
        self.image = image
        self.width = max(face_width(points), 1.0)
        self.triangles = mesh_triangles()
        self.levels: list[tuple[np.ndarray, np.ndarray]] = []
        current, scale = image, 1.0
        for _ in range(4):
            self.levels.append((current, (points * scale)[self.triangles]))
            if min(current.shape[:2]) < 320:
                break
            current = cv2.resize(
                current, (current.shape[1] // 2, current.shape[0] // 2), interpolation=cv2.INTER_AREA
            )
            scale *= 0.5
        oval = np.zeros(image.shape[:2], np.uint8)
        cv2.fillConvexPoly(oval, np.round(points[FACE_OVAL]).astype(np.int32), 255)
        lab = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2LAB)
        mean, std = cv2.meanStdDev(lab, mask=oval)
        self.mean = mean.ravel().astype(np.float32)
        self.std = np.maximum(std.ravel(), 2.0).astype(np.float32)

    def pick_level(self, live_width: float) -> tuple[np.ndarray, np.ndarray]:
        level = int(math.floor(math.log2(max(self.width / max(live_width, 1.0), 1.0))))
        return self.levels[min(max(level, 0), len(self.levels) - 1)]


def _smoothstep(edge0: float, edge1: float, x: float) -> float:
    t = min(max((x - edge0) / (edge1 - edge0), 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


class FaceWarpRenderer:
    def __init__(self) -> None:
        self._textures: dict[str, FaceTexture] = {}
        self._live_mean: np.ndarray | None = None
        self._live_std: np.ndarray | None = None

    def texture(self, key: str, image: np.ndarray, points: np.ndarray) -> FaceTexture:
        tex = self._textures.get(key)
        if tex is None or tex.image is not image:
            tex = FaceTexture(image, points)
            self._textures[key] = tex
        return tex

    def reset(self) -> None:
        self._live_mean = None
        self._live_std = None

    @staticmethod
    def _coefficients(dst_tri: np.ndarray, src_tri: np.ndarray):
        p0, p1, p2 = dst_tri[:, 0], dst_tri[:, 1], dst_tri[:, 2]
        e1, e2 = p1 - p0, p2 - p0
        det = e1[:, 0] * e2[:, 1] - e2[:, 0] * e1[:, 1]
        det = np.where(np.abs(det) < 1e-6, 1e9, det)[:, None]
        s0, s1, s2 = src_tri[:, 0], src_tri[:, 1], src_tri[:, 2]
        f1, f2 = s1 - s0, s2 - s0
        a = (f1 * e2[:, 1:2] - f2 * e1[:, 1:2]) / det
        b = (-f1 * e2[:, 0:1] + f2 * e1[:, 0:1]) / det
        c = s0 - a * p0[:, 0:1] - b * p0[:, 1:2]
        return a, b, c

    def render(
        self,
        frame: np.ndarray,
        key: str,
        image: np.ndarray,
        src_points: np.ndarray,
        dst: np.ndarray,
        live: np.ndarray,
        settings: Settings,
        photo: bool,
    ) -> FaceLayer | None:
        height, width = frame.shape[:2]
        pad = 3
        x0 = int(max(0, math.floor(dst[:, 0].min()) - pad))
        y0 = int(max(0, math.floor(dst[:, 1].min()) - pad))
        x1 = int(min(width, math.ceil(dst[:, 0].max()) + pad))
        y1 = int(min(height, math.ceil(dst[:, 1].max()) + pad))
        bw, bh = x1 - x0, y1 - y0
        if bw < 24 or bh < 24:
            return None
        tex = self.texture(key, image, src_points)
        live_width = face_width(dst)
        level_image, src_tri = tex.pick_level(live_width)
        local = dst - np.array([x0, y0], dtype=np.float32)
        dst_tri = local[tex.triangles]

        shrink = 0.5 if min(bw, bh) >= 120 else 1.0
        sw, sh = max(8, int(round(bw * shrink))), max(8, int(round(bh * shrink)))
        sx, sy = sw / bw, sh / bh
        factor = np.array([sx, sy], dtype=np.float32)

        idmap = np.zeros((sh, sw), np.int32)
        poly = np.round(dst_tri * factor * 16).astype(np.int32)
        for i in range(len(poly)):
            cv2.fillConvexPoly(idmap, poly[i], i + 1, cv2.LINE_8, 4)
        ys, xs = np.nonzero(idmap)
        if len(xs) < 32:
            return None
        tri = idmap[ys, xs] - 1
        a, b, c = self._coefficients(dst_tri, src_tri)
        fx = (xs.astype(np.float32) + 0.5) / sx - 0.5
        fy = (ys.astype(np.float32) + 0.5) / sy - 0.5
        map_x = np.full((sh, sw), -1.0, np.float32)
        map_y = np.full((sh, sw), -1.0, np.float32)
        map_x[ys, xs] = a[tri, 0] * fx + b[tri, 0] * fy + c[tri, 0]
        map_y[ys, xs] = a[tri, 1] * fx + b[tri, 1] * fy + c[tri, 1]
        if (sw, sh) != (bw, bh):
            map_x = cv2.resize(map_x, (bw, bh), interpolation=cv2.INTER_LINEAR)
            map_y = cv2.resize(map_y, (bw, bh), interpolation=cv2.INTER_LINEAR)
        warped = cv2.remap(
            level_image, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0
        )

        k = sx
        cover = (idmap > 0).astype(np.uint8) * 255
        softness = float(np.clip(settings.edge_softness, 0.0, 1.0))
        sigma = max(0.8, live_width * ((0.012 + 0.03 * softness) if photo else 0.03) * k)
        erode = max(1, int(live_width * 0.02 * k)) if photo else max(1, int(2.3 * sigma))
        cover = cv2.erode(cover, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erode * 2 + 1, erode * 2 + 1)))
        cover = cv2.GaussianBlur(cover, (0, 0), sigma)
        if (sw, sh) != (bw, bh):
            cover = cv2.resize(cover, (bw, bh), interpolation=cv2.INTER_LINEAR)
        inner = warped[:, :, 3]

        if settings.keep_eyes_mouth:
            hole = np.zeros((sh, sw), np.uint8)
            if photo:
                for ring in (EYE_RING_LEFT, EYE_RING_RIGHT):
                    cv2.fillPoly(
                        hole, [np.round(local[ring] * factor * 16).astype(np.int32)], 255, cv2.LINE_AA, 4
                    )
            reveal = _smoothstep(0.016, 0.055, mouth_open_ratio(live))
            if reveal > 0.02:
                mouth = np.zeros((sh, sw), np.uint8)
                cv2.fillPoly(
                    mouth, [np.round(local[LIPS_INNER] * factor * 16).astype(np.int32)], 255, cv2.LINE_AA, 4
                )
                hole = np.maximum(hole, cv2.convertScaleAbs(mouth, alpha=reveal))
            if hole.any():
                grow = max(1, int(live_width * 0.016 * k))
                hole = cv2.dilate(
                    hole, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (grow * 2 + 1, grow * 2 + 1))
                )
                hole = cv2.GaussianBlur(hole, (0, 0), max(1.0, live_width * 0.013 * k))
                if (sw, sh) != (bw, bh):
                    hole = cv2.resize(hole, (bw, bh), interpolation=cv2.INTER_LINEAR)
                inner = cv2.multiply(inner, 255 - hole, scale=1.0 / 255.0)

        layer = warped[:, :, :3]
        strength = float(np.clip(settings.color_match, 0.0, 1.0))
        if photo and strength > 0.01:
            layer = self._match_color(layer, frame[y0:y1, x0:x1], cover, tex, strength)
        return FaceLayer(x0, y0, layer, cv2.multiply(cover, inner, scale=1.0 / 255.0), cover, inner)

    def draw(self, frame: np.ndarray, mask: Mask, landmarks: np.ndarray, settings: Settings) -> None:
        fw = face_width(landmarks)
        center = landmarks[FACE_OVAL].mean(axis=0)
        adj = adjustment(
            center,
            settings.mask_scale,
            settings.mask_rotation,
            (settings.mask_offset_x * fw, settings.mask_offset_y * fw),
        )
        dst = apply_points(adj, landmarks[:468])
        layer = self.render(
            frame, mask.mask_id, mask.image, mask.face_landmarks, dst, landmarks, settings, True
        )
        if layer is None:
            return
        alpha = cv2.convertScaleAbs(layer.alpha, alpha=float(np.clip(settings.mask_opacity, 0.0, 1.0)))
        blend_alpha(frame, layer.x0, layer.y0, layer.bgr, alpha)

    def _match_color(
        self, layer: np.ndarray, live: np.ndarray, cover: np.ndarray, tex: FaceTexture, strength: float
    ) -> np.ndarray:
        scale = 96.0 / max(live.shape[1], 1)
        small = cv2.resize(live, (96, max(1, int(live.shape[0] * scale))), interpolation=cv2.INTER_AREA)
        small_mask = cv2.resize(cover, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_AREA)
        small_mask = (small_mask > 200).astype(np.uint8) * 255
        if int(small_mask.sum() // 255) > 30:
            lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)
            mean, std = cv2.meanStdDev(lab, mask=small_mask)
            mean = mean.ravel().astype(np.float32)
            std = np.maximum(std.ravel(), 2.0).astype(np.float32)
            if self._live_mean is None:
                self._live_mean, self._live_std = mean, std
            else:
                self._live_mean = 0.75 * self._live_mean + 0.25 * mean
                self._live_std = 0.75 * self._live_std + 0.25 * std
        if self._live_mean is None:
            return layer
        ratio = np.clip(self._live_std / tex.std, 0.6, 1.5)
        ratio = 1.0 + strength * (ratio - 1.0)
        target = tex.mean + strength * (self._live_mean - tex.mean)
        ramp = np.arange(256, dtype=np.float32)[:, None]
        lut = np.clip((ramp - tex.mean) * ratio + target, 0, 255).astype(np.uint8)[:, None, :]
        lab = cv2.LUT(cv2.cvtColor(layer, cv2.COLOR_BGR2LAB), lut)
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
