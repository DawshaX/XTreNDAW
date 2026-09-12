"""التجميع النهائي — ffmpeg: Ken Burns + دمج + كابتشنز + ترميز بمواصفات المنصات.

المواصفات مفروضة من إنستجرام/يوتيوب (شوف README):
1080×1920 · 30fps · H.264 + AAC · faststart · ≤90 ثانية · ≤40MB
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from . import settings
from .tts import ffmpeg

V = settings.VIDEO


def _run(cmd: list[str], what: str) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        tail = (r.stderr or "")[-900:]
        raise RuntimeError(f"{what} فشل (exit {r.returncode}):\n{tail}")


def probe(path: Path) -> dict:
    """قراءة أبعاد/مدة/حجم الملف الناتج — للتحقق مش للتخمين."""
    r = subprocess.run(
        [ffmpeg(), "-i", str(path)], capture_output=True, text=True
    )
    import re

    err = r.stderr
    dur = 0.0
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", err)
    if m:
        h, mi, s = m.groups()
        dur = int(h) * 3600 + int(mi) * 60 + float(s)
    w = h_ = 0
    m2 = re.search(r"Video:.*?, (\d{2,5})x(\d{2,5})", err)
    if m2:
        w, h_ = int(m2.group(1)), int(m2.group(2))
    vcodec = ""
    m3 = re.search(r"Video: (\w+)", err)
    if m3:
        vcodec = m3.group(1)
    acodec = ""
    m4 = re.search(r"Audio: (\w+)", err)
    if m4:
        acodec = m4.group(1)
    return {"duration": dur, "width": w, "height": h_, "vcodec": vcodec,
            "acodec": acodec, "bytes": path.stat().st_size if path.exists() else 0}


def make_clip(scene_png: Path, seconds: float, out_mp4: Path) -> Path:
    """صورة واحدة → مقطع بحركة Ken Burns بطيئة."""
    frames = max(2, int(round(seconds * V["fps"])))
    zoom_total = 0.10  # 10% zoom على طول المقطع
    vf = (
        f"scale={V['width'] * 3 // 2}:{V['height'] * 3 // 2},"
        f"zoompan=z='1+{zoom_total}*on/{frames}':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={V['width']}x{V['height']}:fps={V['fps']}"
    )
    _run([
        ffmpeg(), "-y", "-i", str(scene_png),
        "-vf", vf, "-frames:v", str(frames), "-r", str(V["fps"]),
        "-c:v", V["vcodec"], "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-an", str(out_mp4),
    ], f"clip {scene_png.name}")
    return out_mp4


def assemble(plan: dict, scenes: list[dict], ass_path: Path,
             out_mp4: Path, workdir: Path) -> Path:
    """الصوت + المشاهد + كابتشنز ASS → MP4 نهائي بمواصفات المنصات.

    scenes: [{"path": Path, "start": float, "end": float}]
    """
    workdir.mkdir(parents=True, exist_ok=True)
    ff = ffmpeg()
    total = plan["total_duration"]

    # 1) مقاطع المشاهد (Ken Burns)
    clip_paths: list[Path] = []
    for i, sc in enumerate(scenes):
        dur = max(0.4, sc["end"] - sc["start"])
        cp = workdir / f"clip{i:02d}.mp4"
        make_clip(Path(sc["path"]), dur, cp)
        clip_paths.append(cp)

    # 2) دمج المقاطع
    concat_list = workdir / "clips.txt"
    concat_list.write_text(
        "".join(f"file \'{p.name}\'\n" for p in clip_paths), encoding="utf-8"
    )
    base_video = workdir / "base.mp4"
    _run([
        ff, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c:v", V["vcodec"], "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", str(V["fps"]), "-an", str(base_video),
    ], "دمج المقاطع")

    # 3) حرق الكابتشنز (libass) + الصوت — فلتر واحد، ذاكرة منخفضة
    fontsdir = str(settings.FONTS)
    vf = f"ass={ass_path.as_posix()}:fontsdir={fontsdir}"
    _run([
        ff, "-y", "-i", str(base_video), "-i", str(plan["wav"]),
        "-vf", vf,
        "-c:v", V["vcodec"], "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", str(V["fps"]),
        "-c:a", V["acodec"], "-b:a", "128k", "-ar", "44100",
        "-t", f"{total:.3f}", "-shortest",
        "-movflags", "+faststart",
        str(out_mp4),
    ], "التجميع النهائي")

    if not out_mp4.exists():
        raise RuntimeError("الملف النهائي ما اتعملش")
    return out_mp4


def validate(path: Path) -> dict:
    """فحص الناتج ضد مواصفات المنصات — بيرجع تقرير فيه pass/fail لكل بند."""
    info = probe(path)
    checks = {
        "الأبعاد 1080×1920": info["width"] == V["width"] and info["height"] == V["height"],
        "الترميز H.264": info["vcodec"] == "h264",
        "الصوت AAC": info["acodec"] == "aac",
        f"المدة ≤{V['max_seconds']}s": 0 < info["duration"] <= V["max_seconds"],
        f"الحجم ≤{V['max_bytes'] // (1024 * 1024)}MB": info["bytes"] <= V["max_bytes"],
    }
    return {"info": info, "checks": checks, "ok": all(checks.values())}
