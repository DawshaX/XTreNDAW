"""استيكرات دلالية — أيقونات متوهجة توصّف كلمات كلام الله لحظة نطقها.

كل أيقونة مرسومة إجرائيًا (هلال، نجمة، قلب، مسجد، مشكاة، كتاب، مطر،
نخلة، لهب، جبل، شعاع) بلون روح الحلقة — تظهر مع الكلمة المطابقة وتختفي.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

S = 220  # مقاس الكانفاس

# جذور كلمية → أيقونة
KEYMAP = [
    (["الله", "لله", "إله", "رب", "رحمن", "رحيم", "قدوس", "عزيز"], "rays"),
    (["نور", "ضياء", "مشك", "سراج", "مصباح", "صبح"], "lamp"),
    (["جن", "فردوس", "نهر", "ظل", "ثمر"], "palm"),
    (["نار", "جحيم", "سعير", "عذاب", "حرق"], "flame"),
    (["مطر", "ماء", "غيث", "أنهار", "بحر", "سيل"], "rain"),
    (["قلب", "صدر", "حب", "مودة"], "heart"),
    (["كتاب", "قرآن", "ذكر", "صحف", "آية", "سورة"], "book"),
    (["مسجد", "صلا", "سجد", "ركع", "أذن"], "mosque"),
    (["هلال", "شهر", "رمضان", "قمر", "ليل"], "crescent"),
    (["سلام", "أمن", "رحمة", "بركة"], "star8"),
    (["جبل", "طور", "أرض", "رواسي"], "mountain"),
    (["شمس", "نهار", "فلق", "ضحى"], "sun"),
    (["ملك", "عرش", "كرسي", "سماء", "نجم", "كوكب"], "star8"),
    (["يد", "دعا", "كف", "ابتهل"], "hands"),
]


def _glow_base(rgb: str) -> tuple[Image.Image, ImageDraw.ImageDraw, tuple]:
    r = int(rgb[0:2], 16), int(rgb[2:4], 16), int(rgb[4:6], 16)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    c = S // 2
    for rr, a in [(105, 14), (85, 22), (65, 34)]:
        d.ellipse([c - rr, c - rr, c + rr, c + rr], fill=(*r, a))
    return img, d, r


def _icon(kind: str, rgb: str) -> Image.Image:
    img, d, (r, g, b) = _glow_base(rgb)
    c = S // 2
    gold = (255, 214, 120, 255)
    white = (255, 250, 240, 255)
    if kind == "crescent":
        d.ellipse([c - 62, c - 62, c + 62, c + 62], fill=gold)
        d.ellipse([c - 38, c - 70, c + 78, c + 46], fill=(0, 0, 0, 0))
        # نجمة صغيرة جنب الهلال
        _star(d, c + 58, c + 34, 16, gold)
    elif kind == "star8" or kind == "rays":
        n = 8 if kind == "star8" else 12
        for i in range(n):
            a = math.pi * 2 * i / n
            x2, y2 = c + 78 * math.cos(a), c + 78 * math.sin(a)
            d.line([(c, c), (x2, y2)], fill=gold, width=7)
        d.ellipse([c - 26, c - 26, c + 26, c + 26], fill=white)
    elif kind == "heart":
        d.ellipse([c - 58, c - 46, c + 2, c + 14], fill=gold)
        d.ellipse([c - 2, c - 46, c + 58, c + 14], fill=gold)
        d.polygon([(c - 56, c - 8), (c + 56, c - 8), (c, c + 66)], fill=gold)
    elif kind == "mosque":
        d.rectangle([c - 60, c - 6, c + 60, c + 62], fill=gold)
        d.pieslice([c - 48, c - 66, c + 48, c + 30], 180, 360, fill=gold)
        d.rectangle([c - 78, c - 40, c - 66, c + 62], fill=gold)
        d.rectangle([c + 66, c - 40, c + 78, c + 62], fill=gold)
        d.ellipse([c - 84, c - 56, c - 60, c - 32], fill=gold)
        d.ellipse([c + 60, c - 56, c + 84, c - 32], fill=gold)
    elif kind == "lamp":
        d.polygon([(c - 34, c - 20), (c + 34, c - 20), (c + 20, c + 44),
                   (c - 20, c + 44)], fill=gold)
        d.ellipse([c - 22, c - 58, c + 22, c - 14], fill=(255, 240, 170, 255))
        d.line([(c, c - 78), (c, c - 58)], fill=gold, width=6)
        for a in range(0, 360, 45):
            x2 = c + 44 * math.cos(math.radians(a))
            y2 = c - 36 + 44 * math.sin(math.radians(a))
            d.line([(c, c - 36), (x2, y2)], fill=(255, 240, 170, 200), width=4)
    elif kind == "book":
        d.polygon([(c - 66, c - 34), (c, c - 16), (c, c + 56), (c - 66, c + 38)],
                  fill=gold)
        d.polygon([(c + 66, c - 34), (c, c - 16), (c, c + 56), (c + 66, c + 38)],
                  fill=(255, 236, 170, 255))
        for i in range(4):
            y = c - 4 + i * 14
            d.line([(c - 54, y), (c - 12, y + 10)], fill=(120, 70, 10, 200), width=4)
    elif kind == "rain":
        d.ellipse([c - 52, c - 52, c + 20, c + 4], fill=white)
        d.ellipse([c - 16, c - 62, c + 56, c + 4], fill=white)
        for i, x in enumerate((-40, 0, 40)):
            d.line([(c + x, c + 26), (c + x - 10, c + 62)],
                   fill=(140, 200, 255, 255), width=8)
    elif kind == "palm":
        d.line([(c, c + 70), (c + 6, c - 10)], fill=(200, 150, 80, 255), width=12)
        for a in (-150, -110, -70, -30):
            x2 = c + 6 * math.cos(math.radians(a)) * 1.4
            y2 = c - 10 + 62 * math.sin(math.radians(a))
            d.line([(c + 4, c - 10), (int(c + 4 + 70 * math.cos(math.radians(a))),
                   int(c - 10 + 46 * math.sin(math.radians(a))))],
                   fill=(120, 220, 130, 255), width=10)
    elif kind == "flame":
        d.pieslice([c - 44, c - 30, c + 44, c + 58], 0, 180, fill=(255, 120, 40, 255))
        d.polygon([(c - 44, c + 14), (c, c - 74), (c + 44, c + 14)],
                  fill=(255, 120, 40, 255))
        d.polygon([(c - 22, c + 16), (c, c - 26), (c + 22, c + 16)],
                  fill=(255, 220, 120, 255))
    elif kind == "mountain":
        d.polygon([(c - 76, c + 56), (c - 14, c - 62), (c + 30, c + 56)], fill=gold)
        d.polygon([(c + 4, c + 56), (c + 48, c - 26), (c + 80, c + 56)],
                  fill=(255, 236, 170, 230))
        d.polygon([(c - 30, c - 34), (c - 14, c - 62), (c + 2, c - 34)], fill=white)
    elif kind == "sun":
        d.ellipse([c - 40, c - 40, c + 40, c + 40], fill=(255, 220, 110, 255))
        for a in range(0, 360, 30):
            x1 = c + 52 * math.cos(math.radians(a))
            y1 = c + 52 * math.sin(math.radians(a))
            x2 = c + 80 * math.cos(math.radians(a))
            y2 = c + 80 * math.sin(math.radians(a))
            d.line([(x1, y1), (x2, y2)], fill=(255, 220, 110, 255), width=7)
    elif kind == "hands":
        for sx in (-1, 1):
            d.pieslice([c - 46 if sx < 0 else c - 6, c - 40,
                        c + 6 if sx < 0 else c + 56, c + 40],
                       0, 180, fill=gold)
            d.ellipse([c - 40 if sx < 0 else c, c - 62,
                       c - 4 if sx < 0 else c + 40, c - 6], fill=gold)
    return img


def _star(d, x, y, r, col):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.45
        a = math.pi / 5 * i - math.pi / 2
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    d.polygon(pts, fill=col)


_CACHE: dict[str, Path] = {}


import re as _re
_TASH = _re.compile(r"[\u064B-\u0652\u0670\u0640\u06D6-\u06ED]")


def _plain(t: str) -> str:
    return _TASH.sub("", t)


def sticker_for(text: str, rgb: str) -> str | None:
    """يرجع اسم الأيقونة المطابقة لأي كلمة في النص، أو None."""
    t = _plain(text)
    for keys, icon in KEYMAP:
        for k in keys:
            if k in t:
                return icon
    return None


def sticker_png(icon: str, rgb: str, out_dir: Path) -> Path:
    key = f"{icon}-{rgb}"
    if key in _CACHE and _CACHE[key].exists():
        return _CACHE[key]
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"stk-{key}.png"
    _icon(icon, rgb).save(p)
    _CACHE[key] = p
    return p
