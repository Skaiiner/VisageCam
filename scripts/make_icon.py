# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 1024
TARGET = Path(__file__).resolve().parents[1] / "src" / "visagecam" / "assets"


def gradient(size: int) -> Image.Image:
    image = Image.new("RGB", (size, size))
    pixels = image.load()
    start, end = (124, 108, 255), (53, 199, 240)
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2.0 * (size - 1))
            pixels[x, y] = tuple(int(a + (b - a) * t) for a, b in zip(start, end))
    return image


def build() -> Image.Image:
    base = gradient(SIZE).convert("RGBA")
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=230, fill=255)
    base.putalpha(mask)
    draw = ImageDraw.Draw(base)
    font = None
    for name in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            font = ImageFont.truetype(name, 470)
            break
        except OSError:
            continue
    font = font or ImageFont.load_default()
    text = "VC"
    box = draw.textbbox((0, 0), text, font=font)
    x = (SIZE - (box[2] - box[0])) / 2 - box[0]
    y = (SIZE - (box[3] - box[1])) / 2 - box[1] - 10
    draw.text((x, y), text, font=font, fill=(11, 13, 18, 255))
    return base


def main() -> int:
    TARGET.mkdir(parents=True, exist_ok=True)
    image = build()
    image.resize((256, 256), Image.LANCZOS).save(TARGET / "visagecam.png")
    image.save(
        TARGET / "visagecam.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(TARGET / "visagecam.ico")
    return 0


if __name__ == "__main__":
    sys.exit(main())
