"""محرك النور — دعوة عامة: قرآن كامل بأصوات الشيوخ، تفسير ميسّر لكل آية،
أدعية، أحاديث، وقصص بمشاهد قوية. بلا موسيقى — التلاوة هي الصوت.

الأنواع: quran (سور قصيرة كونية) · qissa (قصص بآيات متتابعة سينمائية)
· tafsir (آية + تلاوة + شرح ميسّر) · dua · hadith
التلاوة من cdn.islamic.network (بلا مفتاح) والنص/التفسير من api.alquran.cloud.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import requests

from . import brand, captions, scenes, settings, video
from .tts import ffmpeg, probe_duration, synthesize_line, to_wav

UA = {"User-Agent": "XDAW-NOVA-noor/1.0 (free Islamic dawah shorts; educational)"}
APIQ = "https://api.alquran.cloud/v1"
CDN = "https://cdn.islamic.network/quran/audio/128"
CACHE = settings.STATE / "din_cache"

RECITERS = [
    ("ar.alafasy", "مشاري العفاسي"),
    ("ar.husary", "محمود خليل الحصري"),
    ("ar.minshawi", "محمد صديق المنشاوي"),
    ("ar.muhammadayyoub", "محمد أيوب"),
]

# مقاطع القرآن — مشاهد كونية/طبيعة حقيقية (الكلمة ↔ المشهد)
QURAN = [
    dict(id="ikhlas", surah=112, frm=1, to=4,
         scenes=["galaxy nebula space", "night sky stars milky way",
                 "universe planets", "moon clouds night"]),
    dict(id="falaq", surah=113, frm=1, to=5,
         scenes=["dawn sunrise mountains", "night darkness stars",
                 "wind trees dusk", "moon night"]),
    dict(id="nas", surah=114, frm=1, to=6,
         scenes=["heart sky clouds", "person praying silhouette mosque",
                 "night sky stars", "dawn light rays"]),
    dict(id="fatiha", surah=1, frm=1, to=7,
         scenes=["kaaba mecca", "mosque night lights", "sunrise mountains clouds",
                 "quran book mosque", "sky clouds light", "desert dunes sunset",
                 "stars night sky"]),
    dict(id="kursi", surah=2, frm=255, to=255,
         scenes=["universe galaxy stars", "throne light rays sky",
                 "night sky milky way", "cosmos nebula"]),
]

# قصص بآيات متتابعة — مشاهد سينمائية تاريخية
QISSA = [
    dict(id="naqat", surah=11, frm=64, to=67,
         scenes=["camel ancient desert village", "ancient stone village desert mountains",
                 "camel rock cliff desert", "ancient people robes desert",
                 "desert mountains dawn"]),
    dict(id="feel", surah=105, frm=1, to=5,
         scenes=["elephant desert ancient", "ancient army desert history",
                 "kaaba mecca old photo", "birds flock sky sunset",
                 "desert stones ground"]),
    dict(id="yusuf-dream", surah=12, frm=4, to=6,
         scenes=["desert night stars", "sun moon stars sky", "ancient caravan night",
                 "father son desert robes"]),
    dict(id="kahf", surah=18, frm=9, to=12,
         scenes=["cave inside light rays", "ancient cave mountains",
                 "sleeping cave darkness", "sunlight cave entrance"]),
]

# آيات الدعوة — تلاوة + شرح ميسّر بالصوت
TAFASEER = [
    dict(id="t-asr", surah=103, frm=1, to=3,
         scenes=["sunset hourglass sky", "time clock stars", "desert sunset",
                 "people helping hands"]),
    dict(id="t-thikr", surah=13, frm=28, to=28,
         scenes=["heart light chest", "calm lake sunrise", "prayer beads mosque",
                 "sky clouds peace"]),
    dict(id="t-yusr", surah=94, frm=5, to=8,
         scenes=["dark cloud silver lining", "dawn after night mountains",
                 "path light darkness", "sunrise hope sky"]),
    dict(id="t-thara", surah=99, frm=7, to=8,
         scenes=["tiny seed sprout", "mountain small big", "scales justice sky",
                 "desert atom sand"]),
]

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Ayah,Tajawal,84,&H00FFFFFF,&H000000FF,&H00000000,&H7A000000,-1,0,0,0,100,100,0,0,1,4,2,5,60,60,0,1
Style: Trj,Tajawal,44,&H00B6FFB6,&H000000FF,&H00000000,&H7A000000,0,0,0,0,100,100,0,0,1,3,1,2,60,60,150,1
Style: Shr,Tajawal,56,&H00D6C9A6,&H000000FF,&H00000000,&H7A000000,-1,0,0,0,100,100,0,0,1,3,1,2,70,70,220,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _t(s: float) -> str:
    h = int(s // 3600)
    m = int(s % 3600 // 60)
    sec = s % 60
    return f"{h}:{m:02d}:{sec:05.2f}"


def _get_json(url: str) -> dict:
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    return r.json()["data"]


def _ayah_audio(num: int, reciter: str, workdir: Path) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    mp3 = CACHE / f"{reciter}-{num}.mp3"
    if not mp3.exists():
        r = requests.get(f"{CDN}/{reciter}/{num}.mp3", headers=UA, timeout=120)
        r.raise_for_status()
        mp3.write_bytes(r.content)
    wav = workdir / f"ay{num}.wav"
    return to_wav(mp3, wav)


def _scene_media(i: int, spec: dict, workdir: Path, seed: str,
                 seconds: float) -> dict:
    """لقطة فيديو حيّة مطابقة للمعنى ← وإلا صورة حقيقية ← وإلا AI."""
    from . import footage

    q = spec["scenes"][i % len(spec["scenes"])]
    scdir = workdir / f"sc{i:02d}"
    clip = footage.fetch_clip(q, max(1.0, seconds), scdir, f"{seed}:{i}",
                              source="auto")
    if clip:
        return {"video": clip, "overlays": [], "grade": "soft"}
    base = scdir / "base.png"
    if spec.get("style") == "cinema":
        prompt = (f"{q}, ancient middle-east historical scene, cinematic film still, "
                  "realistic, dramatic natural light, 9:16 vertical, no text")
        if not scenes.fetch_ai_visual(prompt, base, hash(seed) % 10_000_000):
            scenes.fetch_real_visual(q, base) or scenes.render_bg(base, "fact1", seed)
    else:
        if not scenes.fetch_real_visual(q, base):
            scenes.fetch_ai_visual(
                f"{q}, majestic cosmic cinematic scene, 9:16 vertical, no text",
                base, hash(seed) % 10_000_000) or scenes.render_bg(base, "hook", seed)
    return {"base": base, "overlays": [], "grade": "soft"}


def _end_card(workdir: Path) -> dict:
    base = scenes.render_bg(workdir / "end" / "base.png", "outro", "noor-end")
    ov = [scenes._brand_layer(workdir / "end" / "brand.png")]
    from . import textrender
    ov.append(textrender.text_image(
        "نُورٌ يُشرِق… تابِع XDAW NOVA", workdir / "end" / "txt.png",
        canvas=(1080, 1920), font_size=64, y_ratio=0.5, fill="#ffd9a0",
        stroke="#000000", stroke_width=5))
    return {"base": base, "overlays": ov}


def produce_din(kind: str, workdir: Path, reciter_idx: int = 0) -> dict:
    """ينتج حلقة نور ويعيد {video, cover, report, title, id}."""
    workdir.mkdir(parents=True, exist_ok=True)
    reciter, rec_name = RECITERS[reciter_idx % len(RECITERS)]
    events: list[dict] = []
    wavs: list[Path] = []
    scene_list: list[dict] = []
    title = ""

    if kind in ("quran", "qissa", "tafsir"):
        pool = {"quran": QURAN, "qissa": QISSA, "tafsir": TAFASEER}[kind]
        spec = pool[reciter_idx % len(pool)]  # تنويع بسيط مع القارئ
        spec = {**spec, "style": "cinema" if kind == "qissa" else "cosmic"}
        ayahs = _get_json(f"{APIQ}/surah/{spec['surah']}/quran-uthmani")["ayahs"]
        sel = [a for a in ayahs if spec["frm"] <= a["numberInSurah"] <= spec["to"]]
        sname = _get_json(f"{APIQ}/surah/{spec['surah']}/quran-uthmani")["name"]
        title = f"{sname} ﴿{spec['frm']}–{spec['to']}﴾ — {rec_name}"
        tafs = None
        if kind == "tafsir":
            t = _get_json(f"{APIQ}/surah/{spec['surah']}/ar.muyassar")["ayahs"]
            tafs = {a["numberInSurah"]: a["text"] for a in t}

        off = 0.0
        for i, a in enumerate(sel):
            wav = _ayah_audio(a["number"], reciter, workdir)
            d = probe_duration(wav)
            wavs.append(wav)
            events.append({"style": "Ayah", "text": a["text"],
                           "start": off, "end": off + d})
            sc = _scene_media(i, spec, workdir, spec["id"], d)
            sc.update(start=off, end=off + d)
            scene_list.append(sc)
            off += d
            if tafs:
                r = synthesize_line(f"قال المفسر: {tafs[a['numberInSurah']]}", "ar",
                                    workdir / "shr", name=f"t{i}",
                                    rate="-8%", pitch="-2Hz")
                wavs.append(r["wav"])
                for ch in captions.chunk_words(r["words"]):
                    events.append({"style": "Shr", "text": ch["text"],
                                   "start": off + ch["start"], "end": off + ch["end"]})
                off += r["duration"] + 0.25
                wavs.append(_silence(workdir / f"sp{i}.wav", 0.25))
        # سطر الترجمة للمقطع كله (قراءة عالمية)
        try:
            en = _get_json(f"{APIQ}/surah/{spec['surah']}/en.sahih")["ayahs"]
            en_sel = [a["text"] for a in en
                      if spec["frm"] <= a["numberInSurah"] <= spec["to"]]
            total = off
            for i, et in enumerate(en_sel):
                s = total * i / max(1, len(en_sel))
                e = total * (i + 1) / max(1, len(en_sel))
                events.append({"style": "Trj", "text": et, "start": s, "end": e})
        except Exception:
            pass
        ep_id = f"noor-{spec['id']}-{reciter.split('.')[-1]}"
    else:  # dua / hadith من المخزون المحلي
        stock = json.loads((settings.ROOT / "content" / "din_stock.json")
                           .read_text(encoding="utf-8"))
        items = stock["duas"] if kind == "dua" else stock["hadiths"]
        item = items[reciter_idx % len(items)]
        label = "دعاء" if kind == "dua" else "قال رسول الله ﷺ"
        title = f"{label}: {item['text'][:40]}…"
        r = synthesize_line(item["text"], "ar", workdir / "vox", name="main",
                            rate="-8%", pitch="-2Hz")
        wavs.append(r["wav"])
        intro = synthesize_line(label, "ar", workdir / "vox", name="intro",
                                rate="-6%", pitch="-3Hz")
        wavs = [intro["wav"], _silence(workdir / "g0.wav", 0.3)] + wavs
        base_off = intro["duration"] + 0.3
        for ch in captions.chunk_words(intro["words"], size=3):
            events.append({"style": "Shr", "text": ch["text"],
                           "start": ch["start"], "end": ch["end"]})
        for ch in captions.chunk_words(r["words"]):
            events.append({"style": "Ayah", "text": ch["text"],
                           "start": base_off + ch["start"],
                           "end": base_off + ch["end"]})
        events.append({"style": "Trj", "text": item["src"],
                       "start": base_off, "end": base_off + r["duration"]})
        off = base_off + r["duration"]
        qs = ["mosque night lights", "kaaba mecca", "quran book candle",
              "praying hands sky", "dawn mountains peace"]
        n = 3
        for i in range(n):
            s = off * i / n
            e = off * (i + 1) / n
            sc = _scene_media(i, {"scenes": qs, "style": "cosmic"},
                              workdir, kind, e - s)
            sc.update(start=s, end=e)
            scene_list.append(sc)
        ep_id = f"noor-{kind}-{reciter_idx % len(items)}"

    # كرت الختام + صمت 3ث
    wavs.append(_silence(workdir / "end.wav", 3.0))
    scene_list.append({**_end_card(workdir), "start": off, "end": off + 3.0})
    total = off + 3.0

    # دمج الصوت + كتابة ASS + تجميع
    list_f = workdir / "vox.txt"
    list_f.write_text("".join(f"file '{p.as_posix()}'\n" for p in wavs),
                      encoding="utf-8")
    vox = workdir / "vox.wav"
    subprocess.run([ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", str(list_f),
                    "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(vox)],
                   capture_output=True, check=True)

    ass = workdir / "din.ass"
    lines = [ASS_HEADER]
    for ev in events:
        txt = ev["text"].replace("\n", " ")
        lines.append(f"Dialogue: 0,{_t(ev['start'])},{_t(ev['end'])},{ev['style']},"
                     f",0,0,0,,{{\\fad(450,350)}}{txt}\n")
    ass.write_text("".join(lines), encoding="utf-8")

    out = settings.OUT / f"{ep_id}.mp4"
    video.assemble({"wav": vox, "total_duration": total}, scene_list, ass,
                   out, workdir, music=None)
    cover = settings.OUT / f"{ep_id}-cover.png"
    brand.compose_cover({"id": ep_id, "title_ar": title,
                         "tags": "نور,قرآن,دعوة,XDAWNOVA"}, cover)
    return {"video": out, "cover": cover, "report": video.validate(out),
            "title": title, "id": ep_id}


def _silence(path: Path, sec: float) -> Path:
    subprocess.run([ffmpeg(), "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                    "-t", f"{sec:.2f}", "-c:a", "pcm_s16le", str(path)],
                   capture_output=True, check=True)
    return path


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", default="quran",
                    choices=["quran", "qissa", "tafsir", "dua", "hadith"])
    ap.add_argument("--reciter", type=int, default=0)
    a = ap.parse_args()
    r = produce_din(a.kind, settings.WORK / "din", a.reciter)
    print(r["title"], "|", r["report"]["ok"], r["report"]["info"]["duration"])
