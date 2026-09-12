"""الكابتشنز — ملف ASS بتوقيتات كلمة-بكلمة.

ليه ASS مش صور PNG:
- الـrunner هنا عنده ~2GB RAM؛ 15+ مدخل صورة للـoverlay بيموّت ffmpeg (OOM، exit -9).
  اتأكد بالقياس: التجميع وصل فريم 309 واتقتل.
- ASS = فلتر واحد، وlibass + libfribidi بيتكفلوا بالتشكيل العربي والاتجاه.
"""
from __future__ import annotations

from pathlib import Path

from . import settings

V = settings.VIDEO
WORDS_PER_CHUNK = 5
MIN_CHUNK_SEC = 0.40

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},{size},&H00FFFFFF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,{outline},{shadow},2,{ml},{mr},{mv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def chunk_words(words: list[dict], size: int = WORDS_PER_CHUNK) -> list[dict]:
    """كلمات → مجموعات {text, start, end}، من غير فراغات ميتة بينها."""
    chunks: list[dict] = []
    for i in range(0, len(words), size):
        group = words[i:i + size]
        if not group:
            continue
        chunks.append({
            "text": " ".join(g["word"] for g in group),
            "start": group[0]["start"],
            "end": group[-1]["end"],
        })
    for a, b in zip(chunks, chunks[1:]):
        if b["start"] > a["end"]:
            a["end"] = b["start"]          # نمدّ لحد بداية اللي بعده
    for c in chunks:
        if c["end"] - c["start"] < MIN_CHUNK_SEC:
            c["end"] = c["start"] + MIN_CHUNK_SEC
    return chunks


def _ass_time(seconds: float) -> str:
    """ASS: H:MM:SS.cc (أجزاء من المئة)."""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _escape(text: str) -> str:
    """ASS: فواصل الأسطر بـ\\N، والأقواس {} بتتهرَّب."""
    return text.replace("{", "(").replace("}", ")").replace("\n", "\\N")


def build_ass(plan: dict, out_path: Path,
              font_name: str = "Tajawal", font_size: int = 68) -> tuple[Path, list[dict]]:
    """خطة الصوت → ملف ASS + قايمة الشرائح (للتقارير والاختبارات)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    chunks: list[dict] = []
    for item in plan["items"]:
        chunks.extend(chunk_words(item["words"]))
    if not chunks:
        raise RuntimeError("مفيش كابتشنز — خطة الصوت فاضية")

    chunks.sort(key=lambda c: c["start"])
    for a, b in zip(chunks, chunks[1:]):        # منع التداخل
        if a["end"] > b["start"]:
            a["end"] = b["start"]

    # الهامش السفلي: 12% من الارتفاع — بعيد عن عناصر واجهة المنصات
    mv = int(V["height"] * 0.13)
    header = HEADER.format(
        w=V["width"], h=V["height"], font=font_name, size=font_size,
        outline=6, shadow=2, ml=70, mr=70, mv=mv,
    )
    lines = [header]
    for c in chunks:
        lines.append(
            f"Dialogue: 0,{_ass_time(c['start'])},{_ass_time(c['end'])},"
            f"Cap,,0,0,0,,{_escape(c['text'])}\n"
        )

    out_path.write_text("".join(lines), encoding="utf-8")
    return out_path, chunks
