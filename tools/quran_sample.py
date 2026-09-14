# -*- coding: utf-8 -*-
"""حلقة قرآن عيّنة — تُنتج على الرنر وتُرفع لريليز noor-samples للمراجعة.

المدخلات من البيئة: SAMPLE_SURAH, SAMPLE_FRM, SAMPLE_TO, SAMPLE_REC (رقم القارئ).
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GENERIC_SCENES = ["ancient middle-east landscape golden hour",
                  "night sky stars milky way", "desert sunrise dunes",
                  "olive tree branch sunlight", "calm sea waves sunrise",
                  "old mosque arch light"]


def main() -> int:
    from xtrendaw import din, github_store

    surah = int(os.environ.get("SAMPLE_SURAH", "93"))
    frm = int(os.environ.get("SAMPLE_FRM", "1"))
    to = int(os.environ.get("SAMPLE_TO", "11"))
    rec = int(os.environ.get("SAMPLE_REC", "4"))

    workdir = ROOT / "work" / "sample"
    workdir.mkdir(parents=True, exist_ok=True)
    spec = {"id": f"sample-s{surah:03d}-{frm}", "surah": surah,
            "frm": frm, "to": to, "scenes": GENERIC_SCENES}
    tts = os.environ.get("SAMPLE_TTS", "") == "1"
    r = din.produce_din("quran", workdir, rec, spec, tts_recite=tts)
    if not r["report"]["ok"]:
        print("فشل فحص المواصفات:", r["report"]["checks"])
        return 1
    print("✓ حلقة العينة:", r["video"], r["title"])

    tok = github_store._token()
    rel = github_store._ensure_tag(tok, "noor-samples", "عينات نوفا للمراجعة",
                                   "حلقات عينة قبل النشر")
    url = github_store.upload_file(tok, rel, Path(r["video"]), "sample.mp4")
    print("SAMPLE_URL:", url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
