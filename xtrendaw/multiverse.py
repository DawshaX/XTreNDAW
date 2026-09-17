# -*- coding: utf-8 -*-
"""محرك الأنماط (Multiverse) — DNA بصري فريد لكل حلقة.

مليارات التوليفات: لوحة ألوان × تدرّج سينمائي × حركة كاميرا ×
جسيمات بعمقين (بارالاكس 3D) × انتقال × حبيبة × فينييت.
البذرة = هوية الحلقة ← نفس الحلقة تعيد نفس الروح، وأي حلقة جديدة
تعيش جوًا مختلفًا تمامًا. حر طليق — بلا نمط ثابت.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# 10 لوحات ألوان — كل لوحة لها بصمة تلوين خاصة
PALETTES: dict[str, dict] = {
    "gold":    {"rgb": "#e8b64c", "cb": "rs=0.07:rm=0.05:rh=0.03:bs=-0.04"},
    "emerald": {"rgb": "#3fd68f", "cb": "gs=0.06:gm=0.04:gh=0.02:rs=-0.03:bm=0.02"},
    "royal":   {"rgb": "#5b8def", "cb": "bs=0.08:bm=0.05:bh=0.03:rs=-0.04:gm=-0.02"},
    "rose":    {"rgb": "#ef7ba8", "cb": "rs=0.07:rm=0.03:rh=0.04:bs=0.02:gs=-0.03"},
    "silver":  {"rgb": "#c9d6e8", "cb": "bs=0.04:bm=0.02:gs=0.02:rs=-0.02"},
    "sunset":  {"rgb": "#ff8a4c", "cb": "rs=0.09:rm=0.04:rh=0.02:bs=-0.06:bm=-0.03"},
    "ocean":   {"rgb": "#41c7d9", "cb": "bs=0.06:bm=0.05:gs=0.03:bh=0.02:rs=-0.03"},
    "mystic":  {"rgb": "#b28aff", "cb": "bs=0.06:rs=0.04:bm=0.05:rh=0.03:gm=-0.03"},
    "amber":   {"rgb": "#ffc96b", "cb": "rs=0.06:rm=0.06:rh=0.04:bs=-0.05:gs=0.02"},
    "aurora":  {"rgb": "#7ce8c0", "cb": "gs=0.05:gm=0.03:bs=0.04:gh=0.02:rs=-0.02"},
}

# 6 تدرجات سينمائية
GRADES: dict[str, str] = {
    "calm":  ("eq=contrast=1.06:saturation=1.07"),
    "soft":  ("eq=contrast=1.05:saturation=1.08:brightness=0.01"),
    "red":   ("eq=contrast=1.08:saturation=1.22:brightness=0.01"),
    "teal":  ("eq=contrast=1.09:saturation=1.12,"
              "colorbalance=bs=0.08:bm=0.05:rs=0.06:rm=0.03"),
    "noir":  ("eq=contrast=1.14:saturation=0.45:brightness=0.02"),
    "night": ("eq=contrast=1.07:saturation=0.95:brightness=-0.03,"
              "colorbalance=bs=0.09:bm=0.06:rs=-0.04"),
}

# 4 انتقالات لقطة
TRANSITIONS = ["black", "white", "palette", "quick"]
# 10 انتقالات مزج احترافية (xfade) — مونتاج استوديو
XFADES = ["fade", "wipeleft", "slideup", "circleopen", "radial",
          "dissolve", "smoothleft", "squeezev", "hblur", "zoomin"]


def _hex(rgb: str) -> tuple[int, int, int]:
    return (int(rgb[1:3], 16), int(rgb[3:5], 16), int(rgb[5:7], 16))


def style_dna(seed: str) -> dict:
    """DNA فريد من بذرة الحلقة — حتميّ ومتنوع بلا حدود."""
    h = int(hashlib.sha256(seed.encode()).hexdigest()[:16], 16)
    pal = list(PALETTES)[h % len(PALETTES)]
    return {
        "seed": seed,
        "palette": pal,
        "rgb": PALETTES[pal]["rgb"],
        "cb": PALETTES[pal]["cb"],
        "grade": list(GRADES)[(h >> 8) % len(GRADES)],
        "motion": (h >> 12) % 8,          # 8 حركات كاميرا
        "particles": (h >> 16) % 5,       # غبار/بوكة/نجوم/مطر/بلا
        "rise": bool((h >> 20) & 1),      # الجسيمات تصعد أم تهبط
        "transition": TRANSITIONS[(h >> 22) % 4],
        "grain": 1 + (h >> 26) % 3,       # حبيبة فيلم 1-3
        "vig": ["PI/6", "PI/5", "PI/4"][(h >> 30) % 3],
        "p_speed": 14 + (h >> 34) % 18,   # سرعة الجسيمات
        "live_zoom": ((h >> 38) & 1) == 1,  # تقريب بطيء على اللقطة الحية (عمق)
        "xtrans": XFADES[(h >> 42) % len(XFADES)],
        "depth": bool((h >> 46) & 1),        # طبقة عمق: خلفية ضبابية + نافذة حادة
        "typo": ["poetic", "bold"][(h >> 48) % 2],  # خط صغير شاعري / تايبوغرافيا ضخمة
        "ramp": bool((h >> 50) & 1),          # نبض سرعة بين المشاهد
        "intro": ["logo", "pop", "logo"][(h >> 52) % 3],
        # تخطيط هيكلي: كل حلقة بتتبنى بشكل مختلف مش بس بألوان
        "layout": ["full", "depth", "letterbox", "circle",
                   "depth"][(h >> 56) % 5],
    }


def rounded_mask(out_path: Path, width: int = 900, height: int = 1600,
                  radius: int = 64) -> Path:
    """قناع نافذة مستديرة الزوايا لطبقة العمق."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("L", (width, height), 0)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, width - 1, height - 1], radius=radius, fill=255)
    # حلقة فاصل شفافة قرب الحافة — الحدود تُرى دائمًا فوق أي لقطة
    d.rounded_rectangle([10, 10, width - 11, height - 11],
                        radius=max(10, radius - 10), outline=0, width=8)
    img.save(out_path)
    return out_path


def circle_mask(out_path: Path, width: int = 900, height: int = 1600) -> Path:
    """قناع كوة دائرية فوق/وسط النافذة — بنفس أبعاد الطبقة الحادة."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("L", (width, height), 0)
    d = ImageDraw.Draw(img)
    d.ellipse([0, 300, width - 1, 300 + width - 1], fill=255)
    d.ellipse([10, 310, width - 11, 290 + width - 1], outline=0, width=8)
    img.save(out_path)
    return out_path


def particles_png(dna: dict, out_dir: Path,
                  width: int = 1080, height: int = 1920) -> list[Path]:
    """طبقتا جسيمات بعمقين (بارالاكس) — png بارتفاع 2H يتكرر كل H."""
    kind = dna["particles"]
    if kind == 4:
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    col = _hex(dna["rgb"])
    rng = np.random.default_rng(
        int(hashlib.sha256(("p" + dna["seed"]).encode()).hexdigest()[:8], 16))
    paths: list[Path] = []
    for layer, (n, r_max, a_max) in enumerate([
            (110, 4, 120),   # بعيد: غبار واسع خفيف
            (45, 9, 215)]):  # قريب: واضح لامع
        img = Image.new("RGBA", (width, height * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for _ in range(n):
            x = int(rng.uniform(0, width))
            y = int(rng.uniform(0, height))
            r = float(rng.uniform(1, r_max))
            a = int(rng.uniform(a_max * 0.4, a_max))
            c = (col[0], col[1], col[2], a)
            for yy in (y, y + height):  # تكرار رأسي سلس
                if kind == 1:      # بوكة دائرية ناعمة
                    d.ellipse([x - r * 2, yy - r * 2, x + r * 2, yy + r * 2],
                              fill=(col[0], col[1], col[2], max(8, a // 3)))
                elif kind == 2:    # نجوم: نقطة + بريق
                    d.ellipse([x - r / 2, yy - r / 2, x + r / 2, yy + r / 2],
                              fill=c)
                    d.line([x - r * 2, yy, x + r * 2, yy],
                           fill=(col[0], col[1], col[2], a // 2), width=1)
                    d.line([x, yy - r * 2, x, yy + r * 2],
                           fill=(col[0], col[1], col[2], a // 2), width=1)
                elif kind == 3:    # مطر نور: شريط رفيع
                    ln = r * 6
                    d.line([x, yy - ln, x + 1, yy + ln], fill=c, width=1)
                else:              # غبار ذهبي
                    d.ellipse([x - r, yy - r, x + r, yy + r], fill=c)
        if kind in (1, 2):
            img = img.filter(ImageFilter.GaussianBlur(1.2 if layer == 0 else 0.6))
        p = out_dir / f"dust{layer}.png"
        img.save(p)
        paths.append(p)
    return paths
