"""اختبار إنتاج حلقة كاملة — بينتج MP4 حقيقي ويفحصه بمواصفات المنصات.

ده مش syntax check: بيولّد صوت فعلي، يرسم مشاهد فعلية، يجمّع فيديو فعلي،
ويقرا الأبعاد/المدة/الترميز من الملف الناتج نفسه.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xtrendaw import content, produce, settings  # noqa: E402

WORK = settings.WORK / "_test_ep1"


def test_full_episode_produces_valid_video() -> None:
    topic = content.SEED_TOPICS[0]
    r = produce.produce_episode(topic, WORK)

    out = r["video"]
    assert out.exists() and out.stat().st_size > 50_000, "الفيديو فاضي أو مش موجود"

    info = r["report"]["info"]
    checks = r["report"]["checks"]

    print(f"الملف: {out}")
    print(f"  الأبعاد: {info['width']}×{info['height']} · المدة: {info['duration']:.2f}s")
    print(f"  الترميز: {info['vcodec']} / {info['acodec']} · الحجم: {info['bytes'] // 1024} KB")
    print(f"  المشاهد: {len(r['scenes'])} · الكابتشنز: {len(r['captions'])}")
    for name, ok in checks.items():
        print(f"  [{'✓' if ok else '✗'}] {name}")

    assert info["width"] == 1080 and info["height"] == 1920, "الأبعاد غلط"
    assert info["vcodec"] == "h264", f"الترميز {info['vcodec']} مش H.264"
    assert info["acodec"] == "aac", f"الصوت {info['acodec']} مش AAC"
    assert 0 < info["duration"] <= 90, f"المدة {info['duration']} خارج الحد"
    assert info["bytes"] <= settings.VIDEO["max_bytes"], "الحجم أكبر من الحد"
    assert r["report"]["ok"], "فيه بند فشل في فحص المواصفات"

    # الكابتشن ثنائي اللغة: عربي كينيتيك + سطر إنجليزي للقراءة
    ass_text = Path(r["ass"]).read_text(encoding="utf-8")
    assert "Style: CapEN" in ass_text, "ستايل الإنجليزي ناقص من الـASS"
    assert "Every carbon atom" in ass_text, "سطر الإنجليزي مش موجود في الـASS"
    print("  [✓] كابتشن ثنائي اللغة (عربي كينيتيك + إنجليزي للقراءة)")

    # الكابتشنز لازم تغطي معظم مدة الحلقة (مش شريحة واحدة ميتة)
    covered = sum(o["end"] - o["start"] for o in r["captions"])
    ratio = covered / info["duration"]
    assert ratio > 0.7, f"تغطية الكابتشنز ضعيفة: {ratio:.0%}"
    print(f"  تغطية الكابتشنز: {ratio:.0%} من مدة الحلقة")


if __name__ == "__main__":
    test_full_episode_produces_valid_video()
    print("\nالحلقة اتنتجت والمواصفات سليمة.")
