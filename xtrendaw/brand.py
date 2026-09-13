"""غلاف الحلقة — صورة 1080×1920 بنفس هوية المشاهد.

المنصات (Shorts/Reels) بتاخد غلاف رأسي. بنطلعه من نفس الخلفية المولّدة
عشان الهوية تفضل ثابتة، وبنضيف العنوان واسم المشروع.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from . import settings, textrender

W, H = settings.VIDEO["width"], settings.VIDEO["height"]


def compose_cover(topic: dict, out_path: Path, seed: str = "") -> Path:
    """غلاف رأسي: خلفية hook + العنوان في النص + اسم المشروع تحت."""
    from . import scenes

    out_path.parent.mkdir(parents=True, exist_ok=True)
    bg_path = scenes.render_bg(
        out_path.with_suffix(".bg.png"), "hook", seed or topic["id"]
    )
    base = Image.open(bg_path).convert("RGB")

    # العنوان في منتصف الصورة
    title_layer = textrender.text_image(
        topic["title_ar"], out_path.with_suffix(".t.png"),
        canvas=(W, H), font_size=92, y_ratio=0.44, max_width_ratio=0.84,
    )
    base.paste(Image.open(title_layer), (0, 0), Image.open(title_layer))

    # اسم المشروع تحت
    brand_layer = textrender.text_image(
        settings.BRAND["name"], out_path.with_suffix(".b.png"),
        canvas=(W, H), font_size=52, fill="#ffd166", y_ratio=0.90,
        max_width_ratio=0.6, stroke_width=4,
    )
    base.paste(Image.open(brand_layer), (0, 0), Image.open(brand_layer))

    base.save(out_path, "PNG")
    return out_path
