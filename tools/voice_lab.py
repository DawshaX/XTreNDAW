"""معمل أصوات النور: يولد عينات XTTS-v2 على الرنر ويرفعها لريليز noor-voices."""
import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("TTS_HOME", "/tmp/tts")
os.environ.setdefault("COQUI_TOS_AGREED", "1")

REFS = {
    "hamed": ("ar-SA-HamedNeural", "-8%", "-2Hz",
              "بسم الله الرحمن الرحيم. يا أخي الكريم، اسمع هذه الكلمات بقلبك، "
              "فإن فيها نورا وهداية وطمأنينة من الله سبحانه وتعالى."),
    "salma": ("ar-EG-SalmaNeural", "-6%", "-1Hz",
              "أهلا بيك يا صديقي الغالي. تعالى أقولك على حاجة جميلة، فيها خير "
              "ونور وراحة للقلب من ربنا سبحانه وتعالى."),
    "basim": ("ar-SA-ZariyahNeural", "-6%", "+0Hz",
              "مرحبا بك أخي الحبيب. هذه كلمات من نور، فيها خير وهداية وسكينة "
              "من الله عز وجل لكل من يستمع إليها."),
}

TEXT = ("وقف ثانية يا صديقي… الآية دي نزلت بمكة! بتقولك إن الله وحده "
        "المتفرد بالألوهية والربوبية، مفيش شريك له أبدا، الله أكبر! الله أكبر! "
        "هل هتنشر الخير؟")


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from xtrendaw.tts import normalize_for_speech

    import edge_tts
    from TTS.api import TTS

    out = Path("voice_lab_out")
    out.mkdir(exist_ok=True)
    for name, (voice, rate, pitch, ref_text) in REFS.items():
        ref = out / f"ref_{name}.mp3"
        asyncio.run(edge_tts.Communicate(ref_text, voice, rate=rate,
                                         pitch=pitch).save(ref))
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cpu")
        wav = out / f"xtts-{name}.wav"
        tts.tts_to_file(text=normalize_for_speech(TEXT), speaker_wav=str(ref),
                        language="ar", file_path=str(wav),
                        temperature=0.72, length_penalty=1.0,
                        repetition_penalty=5.0, speed=0.95)
        print(f"✓ {wav}", flush=True)
        del tts

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from xtrendaw import github_store
    tok = github_store._token()
    rel = github_store._ensure_tag(tok, "noor-voices", "عينات أصوات النور",
                                   "XTTS-v2 — أصوات معبرة")
    for f in sorted(out.glob("xtts-*.wav")):
        print(github_store.upload_file(tok, rel, f, f.name), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
