"""فحص ذاتي: تنقية بنك الحديث من سلسلة الرواة (بلا أي نشر).

بيقرأ xtrendaw/din.py نفسه، بينفّذ دالة التنقية زي ما هي في الملف، وبيتحقق:
  ١) البليّة النظيفة موجودة وعددها كافي (مش أقل من ٢٠٠٠).
  ٢) مفيش عنصر بيبدأ بـ«حَدَّثَنَا / أَخْبَرَنَا» (العيب اللي كان ظاهر في العنوان).
  ٣) مفيش إحالة بلا محتوى («بهذا الإسناد مثله»).
  ٤) المتن الناتج مش أطول من الأصل، ومش فاضي.
  ٥) حافّات: النصوص القصيرة المنسّقة (زي «الدين النصيحة») بتفضل زي ما هي.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIN = ROOT / "xtrendaw" / "din.py"
BANK = ROOT / "content" / "din_stock.json"

WANT = {"_PROP_JUNK", "_MATN_KEEP", "_MATN_REFERRAL", "_MATN_ISNAD_START",
        "_MATN_KINDS", "_MATN_BLOCK", "_bare_ar", "_clean_marks", "_matn",
        "_strip_map", "_title_ar", "_clean_pool"}


def load_helpers() -> dict:
    """ينفّذ بلوك التنقية من din.py نفسه (بلا أي اعتماديات خارجية)."""
    tree = ast.parse(DIN.read_text(encoding="utf-8"))
    nodes = []
    for n in tree.body:
        if isinstance(n, ast.Import) and any(a.name in ("re", "unicodedata", "json")
                                             for a in n.names):
            nodes.append(n)
        elif isinstance(n, ast.Assign) and any(getattr(t, "id", "") in WANT
                                               for t in n.targets):
            nodes.append(n)
        elif isinstance(n, ast.FunctionDef) and n.name in WANT:
            nodes.append(n)
    ns: dict = {"__name__": "din_clean"}
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
                 "din_clean", "exec"), ns)
    missing = WANT - set(ns)
    if missing:
        raise SystemExit(f"❌ ناقص من din.py: {sorted(missing)}")
    return ns


def main() -> int:
    ns = load_helpers()
    matn, pool_fn, title = ns["_matn"], ns["_clean_pool"], ns["_title_ar"]
    bare = ns["_bare_ar"]
    data = json.loads(BANK.read_text(encoding="utf-8"))
    fails: list[str] = []

    # ٥) حافّات
    edge = [
        ("الدين النصيحة.", "الدين النصيحة"),
        ("لَا تَغْضَبْ.", "لَا تَغْضَبْ"),
        ("حَدَّثَنَا مُسَدَّدٌ، قَالَ: قَالَ رَسُولُ اللَّهِ صلى الله عليه وسلم: إنما الأعمال بالنيات",
         "إنما الأعمال بالنيات"),
    ]
    for src, must in edge:
        got = matn(src)
        if must not in got:
            fails.append(f"حافّة: «{src[:40]}» → «{got[:60]}» (المتوقع فيه «{must}»)")
    if matn("بِهَذَا الإِسْنَادِ مِثْلَهُ") != "":
        fails.append("حافّة: الإحالة «بهذا الإسناد مثله» المفروض تتشال")
    if pool_fn([{"text": "وَحَدَّثَنَاهُ أَبُو بَكْرٍ، بِهَذَا الإِسْنَادِ مِثْلَهُ"}]):
        fails.append("حافّة: عنصر بادي بسند المفروض يتشال من البليّة")
    for keep in ("لَا تَغْضَبْ.", "الدين النصيحة."):
        if pool_fn([{"text": keep}]) == []:
            fails.append(f"حافّة: «{keep}» المفروض يفضل في البليّة")

    for key in ("hadiths", "nawawi", "qudsi"):
        items = data.get(key) or []
        if not items:
            continue
        pool = pool_fn(items)
        print(f"▸ {key:<8} الأصل {len(items):>5} → النظيف {len(pool):>5}")
        if key == "hadiths" and len(pool) < 2000:
            fails.append(f"البليّة النظيفة صغيرة: {len(pool)}")
        # ١+٢+٣+٤
        for it in pool:
            t = it["_matn"]
            b = bare(t).strip()
            if not t.strip():
                fails.append("عنصر فاضي في البليّة")
            if len(t) > len(it["text"]) + 40:
                fails.append(f"المتن أطول من الأصل: {t[:50]}")
            if any(b.startswith(w) for w in ns["_MATN_ISNAD_START"]):
                fails.append(f"بادي بسند: {t[:60]}")
            if any(b.startswith(w) for w in ns["_MATN_REFERRAL"]):
                fails.append(f"إحالة تسرّبت: {t[:60]}")
            if any(w in b for w in ns["_MATN_BLOCK"]):
                fails.append(f"محتوى مستبعد تسرّب: {t[:60]}")
            title(t if len(t) < 40 else t[:40], 40)   # مسار العنوان لازم ما يقعش
            if len(fails) > 12:
                break

    print("\n── نموذج عناوين زي ما بتظهر على يوتيوب ──")
    for it in (pool_fn(data["hadiths"])[:6]):
        print(f"   قال رسول الله ﷺ: {title(it['_matn'], 40)}")

    if fails:
        print("\n❌ فشل:")
        for f in fails[:14]:
            print("   ·", f)
        return 1
    print("\n🎉 الفحص نجح — بنك الحديث نضيف بالكامل")
    return 0


if __name__ == "__main__":
    sys.exit(main())
