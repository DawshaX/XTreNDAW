"""غلاف الحلقة — صورة 1080×1920 بنفس هوية المشاهد.

المنصات (Shorts/Reels) بتاخد غلاف رأسي. بنطلعه من نفس الخلفية المولّدة
عشان الهوية تفضل ثابتة، وبنضيف العنوان واسم المشروع.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from . import settings, textrender

W, H = settings.VIDEO["width"], settings.VIDEO["height"]


# لكل نوع غلاف بلونه وشارته — شبكة القناة متنوّعة مش نسخة واحدة
KIND_COVER = {
    "quran": ("quran_c", "#7fb4ff", "قرآن كريم"),
    "tafsir": ("tafsir_c", "#ffb37a", "تفسير وتدبُّر"),
    "dua": ("dua_c", "#8fd8c8", "دعاء"),
    "adhkar": ("adhkar_c", "#9aa7ff", "أذكار"),
    "hadith": ("hadith_c", "#ffd166", "حديث نبوي"),
    "info": ("info_c", "#9fd88a", "معلومة تُضيء"),
    "qissa": ("qissa_c", "#e8c39a", "قصة من القصص"),
    "seerah": ("seerah_c", "#d8b08a", "مِن السيرة النبوية"),
    "asma": ("asma_c", "#ffe9b0", "مِن الأسماء الحسنى"),
    "kawn": ("kawn_c", "#b09aff", "آية في الكون"),
    "akhira": ("akhira_c", "#a8c8d8", "استعد للقاء"),
    "akhlaq": ("akhlaq_c", "#e8a8a0", "خُلق حسن"),
    "juz": ("quran_c", "#7fb4ff", "سلسلة جزء عمّ"),
    "nawawi": ("nawawi_c", "#d8c8a0", "الأربعون النووية"),
    "ruqyah": ("ruqyah_c", "#7fe0b0", "الرقية الشرعية"),
    "hisn": ("hisn_c", "#8fd0d8", "حصن المسلم"),
    "tahseen": ("tahseen_c", "#e0c87f", "التحصين"),
    "qudsi": ("qudsi_c", "#c0a0e0", "حديث قدسي"),
}


def compose_cover(topic: dict, out_path: Path, seed: str = "") -> Path:
    """غلاف رأسي بهوية النوع: لونه + شارته + العنوان + البراند."""
    from . import scenes

    out_path.parent.mkdir(parents=True, exist_ok=True)
    kind = topic.get("_kind", "info")
    pal, accent, chip = KIND_COVER.get(kind, ("hook", "#ff7a1a", "نُور"))
    bg_path = scenes.render_bg(
        out_path.with_suffix(".bg.png"), pal, seed or topic["id"]
    )
    base = Image.open(bg_path).convert("RGB")

    # شارة النوع فوق — لون وشكل مختلف لكل تصنيف
    chip_layer = textrender.text_image(
        f"﴿ {chip} ﴾", out_path.with_suffix(".c.png"),
        canvas=(W, H), font_size=52, y_ratio=0.30, fill=accent,
        stroke_width=3, font_path=settings.FONTS / "AmiriQuran-Regular.ttf",
    )
    base.paste(Image.open(chip_layer), (0, 0), Image.open(chip_layer))

    # العنوان في منتصف الصورة
    title_layer = textrender.text_image(
        topic["title_ar"], out_path.with_suffix(".t.png"),
        canvas=(W, H), font_size=92, y_ratio=0.46, max_width_ratio=0.84,
    )
    base.paste(Image.open(title_layer), (0, 0), Image.open(title_layer))

    # اللوجو فوق العنوان — قالب ثابت
    if settings.LOGO.exists():
        logo = scenes.load_logo(260)
        base.paste(logo, ((W - 260) // 2, int(H * 0.10)), logo)

    # اسم البراند + التاجلاين تحت بلون النوع
    for txt, yr, fs, fill in [
        (settings.BRAND["name"], 0.86, 60, accent),
        (settings.BRAND["tagline_ar"], 0.925, 40, "#c9b8a8"),
    ]:
        layer = textrender.text_image(
            txt, out_path.with_suffix(".b.png"), canvas=(W, H),
            font_size=fs, fill=fill, y_ratio=yr, max_width_ratio=0.8, stroke_width=4,
        )
        base.paste(Image.open(layer), (0, 0), Image.open(layer))

    base.save(out_path, "PNG")
    # Workspace lightweight: delete intermediate cover layers
    for tmp in (".bg.png", ".t.png", ".b.png"):
        out_path.with_suffix(tmp).unlink(missing_ok=True)
    return out_path
