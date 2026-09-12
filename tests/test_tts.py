"""اختبار حقيقي لمحرك الصوت — بينفّذ الكود الفعلي مش بيقلده.

بيعمل: توليد صوت عربي فعلي من edge-tts → يفحص إن الملف موجود،
والمدة منطقية، وتوقيتات الكلمات متزايدة ومتزامنة مع مدة الملف.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xtrendaw import tts  # noqa: E402

TMP = Path(__file__).resolve().parent.parent / "work" / "_test_tts"

AR_LINE = "ثلاث حقائق صادمة عن الكون. الحقيقة الأولى: الكون يتمدد بسرعة متزايدة."


def test_ffmpeg_available() -> None:
    exe = tts.ffmpeg()
    assert Path(exe).exists(), f"ffmpeg مش موجود: {exe}"
    out = subprocess.run([exe, "-version"], capture_output=True, text=True)
    assert out.returncode == 0 and "ffmpeg version" in out.stdout


def test_synthesize_line_produces_audio_and_timings() -> None:
    if TMP.exists():
        shutil.rmtree(TMP)
    r = tts.synthesize_line(AR_LINE, "ar", TMP, name="t1")

    assert r["mp3"].exists() and r["mp3"].stat().st_size > 1000, "mp3 فاضي"
    assert r["wav"].exists(), "wav ما اتعملش"
    assert r["duration"] > 2.0, f"المدة قصيرة بشكل مريب: {r['duration']}"
    assert r["words"], "مفيش توقيتات كلمات رجعت"

    # التوقيتات لازم تكون متزايدة وداخل مدة الملف
    starts = [w["start"] for w in r["words"]]
    assert starts == sorted(starts), "توقيتات الكلمات مش متزايدة"
    assert r["words"][-1]["end"] <= r["duration"] + 0.5, "آخر كلمة بتعدّي مدة الملف"
    # التغطية: آخر كلمة لازم تقرب من نهاية الملف (مش توقيتات فاضية)
    assert r["words"][-1]["end"] > r["duration"] * 0.5, (
        f"توقيتات مش متزامنة: آخر كلمة {r['words'][-1]['end']}s من {r['duration']}s"
    )
    print(f"✓ سطر عربي: {r['duration']:.2f}s · {len(r['words'])} كلمة · "
          f"آخر كلمة بتنتهي عند {r['words'][-1]['end']:.2f}s")


def test_synthesize_segments_merges_and_offsets() -> None:
    if TMP.exists():
        shutil.rmtree(TMP)
    segs = [
        {"seg": "hook", "text": "هل تعرف أن جسمك فيه نجوم؟"},
        {"seg": "fact1", "text": "الحقيقة الأولى: كل ذرة كربون في جسمك اتصنعت جوه نجم."},
        {"seg": "outro", "text": "تابع XTreNDAW."},
    ]
    plan = tts.synthesize_segments(segs, "ar", TMP)

    assert plan["wav"].exists(), "ملف الدمج ما اتعملش"
    assert len(plan["items"]) == 3, f"متوقع 3 مقاطع، وصل {len(plan['items'])}"

    # المقاطع لازم تكون متتالية من غير تداخل
    for a, b in zip(plan["items"], plan["items"][1:]):
        assert a["end"] <= b["start"] + 0.01, f"تداخل بين {a['seg']} و{b['seg']}"

    merged = tts.probe_duration(plan["wav"])
    assert merged > 0, "مدة الملف المدموج صفر"
    # الملف المدموج لازم يطابق مجموع المقاطع (تساهل نصف ثانية لترميز WAV)
    assert abs(merged - plan["total_duration"]) < 0.5, (
        f"الدمج مش مطابق: ملف {merged:.2f}s مقابل مجموع {plan['total_duration']:.2f}s"
    )

    # التوقيتات المطلقة للكلمات جوه نطاق الحلقة
    all_words = [w for it in plan["items"] for w in it["words"]]
    assert all_words, "مفيش كلمات في الخطة"
    assert all_words[-1]["end"] <= merged + 0.5, "كلمة خارج نطاق الملف المدموج"

    print(f"✓ 3 مقاطع: إجمالي {plan['total_duration']:.2f}s · ملف مدموج {merged:.2f}s · "
          f"{len(all_words)} كلمة بتوقيت مطلق")


if __name__ == "__main__":
    test_ffmpeg_available()
    print("✓ ffmpeg متاح")
    test_synthesize_line_produces_audio_and_timings()
    test_synthesize_segments_merges_and_offsets()
    print("\nكل الاختبارات نجحت.")
