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
    "quiet": {"bg": ("#030304", "#0b0b0e"), "neon": "#8a8f98", "neon2": "#5a5f6a"},
    # أغلفة الأنواع — لكل نوع لونه الخاص في شبكة القناة
    "quran_c":  {"bg": ("#020614", "#0a1a3a"), "neon": "#7fb4ff", "neon2": "#3a6ad8"},
    "tafsir_c": {"bg": ("#140a02", "#2a1608"), "neon": "#ffb37a", "neon2": "#d87a3a"},
    "dua_c":    {"bg": ("#021210", "#0a2a26"), "neon": "#8fd8c8", "neon2": "#3ad8b0"},
    "adhkar_c": {"bg": ("#060618", "#141438"), "neon": "#9aa7ff", "neon2": "#5a67d8"},
    "hadith_c": {"bg": ("#140e02", "#2a1e08"), "neon": "#ffd166", "neon2": "#ff9a3a"},
    "info_c":   {"bg": ("#041204", "#0a2a0e"), "neon": "#9fd88a", "neon2": "#4ad860"},
    "qissa_c":  {"bg": ("#120c06", "#2a2014"), "neon": "#e8c39a", "neon2": "#c89a5a"},
}

# خلفيات بلا شبكة أرضية — السكون للهوادئ
_NO_GRID = {"quiet", "quran_c", "tafsir_c", "dua_c", "adhkar_c"}


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

    # شبكة الأرضية — الخاتمة الهادئة بلا شبكة (نهاية سوداء ساكنة كالمرجع)
    if kind not in _NO_GRID:
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


def fetch_real_visual(query: str, out_path: Path) -> bool:
    """مشهد حقيقي من Wikimedia Commons (ناس/أماكن/أحداث حقيقية، بلا مفتاح).

    بيختار صورة فوتوغرافية كافية الدقة ويقصّها cover لـ1080×1920.
    """
    import requests

    if not query or not query.strip():
        return False
    # ويكيميديا بترفض الـUA الافتراضي لمكتبة requests — توقيع واضح ومحترم
    ua = {"User-Agent": "XDAW-NOVA-factory/1.0 (free knowledge shorts; "
                        "dawshaxlol@gmail.com) requests"}
    try:
        r = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={"action": "query", "generator": "search",
                    "gsrsearch": query, "gsrnamespace": 6, "gsrlimit": 8,
                    "prop": "imageinfo", "iiprop": "url|size|mime",
                    "iiurlwidth": 1080, "format": "json"},
            headers=ua, timeout=20,
        )
        if not r.ok:
            return False
        import re as _re
        _junk = _re.compile(r"collage|mosaic|composite|montage|\bmap\b|"
                            r"diagram|chart|logo|poster|coat of arms", _re.I)
        pages = (r.json().get("query") or {}).get("pages") or {}
        cands = []
        for p in pages.values():
            if _junk.search(p.get("title", "")):
                continue  # ملفات الكولاج/الخرائط مش مشهد حقيقي
            ii = (p.get("imageinfo") or [{}])[0]
            if ii.get("mime") == "image/jpeg" and ii.get("width", 0) >= 900:
                cands.append(ii)
        if not cands:
            return False
        from . import library as _lib
        used = _lib._used(query)
        # ترتيب صلة البحث (مش الأكبر حجماً) — الكولاجات العملاقة كانت بتتصدر
        pick = None
        for c in cands:
            u = c.get("thumburl") or c.get("url")
            if u and u not in used:
                pick = u
                break
        if not pick and cands:
            pick = cands[0].get("thumburl") or cands[0].get("url")
        if not pick:
            return False
        _lib._mark_used(query, pick)
        url = pick
        img_r = requests.get(url, headers=ua, timeout=60)
        if not img_r.ok or not img_r.content:
            return False
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(img_r.content)
        img = Image.open(out_path).convert("RGB")
        # حارس البياض: خلفيات بيضاء/مخططات مش مشهد سينمائي
        _tiny = img.convert("L").resize((8, 8))
        if sum(1 for v in _tiny.getdata() if v > 235) > 40:
            out_path.unlink(missing_ok=True)
            return False
        w, h = img.size
        img = img.crop((0, 0, w, h - max(0, h // 30)))
        w, h = img.size
        scale = max(W / w, H / h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        w, h = img.size
        left, top = (w - W) // 2, (h - H) // 2
        img = img.crop((left, top, left + W, top + H))
        img.save(out_path, "PNG")
        return True
    except Exception:
        return False


def fetch_library_visual(query: str, out_path: Path) -> bool:
    """بديل احتياطي من مكتبة الوسائط الموحدة (أرشيف/NASA/Pixabay).

    تُستدعى فقط لو ويكيميديا ما رجعتش نتيجة — إضافة بلا أي تغيير سابق.
    """
    from . import library

    url = library.find_image(query)
    if not url:
        return False
    tmp = out_path.with_suffix(".dl.jpg")
    if not library.download(url, tmp):
        return False
    try:
        img = Image.open(tmp).convert("RGB")
        w, h = img.size
        if w < 700 or h < 700:
            tmp.unlink(missing_ok=True)
            return False
        scale = max(W / w, H / h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        w, h = img.size
        left, top = (w - W) // 2, (h - H) // 2
        img = img.crop((left, top, left + W, top + H))
        img.save(out_path, "PNG")
        return True
    except Exception:
        return False
    finally:
        tmp.unlink(missing_ok=True)


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


def frame_overlay(out_path: Path) -> Path:
    """إطار ذهبي هندسي هادي: خطّان + نجمة ثمانية في الزوايا (روح إسلامية)."""
    cache = settings.ASSETS / "ornaments" / "frame.png"
    if not cache.exists():
        import math

        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        gold = (216, 180, 110, 150)
        gold2 = (216, 180, 110, 80)
        m = 46
        d.rectangle([m, m, W - m, H - m], outline=gold, width=3)
        d.rectangle([m + 14, m + 14, W - m - 14, H - m - 14],
                    outline=gold2, width=1)

        def star(cx: float, cy: float, r: float) -> None:
            p1 = [(cx + r * math.cos(i * math.pi / 2),
                   cy + r * math.sin(i * math.pi / 2)) for i in range(4)]
            p2 = [(cx + r * math.cos(math.pi / 4 + i * math.pi / 2),
                   cy + r * math.sin(math.pi / 4 + i * math.pi / 2))
                  for i in range(4)]
            d.polygon(p1, outline=gold)
            d.polygon(p2, outline=gold)

        for cx, cy in [(m, m), (W - m, m), (m, H - m), (W - m, H - m)]:
            star(cx, cy, 40)
        cache.parent.mkdir(parents=True, exist_ok=True)
        layer.save(cache, "PNG")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(cache.read_bytes())
    return out_path


def intro_base(out_path: Path, title: str = "") -> Path:
    """افتتاحية البراند: سديم كوني + نجوم + توهّج أحمر + اللوجو + عنوان الحلقة.

    الإطار الأول غلاف جذّاب يوصف الحلقة (تيك توك/إنستجرام/يوتيوب)."""
    import random as _rnd
    out_path.parent.mkdir(parents=True, exist_ok=True)
    layer = Image.new("RGB", (W, H), (9, 12, 30))
    d = ImageDraw.Draw(layer, "RGBA")
    # سديم ملوّن ناعم (أزرق/بنفسجي/تركواز)
    for (bx, by, br, col) in [(W * 0.25, H * 0.28, 560, (28, 62, 145, 30)),
                              (W * 0.80, H * 0.52, 640, (96, 32, 118, 26)),
                              (W * 0.50, H * 0.80, 720, (18, 96, 128, 24))]:
        for r in range(int(br), 60, -50):
            d.ellipse([bx - r, by - r, bx + r, by + r], fill=col)
    # نجوم متناثرة
    _rng = _rnd.Random(7)
    for _ in range(460):
        x, y = _rng.randint(0, W - 1), _rng.randint(0, H - 1)
        sz = _rng.choice([1, 1, 1, 2, 2, 3])
        d.ellipse([x, y, x + sz, y + sz],
                  fill=(235, 240, 255, _rng.randint(130, 255)))
    # توهّج البراند الأحمر + اللوجو في القلب
    cx, cy = W // 2, H // 2 - 60
    for r, a in [(680, 14), (520, 20), (380, 30), (250, 46), (150, 66)]:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 42, 42, a))
    if settings.LOGO.exists():
        lg = load_logo(460, 250)
        layer.paste(lg, (cx - 230, cy - 230), lg)
    # عنوان الحلقة — الغلاف الجذّاب اللي بيوصف المحتوى
    if title:
        import re as _re
        # الخط بيرسم الأرقام LTR وbidi بيقلبها — بنعكس النطاق يدويًا
        # عشان القارئ يشوفه صح: 45–48
        def _flip(m):
            a, sep, b = m.group(1), m.group(2), m.group(3)
            return f"{b}{sep}{a}"
        title = _re.sub(r"(\d+)(\s*[–-]\s*)(\d+)", _flip, title)
        from . import textrender as _tr
        f = _tr._font(88, bold=True)
        lines = _tr.wrap_ar(title, f, W - 200)[:3]
        y = cy + 330
        for ln in lines:
            d2 = ImageDraw.Draw(layer, "RGBA")
            w = d2.textlength(_tr._display(ln), font=f)
            x = (W - w) / 2
            for ox, oy, al in [(-3, 3, 190), (3, 3, 190), (-3, -2, 150), (3, -2, 150)]:
                d2.text((x + ox, y + oy), _tr._display(ln), font=f,
                        fill=(20, 6, 4, al))
            d2.text((x, y), _tr._display(ln), font=f, fill=(255, 214, 120, 255))
            y += 118
    layer.save(out_path, "PNG")
    return out_path


def render_glint(out_path: Path) -> Path:
    """لمعة ضوء مائلة خفيفة تتحرك عبر المشهد — جاذبية سينمائية."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        return out_path
    band = Image.new("RGBA", (520, H + 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(band)
    for x in range(520):
        t = x / 519.0
        a = int(46 * (1 - abs(2 * t - 1)) ** 1.6)   # ذروة ناعمة في المنتصف
        d.line([(x, 0), (x, H + 400)], fill=(255, 244, 224, a))
    band = band.rotate(18, expand=True, resample=Image.BICUBIC)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bw, bh = band.size
    layer.paste(band, ((W - bw) // 2, (H - bh) // 2), band)
    layer.save(out_path, "PNG")
    return out_path


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
                subject: str = "", chip: str = "", real_query: str = "") -> dict:
    """مشهد = قاعدة (حقيقي ← AI ← نيون احتياطي) + طبقات نص شفافة.

    بيرجع {"base": Path, "overlays":[Path,...]} عشان الفيديو يركّبها.
    """
    workdir.mkdir(parents=True, exist_ok=True)
    rng = _seeded(seed)
    base = workdir / "base.png"
    ok = (fetch_real_visual(real_query, base)
          or fetch_library_visual(real_query, base)) if real_query else False
    if not ok:
        prompt = _ai_prompt(kind, subject or text)
        ok = fetch_ai_visual(prompt, base, int(rng.integers(1, 10_000_000)))
    if not ok:
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
