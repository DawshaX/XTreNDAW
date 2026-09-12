"""رسم النصوص العربية — بورتابل بين بيئة فيها libraqm وبيئة من غيره.

الدرس المقيس (work/_check/raqm_test.png):
- لو PIL عنده raqm (زي هنا): ممنوع نمرّر نص مُشكَّل مسبقًا — raqm هيشتغل عليه
  تاني ويتكسر (حروف منفصلة + ترتيب معكوس). بنمرّر النص الأصلي مع direction=rtl.
- لو مفيش raqm: بنشكّل يدويًا (reshape + bidi) ونرسم LTR.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, features

from . import settings

FONT_BOLD = settings.FONTS / "Tajawal-Bold.ttf"
FONT_REG = settings.FONTS / "Tajawal-Regular.ttf"
HAS_RAQM = bool(features.check("raqm"))

# ثوابت راqm عشان الاتجاه واللغة
_RTL = {"direction": "rtl", "language": "ar"} if HAS_RAQM else {}


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REG
    if not path.exists():
        raise FileNotFoundError(f"الخط مش موجود: {path}")
    return ImageFont.truetype(str(path), size)


def shape_ar(text: str) -> str:
    """تشكيل يدوي (يُستخدم فقط لو مفيش raqm)."""
    import arabic_reshaper
    from bidi.algorithm import get_display

    return get_display(arabic_reshaper.reshape(text))


def _display(text: str) -> str:
    return text if HAS_RAQM else shape_ar(text)


def _width(font: ImageFont.FreeTypeFont, text: str) -> float:
    if HAS_RAQM:
        return font.getlength(text, direction="rtl", language="ar")
    return font.getbbox(shape_ar(text))[2]


def wrap_ar(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        cur: list[str] = []
        for w in words:
            trial = " ".join(cur + [w])
            if _width(font, trial) <= max_width or not cur:
                cur.append(w)
            else:
                lines.append(" ".join(cur))
                cur = [w]
        if cur:
            lines.append(" ".join(cur))
    return lines


def _draw_centered(draw: ImageDraw.ImageDraw, line: str, W: int, y: int,
                   font: ImageFont.FreeTypeFont, fill: str,
                   stroke_width: int, stroke: str) -> None:
    disp = _display(line)
    w = _width(font, line)
    x = (W - w) / 2
    draw.text(
        (x, y), disp, font=font, fill=fill,
        stroke_width=stroke_width, stroke_fill=stroke,
        anchor="la", **_RTL,
    )


def text_image(text: str, out_path: Path, canvas=(1080, 1920), font_size=76,
               fill="#FFFFFF", stroke="#000000", stroke_width=6,
               y_ratio=0.62, max_width_ratio=0.86, bold=True) -> Path:
    W, H = canvas
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _font(font_size, bold)
    lines = [l for l in wrap_ar(text, font, int(W * max_width_ratio))]
    shaped_lines = [l for l in lines if l.strip()]
    if not shaped_lines:
        shaped_lines = [" "]

    line_h = int(font_size * 1.45)
    y = int(H * y_ratio) - (line_h * len(shaped_lines)) // 2
    for line in shaped_lines:
        _draw_centered(draw, line, W, y, font, fill, stroke_width, stroke)
        y += line_h

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path
