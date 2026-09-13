"""إنتاج حلقة كاملة: موضوع → سيناريو → صوت → مشاهد → كابتشنز → MP4.

دي الوحدة اللي بتتكرر كل دورة. النشر والحالة layers منفصلة فوقها.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from . import captions, content, scenes, settings, tts, video

CHIPS_AR = ["الحقيقة الأولى", "الحقيقة الثانية", "والحقيقة الثالثة"]


def produce_episode(topic: dict, workdir: Path) -> dict:
    """ينتج MP4 واحد ويعيد {video, plan, ass, captions, report}."""
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    # 1) السيناريو (عربي للصوت + إنجليزي للقراءة/الـAI)
    segs = content.compose_script(topic, "ar")
    en_lines = content.english_lines(topic)

    # 2) الصوت + التوقيتات
    plan = tts.synthesize_segments(segs, "ar", workdir / "tts")
    total = plan["total_duration"]
    if total <= 0:
        raise RuntimeError("مدة الصوت صفر")

    # 3) المشاهد — قاعدة AI قوية (Pollinations) أو نيون احتياطي + طبقات نص
    from . import music as _music
    scene_list: list[dict] = []
    for i, item in enumerate(plan["items"]):
        kind = item["seg"] if item["seg"] in ("hook", "outro") else f"fact{(i % 3) + 1}"
        text = item["text"]
        if ":" in text:
            text = text.split(":", 1)[1].strip()
        chip = CHIPS_AR[i - 1] if kind.startswith("fact") and 1 <= i <= 3 else ""
        subject = ""
        if i < len(en_lines):
            subject = en_lines[i]
            if ":" in subject:
                subject = subject.split(":", 1)[1].strip()
        sc = scenes.build_scene(kind, text, seed=f"{topic['id']}:{i}",
                                workdir=workdir / f"sc{i:02d}", subject=subject, chip=chip)
        sc["start"] = item["start"]
        sc["end"] = item["end"]
        scene_list.append(sc)

    # 3.5) موسيقى خلفية مولّدة (بلا حقوق)
    music_path = _music.make_music(plan["total_duration"], workdir / "music.wav")

    # 4) الكابتشنز المتزامنة (ASS — libass بيتكفل بالتشكيل العربي)
    #    + سطر إنجليزي موازٍ لكل مقطع عشان القراءة العالمية
    en_lines = content.english_lines(topic)
    ass_path, chunks = captions.build_ass(plan, workdir / "caps.ass", en_lines=en_lines)

    # 5) التجميع
    out = settings.OUT / f"{topic['id']}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    video.assemble(plan, scene_list, ass_path, out, workdir / "build", music=music_path)

    # 5.5) الغلاف — نفس هوية المشاهد
    from . import brand
    cover = settings.OUT / f"{topic['id']}-cover.png"
    brand.compose_cover(topic, cover)

    # 6) التحقق من المواصفات
    report = video.validate(out)

    (workdir / "report.json").write_text(
        json.dumps(
            {
                "episode": topic["id"],
                "title": topic["title_ar"],
                "total_duration": round(total, 3),
                "scenes": len(scene_list),
                "captions": len(chunks),
                "cover": str(cover),
                "validate": {
                    "info": report["info"],
                    "checks": report["checks"],
                    "ok": report["ok"],
                },
            },
            ensure_ascii=False, indent=1,
        ),
        encoding="utf-8",
    )

    return {
        "video": out,
        "cover": cover,
        "plan": plan,
        "ass": ass_path,
        "captions": chunks,
        "scenes": scene_list,
        "report": report,
    }
