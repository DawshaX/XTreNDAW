"""اختبار رسم العربي — بيقفل درس libraqm المقيس.

الدرس: لما PIL عنده raqm، تمرير نص مُشكَّل مسبقًا بيكسره (حروف منفصلة
وترتيب معكوس). الحل: نمرّر النص الأصلي مع direction=rtl. الاختبار ده بيتأكد
إن المسار ده شغال وإن الناتج فيه حبر فعلي (مش صورة فاضية).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

from xtrendaw import textrender  # noqa: E402

TMP = Path(__file__).resolve().parent.parent / "work" / "_test_textrender"


def _ink(img: Image.Image) -> int:
    """عدد البكسلات غير الشفافة — دليل إن النص اترسم فعلًا."""
    hist = img.convert("RGBA").getchannel("A").histogram()
    return sum(c for v, c in enumerate(hist) if v > 20)


def test_renders_arabic_with_ink() -> None:
    TMP.mkdir(parents=True, exist_ok=True)
    out = textrender.text_image(
        "هل تعرف إن كل ذرة في جسمك كانت جوه نجم انفجر؟",
        TMP / "line.png", font_size=80,
    )
    img = Image.open(out)
    ink = _ink(img)
    assert ink > 5000, f"النص ما اترسمش تقريبًا — حبر {ink} بكسل بس"
    print(f"✓ رسم عربي: {ink} بكسل حبر · raqm={textrender.HAS_RAQM}")


def test_width_measurement_respects_shaping() -> None:
    """القياس لازم يعكس التشكيل الفعلي — أساس الـwrap الصحيح."""
    font = textrender._font(80)
    short = textrender._width(font, "كلمة")
    long = textrender._width(font, "كلمة طويلة جدًا فيها حروف متصلة كتير")
    assert long > short, "القياس مش بيفرق بين نص قصير وطويل"
    print(f"✓ قياس العرض: قصير={short:.0f}px طويل={long:.0f}px")


if __name__ == "__main__":
    test_renders_arabic_with_ink()
    test_width_measurement_respects_shaping()
    print("\nاختبارات الرسم نجحت.")
