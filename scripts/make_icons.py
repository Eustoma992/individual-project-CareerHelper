# -*- coding: utf-8 -*-
"""生成 PWA 图标：深蓝渐变圆角方块 + 🎓 学士帽。"""
import pathlib

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)

# Windows 自带的彩色 emoji 字体
EMOJI_FONT = pathlib.Path(r"C:\Windows\Fonts\seguiemj.ttf")

GRAD = [(37, 120, 224), (37, 120, 224), (37, 120, 224)]  # #0B2038 → #1F4E79 → #2E75B6


def gradient(size):
    """对角线三色渐变背景。"""
    base = Image.new("RGB", (size, size))
    px = base.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * size - 2)
            if t < 0.55:
                k, tt = 0, t / 0.55
            else:
                k, tt = 1, (t - 0.55) / 0.45
            c = tuple(round(GRAD[k][i] + (GRAD[k + 1][i] - GRAD[k][i]) * tt) for i in range(3))
            px[x, y] = c
    return base


def rounded(size, radius):
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def icon(size, path, radius_ratio=0.22):
    img = gradient(size)
    # 彩色 emoji 需 RGBA 图 + embedded_color
    emoji = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(emoji)
    f = ImageFont.truetype(str(EMOJI_FONT), int(size * 0.52))
    draw.text((size / 2, size * 0.53), "\U0001F393", font=f, anchor="mm", embedded_color=True)
    img = img.convert("RGBA")
    img.alpha_composite(emoji)
    img = img.convert("RGB")

    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), rounded(size, int(size * radius_ratio)))
    out.save(path)
    print("生成", path.relative_to(ROOT))


icon(192, OUT / "icon-192.png")
icon(512, OUT / "icon-512.png")
icon(180, OUT / "apple-touch-icon.png", radius_ratio=0.0)
