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
    dna = scene.get("dna") or {}
    grade_red = (f"eq=contrast=1.08:saturation=1.22:brightness=0.01,"
                 f"colorbalance=rs=0.14:rm=0.14:rh=0.08:gm=-0.05:bm=-0.14")
    if dna:
        # تدرّج الحلقة من محرك الأنماط (6 تدرجات × بصمة لون اللوحة)
        from . import multiverse as _mv
        grade = f"{_mv.GRADES[dna['grade']]},colorbalance={dna['cb']}"
    else:
        grade_soft = "eq=contrast=1.05:saturation=1.08:brightness=0.01"
        grade_calm = ("eq=contrast=1.06:saturation=1.07,"
                      "colorbalance=rs=0.07:rm=0.05:rh=0.02:bs=0.03:bm=0.07")
        grade = {"soft": grade_soft, "calm": grade_calm}.get(
            scene.get("grade"), grade_red)
    # لمسة سينمائية حية: فينييت وحبيبة من DNA الحلقة
    rich = (f"vignette={dna.get('vig', 'PI/5')},"
            f"noise=alls={dna.get('grain', 2)}:allf=t,unsharp=5:5:0.5")
    _tcol = {"black": "black", "white": "white",
             "palette": "0x" + dna.get("rgb", "#000000").lstrip("#"),
             "quick": "black"}.get(dna.get("transition", "black"), "black")
    _tdur = 0.10 if dna.get("transition") == "quick" else 0.20
    _tdip = max(0.0, seconds - _tdur)
    _fin = "" if scene.get("nofade_in") else "fade=t=in:st=0:d=0.24:"
    if scene.get("video"):
        # لقطة حية + زحف عمق بطيء (إحساس 3D مع بارالاكس الجسيمات)
        _lz = ""
        if dna.get("live_zoom"):
            _lz = (f"zoompan=z='1+0.05*on/{frames}':"
                   f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                   f"d=1:s={V['width']}x{V['height']}:fps={V['fps']},")
        parts = [
            f"[0:v]{grade},{_lz}{rich},"
            f"{_fin}color=0x0a0603,"
            f"fade=t=out:st={_tdip:.2f}:d={_tdur:.2f}:color={_tcol}[base]"
        ]
    else:
        # حركة مختلفة لكل مشهد: تقريب / إبعاد / بان يمين / بان شمال
        cx = "iw/2-(iw/zoom/2)"
        cy = "ih/2-(ih/zoom/2)"
        mv = dna.get("motion", _move_variant(out_mp4.name)) if dna \
            else _move_variant(out_mp4.name)
        if mv == 0:
            zp = f"z='1+0.11*on/{frames}':x='{cx}':y='{cy}'"
        elif mv == 1:
            zp = f"z='1.11-0.11*on/{frames}':x='{cx}':y='{cy}'"
        elif mv == 2:
            zp = f"z='1.08':x='(iw-iw/zoom)*(0.12+0.76*on/{frames})':y='{cy}'"
        elif mv == 3:
            zp = f"z='1.08':x='(iw-iw/zoom)*(0.88-0.76*on/{frames})':y='{cy}'"
        elif mv == 4:  # انزلاق قطري
            zp = (f"z='1.09':x='(iw-iw/zoom)*(0.1+0.8*on/{frames})':"
                  f"y='(ih-ih/zoom)*(0.8-0.7*on/{frames})'")
        elif mv == 5:  # تنفّس ناعم
            zp = f"z='1.06+0.05*sin(2*PI*on/{frames})':x='{cx}':y='{cy}'"
        elif mv == 6:  # بان رأسي
            zp = f"z='1.09':x='{cx}':y='(ih-ih/zoom)*(0.1+0.8*on/{frames})'"
        else:          # تقريب عميق بطيء
            zp = f"z='1+0.16*on/{frames}':x='{cx}':y='{cy}'"
        parts = [
            f"[0:v]scale={V['width'] * 3 // 2}:{V['height'] * 3 // 2},"
            # دفعة هوية حمراء سينمائية موحّدة فوق أي صورة مصدر
            f"{grade},{rich},"
            f"zoompan={zp}:d={frames}:s={V['width']}x{V['height']}:fps={V['fps']},"
            # انتقال ناعم بلون روح الحلقة — والدخول مشرّق لأول مشهد
            f"{_fin}color=0x140404,"
            f"fade=t=out:st={_tdip:.2f}:d={_tdur:.2f}:color={_tcol}[base]"
        ]
    if scene.get("glint"):
        from . import scenes as _sc
        inputs += ["-i", str(_sc.render_glint(out_mp4.parent / "glint.png"))]
    _dust = scene.get("dust") or []
    for _dp in _dust:
        inputs += ["-i", str(_dp)]
    n_in = len(inputs) // 2
    dust_i0 = n_in - len(_dust)  # أول فهرس لجسيمات
    prev = "[base]"
    for i in range(1, n_in):
        nxt = f"[v{i}]"
        if _dust and i >= dust_i0:
            # بارالاكس: البعيد أبطأ من القريب — عمق حقيقي
            _near = (i - dust_i0) == len(_dust) - 1
            _v = (dna.get("p_speed", 20) * (1.9 if _near else 1.0))
            _y = (f"-mod(t*{_v:.0f},H)" if dna.get("rise")
                  else f"mod(t*{_v:.0f},H)")
            parts.append(f"{prev}[{i}:v]overlay=x=0:y='{_y}'{nxt}")
        elif scene.get("glint") and i == dust_i0 - 1:
            parts.append(f"{prev}[{i}:v]overlay="
                         f"x='mod(t*230,W+900)-900':y=-200{nxt}")
        else:
            parts.append(f"{prev}[{i}:v]overlay=0:0{nxt}")
        prev = nxt

    _run([
        ffmpeg(), "-y", *inputs,
        "-filter_complex", ";".join(parts),
        "-map", prev, "-frames:v", str(frames), "-r", str(V["fps"]),
        "-c:v", V["vcodec"], "-preset", "fast", "-crf", "20",
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
          "-c:v", V["vcodec"], "-preset", "fast", "-crf", "20",
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
          "-c:v", V["vcodec"], "-preset", "fast", "-crf", "20",
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
