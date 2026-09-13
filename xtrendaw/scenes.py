"""المشاهد — هوية 2099 نيون / هاكر أخلاقي.

خلفيات مولّدة برمجيًا (بلا أي مفتاح): تدرّج فحمي + سُدم نيون + شبكة أرضية
perspective + خطوط مسح scanlines + جزيئات + فينييت مريح للعين.
لو PEXELS_API_KEY موجود بيتجرب الأول، وإلا التوليد المحلي فورًا.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import settings, textrender

W, H = settings.VIDEO["width"], settings.VIDEO["height"]

# هوية 2099: فحمي + نيون (أخضر/سماوي/ماجنتا)
PALETTES = {
    "hook":  {"bg": ("#0a0202", "#200606"), "neon": "#ff2a2a", "neon2": "#ff7a1a"},
    "fact1": {"bg": ("#0a0202", "#1c0505"), "neon": "#ff3b3b", "neon2": "#ffb347"},
    "fact2": {"bg": ("#080208", "#1c0610"), "neon": "#ff2a5e", "neon2": "#ff7a1a"},
    "fact3": {"bg": ("#0a0302", "#200a04"), "neon": "#ff7a1a", "neon2": "#ff2a2a"},
    "outro": {"bg": ("#0a0202", "#1a0a04"), "neon": "#ff3b3b", "neon2": "#ffd166"},
}


def _seeded(seed: str) -> np.random.Generator:
    h = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16)
    return np.random.default_rng(h)


def _hex(rgb: str) -> tuple[int, int, int]:
    rgb = rgb.lstrip("#")
    return tuple(int(rgb[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _grid(draw: ImageDraw.ImageDraw, neon: tuple[int, int, int]) -> None:
    """شبكة أرضية perspective تحت الأفق — توقيع 2099."""
    horizon = int(H * 0.78)
    vpx, vpy = W // 2, int(H * 0.60)
    glow = neon + (40,)
    solid = neon + (150,)

    # خطوط أفقية بتتباعد كل ما تنزل
    ys = []
    t = 0.0
    while True:
        y = int(horizon + (H - horizon) * (t ** 1.8))
        if y > H:
            break
        ys.append(y)
        t += 0.14
    for y in ys:
        draw.line([(0, y), (W, y)], fill=glow, width=3)
        draw.line([(0, y), (W, y)], fill=solid, width=1)

    # خطوط رأسية fan من نقطة التلاشي
    for i in range(-8, 9):
        x_bottom = W // 2 + i * int(W * 0.16)
        draw.line([(vpx, vpy), (x_bottom, H)], fill=glow, width=2)


def _scanlines(img: Image.Image) -> Image.Image:
    """خطوط مسح خفيفة — إحساس شاشة نيون من غير إرهاق العين."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for y in range(0, H, 6):
        d.line([(0, y), (W, y)], fill=(0, 0, 0, 18), width=2)
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def render_bg(out_path: Path, kind: str, seed: str) -> Path:
    rng = _seeded(f"{seed}:{kind}")
    pal = PALETTES.get(kind, PALETTES["fact1"])
    top, bottom = _hex(pal["bg"][0]), _hex(pal["bg"][1])
    neon, neon2 = _hex(pal["neon"]), _hex(pal["neon2"])

    # تدرّج رأسي فحمي
    grad = np.stack(
        [np.linspace(top[i], bottom[i], H, dtype=np.float32) for i in range(3)],
        axis=-1,
    )[:, None, :]
    img = np.repeat(grad, W, axis=1)

    # سُدم نيون
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    glow = np.zeros((H, W), dtype=np.float32)
    for _ in range(3):
        cx, cy = int(rng.integers(0, W)), int(rng.integers(0, int(H * 0.7)))
        r = int(rng.integers(W // 4, W // 2))
        d2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (r ** 2)
        glow += np.exp(-d2) * float(rng.uniform(0.3, 0.7))
    glow = np.clip(glow, 0, 1.3)
    acc = np.array(neon2, dtype=np.float32)
    img = img + glow[:, :, None] * acc[None, None, :] * 0.30

    img = np.clip(img, 0, 255).astype(np.uint8)
    out = Image.fromarray(img, "RGB").convert("RGBA")

    draw = ImageDraw.Draw(out)

    # جزيئات نيون عائمة
    for _ in range(90):
        x, y = int(rng.integers(0, W)), int(rng.integers(0, H))
        s = int(rng.integers(1, 4))
        c = neon if rng.random() < 0.6 else neon2
        a = int(rng.integers(60, 200))
        draw.ellipse([x, y, x + s, y + s], fill=c + (a,))

    # شبكة الأرضية
    _grid(draw, neon)

    # فينييت مريح
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-W * 0.25, -H * 0.1, W * 1.25, H * 1.1], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(220))
    black = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    out = Image.composite(out, black, vig)

    out = _scanlines(out)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.convert("RGB").save(out_path, "PNG")
    return out_path


STYLE = {
    "hook":  {"font_size": 96, "y_ratio": 0.42, "max_w": 0.84},
    "outro": {"font_size": 84, "y_ratio": 0.44, "max_w": 0.82},
    "fact":  {"font_size": 72, "y_ratio": 0.46, "max_w": 0.86},
}


def _watermark(base: Image.Image, size: int = 150, alpha: int = 210) -> None:
    """لوجو XDAW NOVA شفاف فوق-يمين — قالب ثابت لكل فيديو."""
    logo_path = settings.LOGO
    if not logo_path.exists():
        return
    logo = Image.open(logo_path).convert("RGBA").resize((size, size), Image.LANCZOS)
    if alpha < 255:
        a = logo.getchannel("A").point(lambda v: int(v * alpha / 255))
        logo.putalpha(a)
    base.paste(logo, (W - size - 40, 40), logo)


def render_scene(out_path: Path, kind: str, text: str, seed: str,
                 chip: str = "") -> Path:
    """مشهد 2099: خلفية نيون + شارة + عنوان كبير بتوهج."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bg_path = render_bg(out_path.with_suffix(".bg.png"), kind, seed)
    base = Image.open(bg_path).convert("RGB")
    pal = PALETTES.get(kind, PALETTES["fact1"])
    st = STYLE.get("fact" if kind.startswith("fact") else kind, STYLE["fact"])

    def paste(layer_path: Path) -> None:
        layer = Image.open(layer_path)
        base.paste(layer, (0, 0), layer)

    if chip:
        paste(textrender.text_image(
            chip, out_path.with_suffix(".chip.png"), canvas=(W, H),
            font_size=56, fill=pal["neon"], y_ratio=st["y_ratio"] - 0.17,
            max_width_ratio=0.8, stroke_width=4,
        ))

    # العنوان الرئيسي أبيض بتوهج نيون حوالين الحروف
    paste(textrender.text_image(
        text or settings.BRAND["name"], out_path.with_suffix(".txt.png"),
        canvas=(W, H), font_size=st["font_size"], y_ratio=st["y_ratio"],
        max_width_ratio=st["max_w"], fill="#f4fffb",
        stroke=pal["neon"], stroke_width=7,
    ))

    _watermark(base)
    base.save(out_path, "PNG")
    return out_path

STYLE = {
    "hook":  "epic cinematic reveal, dramatic, mysterious",
    "fact":  "ultra-detailed sci-fi illustration, cinematic lighting",
    "outro": "glowing futuristic emblem, heroic",
}


def _ai_prompt(kind: str, subject: str) -> str:
    base_style = ("dark futuristic sci-fi scene, red and cyan neon glow, cyberpunk, "
                  "high detail, dramatic cinematic lighting, 9:16 vertical, no text, no watermark")
    flavor = STYLE.get("fact" if kind.startswith("fact") else kind, STYLE["fact"])
    return f"{subject}, {flavor}, {base_style}"


def fetch_ai_visual(prompt: str, out_path: Path, seed: int) -> bool:
    """صورة AI قوية من Pollinations (مجاني/بلا مفتاح) مقصوصة 1080×1920."""
    import urllib.parse
    import requests
    url = ("https://image.pollinations.ai/prompt/"
           + urllib.parse.quote(prompt)
           + f"?width=768&height=1344&seed={seed}&nologo=true")
    try:
        r = requests.get(url, timeout=90)
        if not r.ok or not r.content:
            return False
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(r.content)
        img = Image.open(out_path).convert("RGB")
        w, h = img.size
        img = img.crop((0, 0, w, h - max(24, h // 25)))  # قصّ علامة المصدر السفلية
        # cover-crop لـ1080×1920
        w, h = img.size
        tw, th = W, H
        scale = max(tw / w, th / h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        w, h = img.size
        left = (w - tw) // 2; top = (h - th) // 2
        img = img.crop((left, top, left + tw, top + th))
        img.save(out_path, "PNG")
        return True
    except Exception:
        return False


def load_logo(size: int, alpha: int = 255) -> Image.Image:
    """لوجو XDAW NOVA بمقاس معين والخلفية السوداء متحوّلة لشفافية."""
    logo = Image.open(settings.LOGO).convert("RGBA").resize((size, size), Image.LANCZOS)
    arr = np.array(logo)
    lum = arr[:, :, :3].max(axis=2).astype(np.float32)
    arr[:, :, 3] = np.minimum(arr[:, :, 3], np.clip(lum * 1.6, 0, 255)).astype(np.uint8)
    logo = Image.fromarray(arr, "RGBA")
    if alpha < 255:
        a = logo.getchannel("A").point(lambda v: int(v * alpha / 255))
        logo.putalpha(a)
    return logo


def _brand_layer(out_path: Path) -> Path:
    """طبقة شفافة ثابتة: لوجو XDAW NOVA فوق-يمين + تدرّج سينمائي فوق/تحت
    (يضبط قراءة الكابتشن ويخفي أي علامة مصدر صغيرة)."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    logo_path = settings.LOGO
    if logo_path.exists():
        size = 150
        lg = load_logo(size, 215)
        layer.paste(lg, (W - size - 40, 40), lg)
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(grad)
    gh = int(H * 0.18)
    for i in range(gh):  # تحت: قراءة الكابتشن + إخفاء علامة المصدر
        alpha = int(215 * (i / gh) ** 1.6)
        d.line([(0, H - gh + i), (W, H - gh + i)], fill=(6, 0, 2, alpha), width=1)
    gt = int(H * 0.10)
    for i in range(gt):  # فوق: تثبيت اللوجو والشارة
        alpha = int(120 * (1 - i / gt) ** 1.6)
        d.line([(0, i), (W, i)], fill=(6, 0, 2, alpha), width=1)
    layer = Image.alpha_composite(layer, grad)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    layer.save(out_path, "PNG")
    return out_path


def build_scene(kind: str, text: str, seed: str, workdir: Path,
                subject: str = "", chip: str = "") -> dict:
    """مشهد = قاعدة (AI أو نيون احتياطي) + طبقات نص شفافة.

    بيرجع {"base": Path, "overlays":[Path,...]} عشان الفيديو يركّبها.
    """
    workdir.mkdir(parents=True, exist_ok=True)
    rng = _seeded(seed)
    base = workdir / "base.png"
    prompt = _ai_prompt(kind, subject or text)
    if not fetch_ai_visual(prompt, base, int(rng.integers(1, 10_000_000))):
        base = render_bg(base, kind, seed)  # وقوع آمن للنيون

    pal = PALETTES.get(kind, PALETTES["fact1"])
    st = STYLE_FONT.get("fact" if kind.startswith("fact") else kind, STYLE_FONT["fact"])
    overlays = []
    if chip:
        overlays.append(textrender.text_image(
            chip, workdir / "chip.png", canvas=(W, H), font_size=56,
            fill=pal["neon"], y_ratio=st["y"] - 0.17, max_width_ratio=0.8, stroke_width=4))
    overlays.append(textrender.text_image(
        text or settings.BRAND["name"], workdir / "txt.png", canvas=(W, H),
        font_size=st["size"], y_ratio=st["y"], max_width_ratio=st["max"],
        fill="#f4fffb", stroke="#000000", stroke_width=6))
    overlays.append(_brand_layer(workdir / "brand.png"))  # لوجو + تدرّج — قالب ثابت
    return {"base": base, "overlays": overlays}


STYLE_FONT = {
    "hook":  {"size": 92, "y": 0.42, "max": 0.84},
    "outro": {"size": 82, "y": 0.44, "max": 0.82},
    "fact":  {"size": 70, "y": 0.46, "max": 0.86},
}
