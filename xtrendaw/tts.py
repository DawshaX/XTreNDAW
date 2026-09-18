"""التعليق الصوتي + توقيت كلمة-بكلمة (أساس مزامنة الكابتشنز).

المصدر: edge-tts — مجاني، شغال من السيرفر (مايكروسوفت قفلته في المتصفحات
من 2025-12-17 بس السيرفر بيتحكم في هيدر الـWebSocket).
خدمة غير رسمية → أي فشل هنا لازم يطلع رسالة واضحة، مش استثناء غامض.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from pathlib import Path

from . import settings

_FFMPEG: str | None = None


def ffmpeg() -> str:
    """ffmpeg من النظام، وإلا من حزمة imageio-ffmpeg الثابتة."""
    global _FFMPEG
    if _FFMPEG is None:
        found = shutil.which("ffmpeg")
        if not found:
            import imageio_ffmpeg

            found = imageio_ffmpeg.get_ffmpeg_exe()
        _FFMPEG = found
    return _FFMPEG


def probe_duration(path: Path) -> float:
    """مدة ملف بالثواني — عن طريق ffmpeg (من غير ffprobe)."""
    import re

    r = subprocess.run([ffmpeg(), "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", r.stderr)
    if not m:
        return 0.0
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def _concat_wavs(wavs: list[Path], out: Path, gap: float) -> Path:
    import subprocess as _sp
    import tempfile as _tf

    list_f = out.with_suffix(".lst")
    sil = out.with_suffix(".sil.wav")
    _sp.run([ffmpeg(), "-y", "-f", "lavfi", "-i",
             "anullsrc=r=44100:cl=stereo", "-t", f"{gap:.2f}",
             "-c:a", "pcm_s16le", str(sil)], capture_output=True)
    lines = []
    for w in wavs:
        lines.append(f"file '{w.resolve().as_posix()}'")
        lines.append(f"file '{sil.resolve().as_posix()}'")
    list_f.write_text("\n".join(lines), encoding="utf-8")
    _sp.run([ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", str(list_f),
             "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(out)],
            capture_output=True, check=True)
    for w in list(wavs) + [sil, list_f]:
        w.unlink(missing_ok=True)
    return out


def to_wav(src: Path, dst: Path, rate: int = 44100) -> Path:
    """تحويل إلى WAV موحد — لازم قبل الدمج في الفيديو."""
    subprocess.run(
        [ffmpeg(), "-y", "-i", str(src), "-ar", str(rate), "-ac", "2",
         "-c:a", "pcm_s16le", str(dst)],
        capture_output=True, check=True,
    )
    return dst


def _spread(sentence: str, start: float, end: float) -> list[dict]:
    """يوزّع مدة جملة على كلماتها بوزن طول الكلمة.

    ده البديل الضروري لأن edge-tts 7.2.8 بيرجع SentenceBoundary فقط
    (مقيس على ar-EG-SalmaNeural وar-SA-ZariyahNeural وen-US-JennyNeural) —
    فأي كود بيعتمد على WordBoundary هياخد قايمة فاضية.
    """
    tokens = sentence.split()
    if not tokens:
        return []
    weights = [max(1, len(t)) for t in tokens]
    total_w = sum(weights)
    span = max(0.0, end - start)
    out: list[dict] = []
    cursor = start
    for tok, w in zip(tokens, weights):
        piece = span * w / total_w
        out.append({"word": tok, "start": round(cursor, 3),
                    "end": round(cursor + piece, 3)})
        cursor += piece
    return out


async def _synth_line(text: str, voice: str, out_mp3: Path,
                      rate: str | None = None, pitch: str | None = None,
                      volume: str | None = None) -> dict:
    """يولّد سطرًا ويعيد {words, sentences, source}.

    source = "word" (توقيتات أصلية من الخدمة) أو "sentence" (موزّعة من الجمل)
    أو "estimated" (مفيش حدود خالص).
    """
    import edge_tts

    word_bounds: list[dict] = []
    sent_bounds: list[dict] = []
    out_mp3.parent.mkdir(parents=True, exist_ok=True)

    communicate = edge_tts.Communicate(
        text, voice,
        rate=rate or settings.VOICE_RATE,
        pitch=pitch or settings.VOICE_PITCH,
        volume=volume or "+0%",
    )
    with open(out_mp3, "wb") as audio:
        async for chunk in communicate.stream():
            kind = chunk["type"]
            if kind == "audio":
                audio.write(chunk["data"])
            elif kind in ("WordBoundary", "SentenceBoundary"):
                # offset/duration بوحدات 100 نانوثانية
                rec = {
                    "text": chunk.get("text", ""),
                    "start": chunk["offset"] / 10_000_000,
                    "end": (chunk["offset"] + chunk["duration"]) / 10_000_000,
                }
                (word_bounds if kind == "WordBoundary" else sent_bounds).append(rec)

    if not out_mp3.exists() or out_mp3.stat().st_size == 0:
        raise RuntimeError(f"edge-tts رجع صوت فاضي للنص: {text[:40]!r}")

    if word_bounds:
        words = [{"word": w["text"], "start": round(w["start"], 3),
                  "end": round(w["end"], 3)} for w in word_bounds]
        return {"words": words, "sentences": sent_bounds, "source": "word"}

    if sent_bounds:
        words = []
        for sb in sent_bounds:
            words.extend(_spread(sb["text"], sb["start"], sb["end"]))
        if words:
            return {"words": words, "sentences": sent_bounds, "source": "sentence"}

    return {"words": [], "sentences": sent_bounds, "source": "empty"}


_SPEECH_MAP = [
    ("ﷺ", " صلى الله عليه وسلم "), ("ﷻ", " جل جلاله "),
    ("ﻻ", "لا"), ("ٱ", "ا"), ("ـ", ""),
]
import re as _re
_MARKS = _re.compile("[ؐ-ؚۖ-ۭ]")


def normalize_for_speech(text: str) -> str:
    """تطبيع للنطق: كل كلمة وكل حرف يوصل صح."""
    for a, b in _SPEECH_MAP:
        text = text.replace(a, b)
    text = _MARKS.sub("", text)
    return _re.sub(r"\s+", " ", text).strip()


def _sent_prosody(sent: str, base_rate: str) -> tuple[str, str, str]:
    s = sent.strip()
    if s.endswith("!") or "!" in s:
        return base_rate or "-14%", "+0Hz", "+25%"   # الله أكبر! أعلى وأفخم
    if s.endswith("؟") or "?" in s:
        return "-8%", "+2Hz", "+0%"                 # استفهام أرق
    if s.endswith("…"):
        return "-10%", "-1Hz", "+0%"                # وقفة تأمل
    return base_rate or "-6%", "-1Hz", "+0%"


def _piper_model() -> Path | None:
    """نموذج Piper من ريليز noor-models — يتخزن في /tmp (خارج مساحة العمل)."""
    import requests as _rq

    m = settings.PIPER_DIR / "ar-kareem.onnx"
    j = Path(str(m) + ".json")
    if not (m.exists() and j.exists()):
        try:
            m.parent.mkdir(parents=True, exist_ok=True)
            base = (f"https://github.com/DawshaX/XTreNDAW/releases/download/"
                    f"{settings.PIPER_RELEASE}")
            r = _rq.get(f"{base}/ar-kareem.onnx", timeout=(10, 90), stream=True)
            if not r.ok:
                return None
            with open(m, "wb") as f:
                for ch in r.iter_content(1 << 18):
                    f.write(ch)
            j.write_bytes(_rq.get(f"{base}/ar-kareem.json", timeout=60).content)
        except Exception:
            return None
    return m if (m.exists() and j.exists()) else None


def _piper_synth(text: str, out_wav: Path, model: Path) -> bool:
    import subprocess as _sp
    import sys as _sys

    try:
        r = _sp.run([_sys.executable, "-m", "piper", "--model", str(model),
                       "--output_file", str(out_wav), "--length_scale", "1.12"],
                      input=text.encode("utf-8"), capture_output=True, timeout=300)
        return r.returncode == 0 and out_wav.exists()
    except Exception:
        return False


def _piper_line(text: str, out_dir: Path, name: str) -> dict | None:
    """Piper — المحرك الاحتياطي (محلي 100%)."""
    model = _piper_model()
    if not model:
        return None
    raw = out_dir / f"{name}_p.wav"
    if _piper_synth(normalize_for_speech(text), raw, model):
        d = probe_duration(raw)
        if d > 0:
            wav = to_wav(raw, out_dir / f"{name}.wav")
            raw.unlink(missing_ok=True)
            return {"wav": wav, "duration": d,
                    "words": _spread(text, 0, d), "timing_source": "piper"}
    return None


# تنويع الأصوات: din بيغيّرها كل حلقة (تنوع بلا حدود)
VOICE_OVERRIDE_AR: str | None = None


def _orpheus_ar(text: str, out_dir: Path, name: str) -> dict | None:
    """صوت Orpheus العربي من Groq (أكثر دفئًا) — يرجع None لو مش متاح."""
    key = (settings.LLM or {}).get("key") or ""
    if not key.startswith("gsk"):
        return None
    import requests as _rq
    out_wav = out_dir / f"{name}_orp.wav"
    if out_wav.exists():
        d = probe_duration(out_wav)
        if d > 0:
            return {"wav": out_wav, "duration": d,
                    "words": _spread(text.strip(), 0, d),
                    "timing_source": "orpheus"}
    # تجربة واحدة فقط بمهلة قصيرة؛ لو الخدمة مش متاحة ننتقل فورًا لـedge/Piper.
    for v in ("lina",):
        try:
            r = _rq.post("https://api.groq.com/openai/v1/audio/speech",
                         headers={"Authorization": f"Bearer {key}"},
                         json={"model": "canopylabs/orpheus-arabic-saudi",
                               "voice": v,
                               "input": normalize_for_speech(text)},
                         timeout=25)
            if r.status_code != 200 or not r.content or r.content[:1] == b"{":
                continue
            mp3 = out_dir / f"{name}_orp.mp3"
            mp3.write_bytes(r.content)
            d = probe_duration(mp3)
            if d <= 0:
                continue
            w = to_wav(mp3, out_wav)
            return {"wav": w, "duration": d,
                    "words": _spread(text.strip(), 0, d),
                    "timing_source": "orpheus"}
        except Exception:
            continue
    return None


def synthesize_line(text: str, lang: str, out_dir: Path, name: str = "line",
                    rate: str | None = None, pitch: str | None = None) -> dict:
    """سطر واحد → {wav, duration, words, timing_source}.

    للعربي: Orpheus (Groq) أولًا، ثم نيورال طبيعي (edge) + نبرة جملة-بجملة،
    وPiper احتياطي محلي.
    """
    voice = settings.VOICE_EN if lang == "en" else (
        VOICE_OVERRIDE_AR or settings.VOICE_AR)
    out_dir.mkdir(parents=True, exist_ok=True)
    if lang == "ar":
        try:
            _o = _orpheus_ar(text, out_dir, name)
            if _o:
                return _o
        except Exception:
            pass

    if lang == "ar" and settings.TTS_ENGINE == "piper":
        _r = _piper_line(text, out_dir, name)
        if _r:
            return _r

    if lang == "ar":
        try:
            return _edge_ar(text, out_dir, name, rate, pitch, voice)
        except Exception:
            _r = _piper_line(text, out_dir, name)   # fallback محلي
            if _r:
                return _r
            raise
    return _edge_single(text, out_dir, name, rate, pitch, voice)


async def _bounded_synth(text: str, voice: str, out_mp3: Path,
                          rate: str | None = None, pitch: str | None = None,
                          volume: str | None = None) -> dict:
    """edge-tts بمهلة: الخدمة المجانية لا توقف دورة المصنع للأبد."""
    return await asyncio.wait_for(
        _synth_line(text, voice, out_mp3, rate=rate, pitch=pitch,
                    volume=volume), timeout=45)


def _edge_ar(text: str, out_dir: Path, name: str, rate, pitch, voice) -> dict:
    if True:
        text = normalize_for_speech(text)
        parts = [p for p in _re.split(r"(?<=[!؟…])", text) if p.strip()]
        if len(parts) > 1:
            wavs: list[Path] = []
            words: list[dict] = []
            cursor = 0.0
            gap = 0.14
            for i, sent in enumerate(parts):
                rr, pp, vv = _sent_prosody(sent, rate)
                mp3 = out_dir / f"{name}_s{i}.mp3"
                asyncio.run(_bounded_synth(sent, voice, mp3, rate=rr, pitch=pp,
                                           volume=vv))
                d = probe_duration(mp3)
                if d <= 0:
                    continue
                w = to_wav(mp3, out_dir / f"{name}_s{i}.wav")
                wavs.append(w)
                words.extend(_spread(sent.strip(), cursor, cursor + d))
                cursor += d + gap
            if wavs:
                final = out_dir / f"{name}.wav"
                _concat_wavs(wavs, final, gap)
                total = probe_duration(final)
                return {"wav": final, "duration": total, "words": words,
                        "timing_source": "sentence"}

    return _edge_single(text, out_dir, name, rate, pitch, voice)


def _edge_single(text: str, out_dir: Path, name: str, rate, pitch, voice) -> dict:
    mp3 = out_dir / f"{name}.mp3"
    r = asyncio.run(_bounded_synth(text, voice, mp3, rate=rate, pitch=pitch))
    duration = probe_duration(mp3)
    if duration <= 0:
        raise RuntimeError(f"مدة الصوت صفر لـ{name} — edge-tts فشل")

    words = r["words"]
    # لو الخدمة مارجعتش أي حد زمني: وزّع على مدة الملف الحقيقية
    if not words:
        words = _spread(text, 0.0, duration)
        r["source"] = "estimated"
    # تصحيح: التوقيتات لازم ماتعدّاش مدة الملف الفعلية
    elif words[-1]["end"] > duration:
        scale = duration / words[-1]["end"]
        words = [{"word": w["word"], "start": round(w["start"] * scale, 3),
                  "end": round(w["end"] * scale, 3)} for w in words]

    wav = to_wav(mp3, out_dir / f"{name}.wav")
    return {"mp3": mp3, "wav": wav, "duration": duration,
            "words": words, "timing_source": r["source"]}


def _prosody(seg: str, text: str, i: int) -> tuple[str, str, float]:
    """إخراج الصوت: سرعة/طبقة لكل نوع سطر + وقفة درامية بعده.

    hook = طاقة واندفاع · تحذير = تهدئة وثِقل · outro = دفء · facts = تنويع خفيف.
    """
    import random

    rng = random.Random(f"{i}:{text[:12]}")
    if seg == "hook":
        rate, pitch, gap = 10, 6, 0.38          # طاقة واندفاع
    elif seg == "takeaway":
        rate, pitch, gap = -7, -4, 0.5          # جدّ هادي — لحظة تستقر في القلب
    elif seg == "cta":
        rate, pitch, gap = 3, 2, 0.35           # دفء ولعب — المشاهد صاحب مكان
    elif seg == "outro":
        rate, pitch, gap = -6, -4, 0.30         # خاتمة دافية
    elif "تحذير" in text:
        rate, pitch, gap = -8, -6, 0.42         # ثِقل التحذير
    else:
        rate, pitch, gap = 2, 0, 0.30
    # لحظة جنون/فكاهة جوّا السطر؟ الجنون ياخد حقه هو كمان
    if any(k in text for k in ("استمتع", "بجد", "تدلع", "متستحش", "Mic drop", "Enjoy")):
        rate += 6
        pitch += 4
    rate += rng.randint(-2, 2)  # كسر الرتابة
    pitch += rng.randint(-2, 2)
    return (f"{'+' if rate >= 0 else ''}{rate}%",
            f"{'+' if pitch >= 0 else ''}{pitch}Hz", gap)


def synthesize_segments(segments: list[dict], lang: str, out_dir: Path) -> dict:
    """كل مقاطع الحلقة → ملف صوت واحد + توقيتات مطلقة لكل كلمة.

    segments: [{"seg": "hook"|"fact1"…, "text": "…"}]
    يعيد: {"wav", "total_duration", "items": [{seg, text, start, end, words}]}
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []
    wavs: list[Path] = []
    offset = 0.0

    for i, seg in enumerate(segments):
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        rate, pitch, gap = _prosody(seg.get("seg", ""), text, i)
        r = synthesize_line(text, lang, out_dir, name=f"seg{i}",
                            rate=rate, pitch=pitch)
        wavs.append(r["wav"])
        items.append({
            "seg": seg.get("seg", f"seg{i}"),
            "text": text,
            "start": round(offset, 3),
            "end": round(offset + r["duration"], 3),
            "timing_source": r["timing_source"],
            "words": [
                {**w, "start": round(w["start"] + offset, 3),
                 "end": round(w["end"] + offset, 3)}
                for w in r["words"]
            ],
        })
        offset += r["duration"]
        # وقفة درامية بين السطور (مش بعد الأخير)
        if i < len(segments) - 1:
            gap_wav = out_dir / f"gap{i}.wav"
            subprocess.run(
                [ffmpeg(), "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                 "-t", f"{gap:.2f}", "-c:a", "pcm_s16le", str(gap_wav)],
                capture_output=True, check=True,
            )
            wavs.append(gap_wav)
            offset += gap

    if not items:
        raise RuntimeError("مفيش مقاطع صوتية اتولدت — السيناريو فاضي")

    # دمج كل المقاطع في ملف واحد بالترتيب (re-encode عشان الترميز يتوحد)
    list_file = out_dir / "concat.txt"
    list_file.write_text(
        "".join(f"file '{p.name}'\n" for p in wavs), encoding="utf-8"
    )
    raw_wav = out_dir / "narration_raw.wav"
    subprocess.run(
        [ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
         "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(raw_wav)],
        capture_output=True, check=True, cwd=str(out_dir),
    )

    # ماسترينج: دفء + حضور + ضغط خفيف + توحيد مستوى → صوت "شخص" مش آلة
    final_wav = out_dir / "narration.wav"
    subprocess.run(
        [ffmpeg(), "-y", "-i", str(raw_wav), "-af",
         "highpass=f=90,"
         "equalizer=f=180:width_type=q:w=0.9:g=1.5,"
         "equalizer=f=3200:width_type=q:w=1.4:g=2.5,"
         "acompressor=threshold=0.1:ratio=3:attack=8:release=250,"
         "loudnorm=I=-16:TP=-1.5:LRA=11",
         "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(final_wav)],
        capture_output=True, check=True,
    )

    plan = {"wav": final_wav, "total_duration": offset, "items": items}
    (out_dir / "plan.json").write_text(
        json.dumps(
            {k: (str(v) if isinstance(v, Path) else v) for k, v in plan.items()},
            ensure_ascii=False, indent=1,
        ),
        encoding="utf-8",
    )
    return plan
