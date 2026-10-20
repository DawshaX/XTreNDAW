"""⭐ غرسة «سلسلة التدبُّر (1/42)» مايرجعش تاني — نوافذ المخطط لها رقم حقيقي."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xtrendaw import din  # noqa: E402


def _specs():
    wins = [{"surah": 3, "frm": f, "to": min(f + 3, 200)}
            for f in range(1, 198, 4)]
    return wins


def test_window_title_has_true_index_and_hook():
    spec = {"id": "ts003-145", "surah": 3, "frm": 145, "to": 148}
    t = din._tafsir_window_title(
        spec, "سُورَةُ آلِ عِمۡرَانَ", "أيمن سويد",
        "وَإِنْ يَمْسَسْكَ اللَّهُ بِضُرٍّ فَلَا كَاشِفَ لَهُ إِلَّا هُوَ",
        _specs())
    assert "(1/42)" not in t, "الرقم المعدوم رجع تاني!"
    assert "(37/50)" in t, f"الرقم الحقيقي مش موجود: {t}"
    assert "تفسير ميسّر" in t and "تدبّر" in t
    # اسم نظيف للبحث — «آل عمران» مش «ال عمران»
    assert "آل عمران" in t


def test_window_title_differs_per_window():
    wins = _specs()
    a = din._tafsir_window_title({"id": "x", "surah": 3, "frm": 1, "to": 4},
                                 "سورة آل عمران", "قارئ", "نص أول", wins)
    b = din._tafsir_window_title({"id": "y", "surah": 3, "frm": 5, "to": 8},
                                 "سورة آل عمران", "قارئ", "نص تاني", wins)
    assert a != b and "(1/50)" in a and "(2/50)" in b


def test_bank_row_keeps_legacy_number():
    """صفوف البنك الثابتة تحتفظ بترقيمها الأصلي — مافيش كسر للقديم."""
    ids = [w["id"] for w in din.TAFASEER]
    assert "t-asr" in ids
    # النوافذ مش موجودة في البنك ⇒ ترقيمها الحقيقي من quran_windows
    assert "ts003-145" not in ids


if __name__ == "__main__":
    test_window_title_has_true_index_and_hook()
    test_window_title_differs_per_window()
    test_bank_row_keeps_legacy_number()
    print("✓ كل اختبارات عناوين التفسير نجحت")
