"""التجميع النهائي — ffmpeg.

مشهد = قاعدة (AI/نيون) بحركة Ken Burns + طبقات نص شفافة.
النهائي = دمج المشاهد + كابتشن ASS (عربي كينيتيك + إنجليزي) + سرد + موسيقى.
المواصفات مفروضة من المنصات: 1080×1920 · 30fps · H.264+AAC · faststart · ≤90s · ≤40MB
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from . import settings
from .tts import ffmpeg

V = settings.VIDEO


def _run(cmd: list[str], what: str) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{what} فشل (exit {r.returncode}):\n{(r.stderr or '')[-700:]}")


def probe(path: Path) -> dict:
    r = subprocess.run([ffmpeg(), "-i", str(path)], capture_output=True, text=True)
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
    vc = re.search(r"Video: (\w+)", err)
    ac = re.search(r"Audio: (\w+)", err)
    return {"duration": dur, "width": w, "height": h_,
            "vcodec": vc.group(1) if vc else "", "acodec": ac.group(1) if ac else "",
            "bytes": path.stat().st_size if path.exists() else 0}


def _move_variant(seed_str: str) -> int:
    import hashlib

    return int(hashlib.sha256(seed_str.encode()).hexdigest()[:8], 16) % 4


def make_clip(scene: dict, seconds: float, out_mp4: Path) -> Path:
    """قاعدة (صورة) + طبقات نص → مقطع بحركة سينمائية متنوعة + انتقال ناعم."""
    frames = max(2, int(round(seconds * V["fps"])))
    base_path = scene.get("video") or scene["base"]
    inputs = ["-i", str(base_path)]
    for ov in scene.get("overlays", []):
        inputs += ["-i", str(ov)]

    dip_out = max(0.0, seconds - 0.20)
    grade_red = (f"eq=contrast=1.08:saturation=1.22:brightness=0.01,"
                 f"colorbalance=rs=0.14:rm=0.14:rh=0.08:gm=-0.05:bm=-0.14")
    grade_soft = "eq=contrast=1.05:saturation=1.08:brightness=0.01"
    grade = grade_soft if scene.get("grade") == "soft" else grade_red
    # لمسة سينمائية: فينييت + حبيبة فيلم خفيفة + وضوح
    rich = "vignette=PI/5,noise=alls=2:allf=t,unsharp=5:5:0.5"
    _fin = "" if scene.get("nofade_in") else "fade=t=in:st=0:d=0.24:"
    if scene.get("video"):
        # قاعدة فيديو حيّ متحرك — مفيش zoompan، الحركة من اللقطة نفسها
        parts = [
            f"[0:v]{grade},{rich},"
            f"{_fin}color=0x0a0603,"
            f"fade=t=out:st={dip_out:.2f}:d=0.20:color=black[base]"
        ]
    else:
        # حركة مختلفة لكل مشهد: تقريب / إبعاد / بان يمين / بان شمال
        cx = "iw/2-(iw/zoom/2)"
        cy = "ih/2-(ih/zoom/2)"
        mv = _move_variant(out_mp4.name)
        if mv == 0:
            zp = f"z='1+0.11*on/{frames}':x='{cx}':y='{cy}'"
        elif mv == 1:
            zp = f"z='1.11-0.11*on/{frames}':x='{cx}':y='{cy}'"
        elif mv == 2:
            zp = f"z='1.08':x='(iw-iw/zoom)*(0.12+0.76*on/{frames})':y='{cy}'"
        else:
            zp = f"z='1.08':x='(iw-iw/zoom)*(0.88-0.76*on/{frames})':y='{cy}'"
        parts = [
            f"[0:v]scale={V['width'] * 3 // 2}:{V['height'] * 3 // 2},"
            # دفعة هوية حمراء سينمائية موحّدة فوق أي صورة مصدر
            f"{grade},{rich},"
            f"zoompan={zp}:d={frames}:s={V['width']}x{V['height']}:fps={V['fps']},"
            # انتقال ناعم: خروج لأسود — والدخول مشرّق لأول مشهد (غلاف إنستجرام)
            f"{_fin}color=0x140404,"
            f"fade=t=out:st={dip_out:.2f}:d=0.20:color=black[base]"
        ]
    prev = "[base]"
    for i in range(1, len(inputs) // 2):
        nxt = f"[v{i}]"
        parts.append(f"{prev}[{i}:v]overlay=0:0{nxt}")
        prev = nxt

    _run([
        ffmpeg(), "-y", *inputs,
        "-filter_complex", ";".join(parts),
        "-map", prev, "-frames:v", str(frames), "-r", str(V["fps"]),
        "-c:v", V["vcodec"], "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-an", str(out_mp4),
    ], f"clip {out_mp4.name}")
    return out_mp4


def assemble(plan: dict, scenes: list[dict], ass_path: Path, out_mp4: Path,
             workdir: Path, music: Path | None = None) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    ff = ffmpeg()
    total = plan["total_duration"]

    clip_paths = []
    for i, sc in enumerate(scenes):
        cp = workdir / f"clip{i:02d}.mp4"
        make_clip(sc, max(0.4, sc["end"] - sc["start"]), cp)
        clip_paths.append(cp)

    concat_list = workdir / "clips.txt"
    concat_list.write_text("".join(f"file '{p.name}'\n" for p in clip_paths), encoding="utf-8")
    base_video = workdir / "base.mp4"
    _run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
          "-c:v", V["vcodec"], "-preset", "veryfast", "-crf", "23",
          "-pix_fmt", "yuv420p", "-r", str(V["fps"]), "-an", str(base_video)], "دمج")

    ass = f"ass={ass_path.as_posix()}:fontsdir={settings.FONTS}"
    # لمسة فيلم: حبيبات خفيفة + فينييت مريح
    grade = ",noise=alls=4:allf=t,vignette=a=0.3"
    if music and Path(music).exists():
        # الموسيقى تتنفس: دخول/خروج + خفض تلقائي تحت الصوت (sidechain)
        duck = (f"[2:a]afade=t=in:d=0.8,afade=t=out:st={max(0, total - 1.4):.2f}:d=1.4[m0];"
                f"[m0][1:a]sidechaincompress=threshold=0.08:ratio=5:attack=15:release=350[m];"
                f"[1:a][m]amix=inputs=2:duration=first:normalize=0[a]")
        fc = f"[0:v]{ass}{grade}[v];{duck}"
        audio_in = ["-i", str(plan["wav"]), "-i", str(music)]
        amap = "[a]"
    else:
        fc = f"[0:v]{ass}{grade}[v]"
        audio_in = ["-i", str(plan["wav"])]
        amap = "1:a"
    _run([ff, "-y", "-i", str(base_video), *audio_in,
          "-filter_complex", fc, "-map", "[v]", "-map", amap,
          "-c:v", V["vcodec"], "-preset", "veryfast", "-crf", "23",
          "-pix_fmt", "yuv420p", "-r", str(V["fps"]),
          "-c:a", V["acodec"], "-b:a", "160k", "-ar", "44100",
          "-t", f"{total:.3f}", "-shortest", "-movflags", "+faststart",
          str(out_mp4)], "التجميع النهائي")

    if not out_mp4.exists():
        raise RuntimeError("الملف النهائي ما اتعملش")
    return out_mp4


def validate(path: Path) -> dict:
    info = probe(path)
    checks = {
        "الأبعاد 1080×1920": info["width"] == V["width"] and info["height"] == V["height"],
        "الترميز H.264": info["vcodec"] == "h264",
        "الصوت AAC": info["acodec"] == "aac",
        f"المدة ≤{V['max_seconds']}s": 0 < info["duration"] <= V["max_seconds"],
        f"الحجم ≤{V['max_bytes'] // (1024 * 1024)}MB": info["bytes"] <= V["max_bytes"],
    }
    return {"info": info, "checks": checks, "ok": all(checks.values())}
