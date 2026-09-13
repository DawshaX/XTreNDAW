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

    # 1) السيناريو
    segs = content.compose_script(topic, "ar")

    # 2) الصوت + التوقيتات
    plan = tts.synthesize_segments(segs, "ar", workdir / "tts")
    total = plan["total_duration"]
    if total <= 0:
        raise RuntimeError("مدة الصوت صفر")

    # 3) المشاهد — مشهد لكل مقطع، بنفس مدته
    scene_list: list[dict] = []
    for i, item in enumerate(plan["items"]):
        kind = item["seg"] if item["seg"] in ("hook", "outro") else f"fact{(i % 3) + 1}"
        text = item["text"]
        if ":" in text:
            text = text.split(":", 1)[1].strip()
        chip = CHIPS_AR[i - 1] if kind.startswith("fact") and 1 <= i <= 3 else ""
        path = scenes.render_scene(
            workdir / f"scene_{i:02d}.png", kind, text,
            seed=f"{topic['id']}:{i}", chip=chip,
        )
        scene_list.append({"path": path, "start": item["start"], "end": item["end"]})

    # 4) الكابتشنز المتزامنة (ASS — libass بيتكفل بالتشكيل العربي)
    ass_path, chunks = captions.build_ass(plan, workdir / "caps.ass")

    # 5) التجميع
    out = settings.OUT / f"{topic['id']}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    video.assemble(plan, scene_list, ass_path, out, workdir / "build")

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
