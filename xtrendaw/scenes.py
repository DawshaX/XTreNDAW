"""المشاهد — توليد خلفيات برمجيًا (بلا أي مفتاح API) + مشاهد بهوية المشروع.

الهدف: الإنتاج ما يقفش أبدًا بسبب نفاد حصة أو غياب مفتاح.
لو PEXELS_API_KEY موجود بيتجرب الأول، وإلا نرجع للتوليد المحلي فورًا.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import settings, textrender

W, H = settings.VIDEO["width"], settings.VIDEO["height"]

# لوحات ألوان حسب نوع المقطع — هوية بصرية ثابتة
PALETTES = {
    "hook":   [("#0a0a2a", "#3d0a4a"), ("#ff1e1e", "#ffb347")],
    "fact1":  [("#050d1f", "#0f3b5c"), ("#ffb347", "#ffe9b0")],
    "fact2":  [("#10071f", "#3a0f4a"), ("#7bdff2", "#b99cff")],
    "fact3":  [("#0b1a0f", "#14452f"), ("#ffd166", "#06d6a0")],
    "outro":  [("#1a0505", "#3d0a0a"), ("#ff1e1e", "#ffd166")],
}


def _seeded(seed: str) -> np.random.Generator:
    """بذرة ثابتة من نص — نفس الموضوع يطلع بنفس الشكل (قابل للتكرار)."""
    h = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16)
    return np.random.default_rng(h)


def _hex(rgb: str) -> tuple[int, int, int]:
    rgb = rgb.lstrip("#")
    return tuple(int(rgb[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def render_bg(out_path: Path, kind: str, seed: str) -> Path:
    """خلفية 1080×1920 مولّدة رياضيًا: تدرّج + سُدُم + نجوم + فينييت."""
    rng = _seeded(f"{seed}:{kind}")
    base, accent = PALETTES.get(kind, PALETTES["fact1"])
    top, bottom = _hex(base[0]), _hex(base[1])

    # تدرّج رأسي
    t = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    grad = np.stack(
        [np.linspace(top[i], bottom[i], H, dtype=np.float32) for i in range(3)],
        axis=-1,
    )[:, None, :]
    img = np.repeat(grad, W, axis=1)

    # سُدم: بقع ضبابية بلون مميز
    glow = np.zeros((H, W), dtype=np.float32)
    for _ in range(3):
        cx, cy = rng.integers(0, W), rng.integers(0, H)
        r = rng.integers(W // 4, W // 2)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (r ** 2)
        glow += np.exp(-d2) * rng.uniform(0.35, 0.8)
    glow = np.clip(glow, 0, 1.5)
    acc = np.array(_hex(accent[1]), dtype=np.float32)
    img = img + glow[:, :, None] * acc[None, None, :] * 0.35

    img = np.clip(img, 0, 255).astype(np.uint8)
    out = Image.fromarray(img, "RGB")

    # نجوم
    draw = ImageDraw.Draw(out)
    for _ in range(160):
        x, y = int(rng.integers(0, W)), int(rng.integers(0, H))
        s = int(rng.integers(1, 3))
        a = int(rng.integers(90, 235))
        draw.ellipse([x, y, x + s, y + s], fill=(255, 255, 255, a))

    # فينييت (تعتيم الأطراف) عشان النص يقرا
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-W * 0.25, -H * 0.1, W * 1.25, H * 1.1], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(220))
    black = Image.new("RGB", (W, H), (0, 0, 0))
    out = Image.composite(out, black, vig)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path, "PNG")
    return out_path


STYLE = {
    "hook":  {"font_size": 96, "y_ratio": 0.50, "max_w": 0.84, "fill": "#FFFFFF"},
    "outro": {"font_size": 88, "y_ratio": 0.46, "max_w": 0.82, "fill": "#ffd166"},
    "fact":  {"font_size": 74, "y_ratio": 0.56, "max_w": 0.86, "fill": "#FFFFFF"},
}


def render_scene(out_path: Path, kind: str, text: str, seed: str,
                 chip: str = "") -> Path:
    """مشهد كامل 1080×1920: خلفية مولّدة + نص عربي مشكّل (+ شارة للحقائق)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bg_path = render_bg(out_path.with_suffix(".bg.png"), kind, seed)
    base = Image.open(bg_path).convert("RGB")
    st = STYLE.get("fact" if kind.startswith("fact") else kind, STYLE["fact"])

    def paste(layer_path: Path) -> None:
        layer = Image.open(layer_path)
        base.paste(layer, (0, 0), layer)

    if chip:
        paste(textrender.text_image(
            chip, out_path.with_suffix(".chip.png"), canvas=(W, H),
            font_size=58, fill="#ffd166", y_ratio=st["y_ratio"] - 0.16,
            max_width_ratio=0.8,
        ))

    paste(textrender.text_image(
        text or settings.BRAND["name"], out_path.with_suffix(".txt.png"),
        canvas=(W, H), font_size=st["font_size"], y_ratio=st["y_ratio"],
        max_width_ratio=st["max_w"], fill=st["fill"],
    ))

    base.save(out_path, "PNG")
    return out_path
