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

# قرّاء بمصادر أقل عرضة للمطالبات + بيت ريت مختلف لكل مصدر
RECITERS = [
    ("ar.husary", "محمود خليل الحصري", 128),
    ("ar.minshawi", "محمد صديق المنشاوي", 128),
    ("ar.abdulbasitmurattal", "عبد الباسط عبد الصمد", 64),
    ("ar.abdurrahmaansudais", "عبدالرحمن السديس", 64),
    # قراء نادرون — توزيع أقل = بصمة أقل تسجيلًا عند Content ID
    ("ar.hanirifai", "هاني الرفاعي", 64),
    ("ar.husarymujawwad", "محمود خليل الحصري (مجوَّد)", 128),
    ("ar.muhammadjibreel", "محمد جبريل", 128),
    ("ar.aymanswoaid", "أيمن سويد", 128),
    ("ar.hudhaify", "علي الحذيفي", 128),
    ("ar.shaatree", "أبو بكر الشاطري", 128),
    ("ar.abdullahbasfar", "عبدالله بصفر", 64),
    ("ar.mahermuaiqly", "ماهر المعيقلي", 128),
    ("ar.saoodshuraym", "سعود الشريم", 64),
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
    dict(id="naqat", title="ناقة صالح", surah=11, frm=64, to=67,
         scenes=["camel ancient desert village", "ancient stone village desert mountains",
                 "camel rock cliff desert", "ancient people robes desert",
                 "desert mountains dawn"]),
    dict(id="feel", title="أصحاب الفيل", surah=105, frm=1, to=5,
         scenes=["elephant desert ancient", "ancient army desert history",
                 "kaaba mecca old photo", "birds flock sky sunset",
                 "desert stones ground"]),
    dict(id="yusuf-dream", title="رؤيا يوسف", surah=12, frm=4, to=6,
         scenes=["desert night stars", "sun moon stars sky", "ancient caravan night",
                 "father son desert robes"]),
    dict(id="kahf", title="أهل الكهف", surah=18, frm=9, to=12,
         scenes=["cave inside light rays", "ancient cave mountains",
                 "sleeping cave darkness", "sunlight cave entrance"]),
    dict(id="adam", title="آدم وتعلّم الأسماء", surah=2, frm=30, to=33,
         scenes=["garden eden trees light", "angels light sky", "first man earth dawn",
                 "stars cosmos creation"]),
    dict(id="nuh", title="سفينة نوح", surah=11, frm=37, to=41,
         scenes=["ancient wooden ship flood", "heavy rain clouds sea", "mountain waves storm",
                 "dove bird sky calm"]),
    dict(id="ibrahim-nar", title="نار إبراهيم بردًا", surah=21, frm=68, to=70,
         scenes=["huge fire flames night", "man standing fire calm", "green garden from ashes",
                 "ancient babylon ruins"]),
    dict(id="musa", title="عصا موسى", surah=20, frm=17, to=21,
         scenes=["ancient egypt nile river", "wooden staff hand desert", "snake sand ancient",
                 "pharaoh palace ruins"]),
    dict(id="yunus", title="يونس في بطن الحوت", surah=37, frm=139, to=144,
         scenes=["whale deep sea dark", "man sea night waves", "glowing plankton ocean deep",
                 "pumpkin plant shore"]),
    dict(id="sulayman", title="سليمان والنملة", surah=27, frm=17, to=19,
         scenes=["ancient army desert march", "tiny ant sand closeup", "king throne ancient",
                 "birds flock sky army"]),
    dict(id="zakariya", title="دعاء زكريا", surah=19, frm=2, to=6,
         scenes=["old man praying mihrab", "candle light ancient mosque", "white hair hands dua",
                 "dawn light window"]),
    dict(id="maryam", title="مريم ونخلة الرطب", surah=19, frm=22, to=26,
         scenes=["palm tree desert oasis", "dates palm closeup", "stream water desert",
                 "mother baby light"]),
    dict(id="ayyub", title="صبر أيوب", surah=38, frm=41, to=43,
         scenes=["sick man patient ancient", "spring water gushing rock", "family reunion desert",
                 "green field after rain"]),
    dict(id="dhaby", title="فداء إسماعيل", surah=37, frm=102, to=107,
         scenes=["father son mountain walk", "ram mountain dawn", "kaaba ancient desert",
                 "sky clouds mercy light"]),
    dict(id="hijra", title="هجرة النبي ﷺ والغار", surah=9, frm=40, to=40,
         scenes=["cave entrance spider web", "two men cave light", "desert night journey camels",
                 "dawn horizon hijra"]),
    dict(id="badr", title="نصر بدر", surah=3, frm=123, to=125,
         scenes=["ancient battle desert dawn", "angels light sky riders", "desert camp night fires",
                 "victory sunrise desert"]),
    {"id": "ukhdud", "title": "أصحاب الأخدود", "surah": 85, "frm": 4, "to": 9, "scenes": ["ancient fire trench desert night", "believers standing firm crowd", "ancient king palace throne", "fire burning pit desert", "stars night sky hope"]},
    {"id": "talut", "title": "طالوت وجالوت", "surah": 2, "frm": 246, "to": 251, "scenes": ["ancient army river crossing", "young shepherd with sling", "giant warrior battlefield", "ancient battle desert dust", "victory sunrise soldiers"]},
    {"id": "baqara-q", "title": "قصة البقرة", "surah": 2, "frm": 67, "to": 73, "scenes": ["cow grazing green field", "ancient israelite village", "people arguing prophets", "golden light miracle", "ancient scroll torah"]},
    {"id": "khidr", "title": "موسى والخضر", "surah": 18, "frm": 65, "to": 75, "scenes": ["two travelers sea shore", "wooden boat old sea", "ancient wall rebuilding village", "sea waves journey mystery", "wisdom old man light"]},
    {"id": "jannatayn", "title": "صاحب الجنتين", "surah": 18, "frm": 32, "to": 43, "scenes": ["lush garden grape vines", "two beautiful gardens fountain", "storm destroying garden night", "rich man proud palace", "ruins garden regret dawn"]},
    {"id": "uzair", "title": "الذي نام مئة عام", "surah": 2, "frm": 259, "to": 259, "scenes": ["ancient ruined city walls", "donkey standing desert road", "bones rising life miracle", "sunrise sunset time lapse", "rebuilt ancient town light"]},
    {"id": "abnay-adam", "title": "ابنا آدم", "surah": 5, "frm": 27, "to": 31, "scenes": ["two brothers ancient field", "raven digging earth", "green hills ancient land", "sacrifice offering fire sky", "lonely man regret sunset"]},
    {"id": "luqman", "title": "وصايا لقمان", "surah": 31, "frm": 12, "to": 19, "scenes": ["wise father son talking", "ancient simple home", "mountains steadfast rock", "bird flying sky small", "path humble walk sunset"]},
    {"id": "namla", "title": "سليمان والنملة", "surah": 27, "frm": 17, "to": 19, "scenes": ["ant on ground close up", "ancient army marching valley", "king prophet smiling sky", "ants colony moving", "desert valley sunlight"]},
    {"id": "hudhud", "title": "الهدهد وملكة سبأ", "surah": 27, "frm": 20, "to": 28, "scenes": ["hoopoe bird flying", "ancient queen throne palace", "letter scroll royal seal", "sun worshipping people ancient", "majestic kingdom gold"]},
    {"id": "sabt", "title": "أصحاب السبت", "surah": 7, "frm": 163, "to": 166, "scenes": ["sea shore fishing village", "fish jumping water sabbath", "ancient seaside town walls", "storm sea punishment waves", "quiet empty village lesson"]},
    {"id": "firawn", "title": "غرق فرعون", "surah": 10, "frm": 90, "to": 92, "scenes": ["sea parting walls water", "ancient egypt chariots army", "pharaoh drowning waves", "pyramids desert ancient egypt", "calm sea after storm dawn"]},
    {"id": "abrar", "title": "الأبرار في الجنة", "surah": 76, "frm": 8, "to": 12, "scenes": ["poor family sharing food", "orphan receiving bread kindness", "captive fed mercy hands", "paradise garden rivers light", "silk garments reward glow"]},
    {"id": "qarun", "title": "قارون وكنوزه", "surah": 28, "frm": 76, "to": 82, "scenes": ["treasure gold chests ancient", "rich man arrogant crowd", "earth swallowing palace ruin", "gold coins shining dark", "desert emptiness lesson dawn"]},
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
Style: Ayah,Amiri,92,&H0039C8FF,&H00F2F2F2,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,4,2,5,70,70,0,1
Style: Trj,Tajawal,46,&H00B6FFB6,&H000000FF,&H00000000,&H8A000000,0,0,0,0,100,100,0,0,1,3,1,2,60,60,150,1
Style: Shr,Amiri,56,&H00D6C9A6,&H000000FF,&H00000000,&H8A000000,-1,0,0,0,100,100,0,0,1,3,1,2,70,70,220,1
Style: Calm,Amiri,54,&H00FFFFFF,&H00000000,&H00101010,&H8A000000,0,0,0,0,0,100,100,0,0,1,2,2,2,70,70,300,1
Style: Hdr,Amiri Quran,60,&H009AD8FF,&H000000FF,&H00000000,&H8A000000,-1,0,0,0,100,100,0,0,1,3,2,8,60,60,90,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _t(s: float) -> str:
    h = int(s // 3600)
    m = int(s % 3600 // 60)
    sec = s % 60
    return f"{h}:{m:02d}:{sec:05.2f}"


_AR = "٠١٢٣٤٥٦٧٨٩"


def _ar_num(n: int) -> str:
    return "".join(_AR[int(c)] for c in str(n))


def _trim_sent(text: str, limit: int = 200) -> str:
    """قصّ على حد جملة حتى تفضل الفائدة مقروءة."""
    t = text.strip().replace("\n", " ")
    if len(t) <= limit:
        return t
    cut = t[:limit]
    for sep in ("۔", ".", "،", "؛", " "):
        i = cut.rfind(sep)
        if i > limit // 2:
            return cut[: i + 1].strip()
    return cut + "…"


def _get_json(url: str) -> dict:
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    return r.json()["data"]


def _ayah_audio(num: int, reciter: str, workdir: Path, kbps: int = 128) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    mp3 = CACHE / f"{reciter}-{num}.mp3"
    if not mp3.exists():
        _tried = []
        for _kb in dict.fromkeys((kbps, 128, 64)):   # الأعلى أولًا ثم تراجع
            try:
                r = requests.get(
                    f"{CDN.replace('/128', f'/{_kb}')}/{reciter}/{num}.mp3",
                    headers=UA, timeout=120)
                if r.ok and len(r.content) > 1000:
                    mp3.write_bytes(r.content)
                    break
            except Exception:
                pass
            _tried.append(_kb)
        else:
            raise RuntimeError(f"تلاوة {reciter}:{num} مش متاحة ({_tried})")
    wav = workdir / f"ay{num}.wav"
    return to_wav(mp3, wav)


def _scene_media(i: int, spec: dict, workdir: Path, seed: str,
                 seconds: float) -> dict:
    """لقطة فيديو حيّة مطابقة للمعنى ← وإلا صورة حقيقية ← وإلا AI."""
    from . import footage

    q = spec["scenes"][i % len(spec["scenes"])]
    # تنويع حقيقي: كل مشهد بزاوية/إضاءة مختلفة — بلا تكرار بين الحلقات
    q = f"{q}, {['cinematic wide shot', 'golden hour light', 'aerial view', 'close-up detail', 'dramatic side light'][i % 5]}"
    scdir = workdir / f"sc{i:02d}"
    clip = footage.fetch_clip(q, max(1.0, seconds), scdir, f"{seed}:{i}",
                              source="auto")
    if clip:
        return {"video": clip, "overlays": [],
                "grade": spec.get("grade", "soft")}
    base = scdir / "base.png"
    if spec.get("style") == "cinema":
        prompt = (f"{q}, ancient middle-east historical scene, cinematic film still, "
                  "realistic, dramatic natural light, 9:16 vertical, no text")
        if not scenes.fetch_ai_visual(prompt, base, hash(seed) % 10_000_000):
            (scenes.fetch_real_visual(q, base)
             or scenes.fetch_library_visual(q, base)
             or scenes.render_bg(base, "fact1", seed))
    else:
        if not (scenes.fetch_real_visual(q, base) or scenes.fetch_library_visual(q, base)):
            scenes.fetch_ai_visual(
                f"{q}, majestic cosmic cinematic scene, 9:16 vertical, no text",
                base, hash(seed) % 10_000_000) or scenes.render_bg(base, "hook", seed)
    return {"base": base, "overlays": [], "grade": "soft"}


def _end_card(workdir: Path, fayda: str) -> dict:
    """كرت الختام: خلفية البراند النيون + اللوجو + فائدة الآية/الدعاء."""
    from . import textrender

    d = workdir / "end"
    ov = [scenes._brand_layer(d / "brand.png")]
    ov.append(textrender.text_image(
        "﴿ فَائِدَةٌ وَنُور ﴾", d / "h.png", font_size=56, y_ratio=0.28,
        fill="#ffd9a0", stroke_width=4,
        font_path=settings.FONTS / "AmiriQuran-Regular.ttf"))
    ov.append(textrender.text_image(fayda, d / "f.png", font_size=48,
                                    y_ratio=0.52, fill="#f7ecd7",
                                    stroke_width=4))
    ov.append(textrender.text_image("انشر الخير — XDAW NOVA", d / "b.png",
                                    font_size=34, y_ratio=0.90,
                                    fill="#ffd166", stroke_width=3))
    return {"base": scenes.render_bg(d / "base.png", "outro", "noor-end"),
            "overlays": ov}


def produce_din(kind: str, workdir: Path, reciter_idx: int = 0,
                spec: dict | None = None,
                tts_recite: bool = False) -> dict:
    """ينتج حلقة نور ويعيد {video, cover, report, title, id}."""
    workdir.mkdir(parents=True, exist_ok=True)
    reciter, rec_name, kbps = RECITERS[reciter_idx % len(RECITERS)]
    from . import state as _state
    _bad = _state.reciter_badlist()
    if reciter in _bad:
        for _alt in RECITERS:
            if _alt[0] not in _bad:
                reciter, rec_name, kbps = _alt
                break
    events: list[dict] = []
    wavs: list[Path] = []
    scene_list: list[dict] = []
    title = ""

    if kind in ("quran", "qissa", "tafsir"):
        pool = {"quran": QURAN, "qissa": QISSA, "tafsir": TAFASEER}[kind]
        spec = spec or pool[reciter_idx % len(pool)]
        spec = {**spec, "style": "cinema" if kind == "qissa" else "cosmic"}
        ayahs = _get_json(f"{APIQ}/surah/{spec['surah']}/quran-uthmani")["ayahs"]
        sel = [a for a in ayahs if spec["frm"] <= a["numberInSurah"] <= spec["to"]]
        # حماية المواصفات: التلاوة الطويلة → قصّ عدد الآيات تلقائيا
        max_rec = 30.0 if kind == "tafsir" else 63.0
        _durs = [probe_duration(_ayah_audio(a["number"], reciter, workdir, kbps))
                 for a in sel]
        while len(sel) > 1 and sum(_durs) > max_rec:
            sel.pop()
            _durs.pop()
            spec = {**spec, "to": sel[-1]["numberInSurah"]}
        if kind == "tafsir":
            # شرح المفسر بيضيف وقت — 3 آيات كفاية عشان نفضل تحت 90 ثانية
            while len(sel) > 3:
                sel.pop()
                _durs.pop()
                spec = {**spec, "to": sel[-1]["numberInSurah"]}
        q = _get_json(f"{APIQ}/surah/{spec['surah']}/quran-uthmani")
        sname = q["name"]
        meta = _get_json(f"{APIQ}/surah/{spec['surah']}")
        rev = "مَكِّيَّة" if meta.get("revelationType") == "Meccan" else "مَدَنِيَّة"
        title = f"{sname} ﴿{spec['frm']}–{spec['to']}﴾ — {rec_name}"
        t = _get_json(f"{APIQ}/surah/{spec['surah']}/ar.muyassar")["ayahs"]
        tafs = {a["numberInSurah"]: a["text"] for a in t}
        fayda = _trim_sent(tafs.get(spec["frm"], ""), 190)
        fayda = f"نزلت {rev}. {fayda}"
        # لمسة المراجع الناجحة: مود بصري واحد موحّد للفيديو كله
        if kind in ("quran", "tafsir"):
            import hashlib as _h
            _moods = [
                ["sunset over calm sea", "ocean horizon golden light",
                 "sun setting into water", "slow sea waves golden hour"],
                ["candle flame close up", "warm candlelight dark room",
                 "candles glowing night", "lantern warm light night"],
                ["rain on window night", "rainy street lights reflection",
                 "window rain drops dark", "night rain city glow"],
                ["mosque silhouette dusk", "minarets sunset sky",
                 "mosque dome blue hour", "masjid lights night"],
                ["starry night sky", "milky way over desert",
                 "stars night clouds", "moon night sky calm"],
                ["old street lantern night", "vintage room warm light",
                 "flowers by window dusk", "cozy interior candle light"],
            ]
            _mi = int(_h.sha1(spec["id"].encode()).hexdigest(), 16) % len(_moods)
            spec = {**spec, "scenes": _moods[_mi], "grade": "calm"}
        try:
            _en_ay = _get_json(f"{APIQ}/surah/{spec['surah']}/en.sahih")["ayahs"]
            _en_txt = {a["numberInSurah"]: a["text"] for a in _en_ay}
        except Exception:
            _en_txt = {}

        # ترويسة السورة أول ٣٫٥ ثانية
        events.append({"style": "Hdr",
                       "text": f"{sname} • {rev}",
                       "start": 0.0, "end": 1.35})

        if tts_recite:
            rec_name = "بصوت نُور"
        off = 0.0
        for i, a in enumerate(sel):
            if tts_recite:
                # تلاوة مملوكة لنا 100% — صفر حقوق ملكية للأبد
                _r = synthesize_line(a["text"], "ar", workdir / "rec",
                                     name=f"r{a['number']}", rate="-20%")
                wav, d = _r["wav"], _r["duration"]
            else:
                wav = _ayah_audio(a["number"], reciter, workdir, kbps)
                d = probe_duration(wav)
            wavs.append(wav)
            if kind in ("quran", "tafsir"):
                # مقاطع قصيرة ثنائية اللغة متتابعة — أسلوب القنوات الهادئة
                _ar_w = a["text"].split()
                _en_w = _en_txt.get(a["numberInSurah"], "").split()
                _nfr = max(1, min(8, round(d / 4.5)))
                _lw = max(1, len(_ar_w))
                for _f in range(_nfr):
                    _a0 = _f * len(_ar_w) // _nfr
                    _a1 = (_f + 1) * len(_ar_w) // _nfr
                    _e0 = _f * len(_en_w) // _nfr
                    _e1 = (_f + 1) * len(_en_w) // _nfr
                    _ar_frag = " ".join(_ar_w[_a0:_a1])
                    if _f == _nfr - 1:
                        _ar_frag += f" ﴿{_ar_num(a['numberInSurah'])}﴾"
                    _en_frag = " ".join(_en_w[_e0:_e1])
                    events.append({
                        "style": "Calm",
                        "text": _ar_frag + "\\N" + _en_frag,
                        "start": off + d * _a0 / _lw,
                        "end": off + d * _a1 / _lw})
            else:
                events.append({"style": "Ayah",
                               "text": f"{a['text']} ﴿{_ar_num(a['numberInSurah'])}﴾",
                               "start": off, "end": off + d})
            _nsc = max(1, min(4, int(d // 7)))
            for _si in range(_nsc):
                _s0 = off + d * _si / _nsc
                _s1 = off + d * (_si + 1) / _nsc
                sc = _scene_media(i + _si, spec, workdir, spec["id"], _s1 - _s0)
                sc.update(start=_s0, end=_s1, frame=_si == 0)
                scene_list.append(sc)
            off += d
            if kind == "tafsir":
                r = synthesize_line(
                    "قال المفسر: " + _trim_sent(tafs[a["numberInSurah"]], 130), "ar",
                                    workdir / "shr", name=f"t{i}",
                                    rate="-8%", pitch="-2Hz")
                wavs.append(r["wav"])
                for ch in captions.chunk_words(r["words"]):
                    events.append({"style": "Shr", "text": ch["text"],
                                   "start": off + ch["start"], "end": off + ch["end"]})
                off += r["duration"] + 0.12
                wavs.append(_silence(workdir / f"sp{i}.wav", 0.12))
        # الترجمة الإنجليزية بقت مدمجة سطر-بسطر داخل الكابتشن الهادئ
        ep_id = f"noor-{spec['id']}-{reciter.split('.')[-1]}"
    else:  # dua / hadith / adhkar / info من المخزون المحلي الصحيح
        stock = json.loads((settings.ROOT / "content" / "din_stock.json")
                           .read_text(encoding="utf-8"))
        lists = {"dua": ("duas", "دعاء"), "hadith": ("hadiths", "قال رسول الله ﷺ"),
                 "adhkar": ("adhkar", "مِن أذكار المسلم"),
                 "info": ("info", "معلومة تُضيء")}
        lname, label = lists[kind]
        items = stock[lname]
        item = items[(spec or {}).get("idx", reciter_idx) % len(items)]
        title = f"{label}: {item['text'][:40]}…"
        r = synthesize_line(item["text"], "ar", workdir / "vox", name="main",
                            rate="-8%", pitch="-2Hz")
        wavs.append(r["wav"])
        intro = synthesize_line(label, "ar", workdir / "vox", name="intro",
                                rate="-6%", pitch="-3Hz")
        wavs = [intro["wav"], _silence(workdir / "g0.wav", 0.15)] + wavs
        base_off = intro["duration"] + 0.15
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
        fayda = {
            "dua": "الدعاء عبادةٌ تُشرَح بها الصدور ويُرَدّ بها البلاء — "
                   "اجعله وَردَك اليوم.",
            "hadith": "علمٌ يُعمَل به ويُنشَر يضاعِف اللهُ به الأجر — "
                      "اعمل به وذكِّر غيرك.",
            "adhkar": "ذِكرُ الله تُطمئنّ به القلوب وتُحطّ به الخطايا — "
                      "لا يفارق لسانك.",
            "info": "التفكّر عبادة، والمعرفة نور — تدبَّر وشارك الخير.",
        }[kind]
        qs = ["mosque night lights", "kaaba mecca", "quran book candle",
              "praying hands sky", "dawn mountains peace"]
        n = 3
        for i in range(n):
            s = off * i / n
            e = off * (i + 1) / n
            sc = _scene_media(i, {"scenes": qs, "style": "cosmic"},
                              workdir, kind, e - s)
            sc.update(start=s, end=e, frame=True)
            scene_list.append(sc)
        ep_id = f"noor-{kind}-{reciter_idx % len(items)}"

    # جاذبية بصرية: لمعة ضوء تجوب كل مشهد
    for sc in scene_list:
        sc.setdefault("glint", True)

    # هوية البراند فوق كل المشاهد: لوجو + تدرّجات + إطار ذهبي للمشاهد
    INTRO = 1.4
    bl = scenes._brand_layer(workdir / "ov" / "brand.png")
    fr_ov = scenes.frame_overlay(workdir / "ov" / "frame.png")
    for sc in scene_list:
        sc["overlays"] = [bl] + (sc.get("overlays") or [])
        if sc.get("frame"):
            sc["overlays"].append(fr_ov)
    for ev in events:
        ev["start"] += INTRO
        ev["end"] += INTRO
    for sc in scene_list:
        sc["start"] += INTRO
        sc["end"] += INTRO
    wavs.insert(0, _silence(workdir / "intro.wav", INTRO))
    scene_list.insert(0, {"base": scenes.intro_base(workdir / "intro.png", title),
                          "overlays": [], "start": 0.0, "end": INTRO,
                          "nofade_in": True})
    off += INTRO

    # كرت الختام: فائدة مسموعة فوق خلفية البراند
    voice_fayda = (f"وقف ثانية يا صديقي… {fayda} "
                   "انشر الخير، لعلها تكون صدقة جارية ليك وليّا.")
    fr = synthesize_line(voice_fayda, "ar", workdir / "end", name="fayda",
                         rate="-6%", pitch="-1Hz")
    wavs.append(fr["wav"])
    end_dur = fr["duration"] + 1.0
    scene_list.append({**_end_card(workdir, fayda),
                       "start": off, "end": off + end_dur})
    total = off + end_dur

    # دمج الصوت + كتابة ASS + تجميع
    list_f = workdir / "vox.txt"
    list_f.write_text("".join(f"file '{p.as_posix()}'\n" for p in wavs),
                      encoding="utf-8")
    vox = workdir / "vox.wav"
    subprocess.run([ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", str(list_f),
                    "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(vox)],
                   capture_output=True, check=True)
    # معالجة الصوت — لكل محتوى ما يناسبه:
    processed = workdir / "vox_p.wav"
    if kind in ("quran", "tafsir", "qissa"):
        # التلاوة مقدسة: نقية 100% — إزالة تشويش + وضوح + جهارة بث
        # (بلا رفع تون، بلا إيكو، بلا همس — زي الاستوديو)
        pr = subprocess.run([ffmpeg(), "-y", "-i", str(vox), "-af",
                             "highpass=f=55,afftdn=nf=-28,"
                             "equalizer=f=3200:width_type=q:width=1.2:g=1.5,"
                             "loudnorm=I=-14:TP=-1.2:LRA=11",
                             "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le",
                             str(processed)], capture_output=True)
    else:
        # الأدعية/الأحاديث/المعلومات: هوية XDAW — دفء ووضوح بلا تشويه
        amb = workdir / "amb.wav"
        subprocess.run([ffmpeg(), "-y", "-f", "lavfi", "-i",
                        "anoisesrc=color=brown:amplitude=0.35",
                        "-af", "lowpass=f=300,volume=0.018", "-t", f"{total:.2f}",
                        "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le",
                        str(amb)], capture_output=True)
        pr = subprocess.run([ffmpeg(), "-y", "-i", str(vox), "-i", str(amb),
                             "-filter_complex",
                             "[0:a]afftdn=nf=-30,"
                             "equalizer=f=110:width_type=q:width=1:g=1,"
                             "equalizer=f=3400:width_type=q:width=1:g=1.5,"
                             "aecho=0.2:0.25:30:0.07[a];"
                             "[a][1:a]amix=inputs=2:normalize=0,"
                             "loudnorm=I=-14:TP=-1.2:LRA=11[out]",
                             "-map", "[out]", "-ar", "44100", "-ac", "2",
                             "-c:a", "pcm_s16le", str(processed)],
                            capture_output=True)
    if pr.returncode == 0 and processed.exists():
        vox = processed

    if kind in ("quran", "tafsir"):
        # ختام ساكن: شاشة سوداء + سطر واحد (لمسة المراجع)
        _blk = workdir / "black.mp4"
        subprocess.run([ffmpeg(), "-y", "-f", "lavfi", "-i",
                        "color=c=black:s=1080x1920:d=2.0:r=30",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                        "-pix_fmt", "yuv420p", str(_blk)], capture_output=True)
        if _blk.exists():
            wavs.append(_silence(workdir / "tail.wav", 2.0))
            scene_list.append({"video": _blk, "overlays": [], "grade": "calm",
                               "nofade_in": True, "start": off,
                               "end": off + 2.0, "frame": False})
            events.append({"style": "Calm", "start": off + 0.25,
                           "end": off + 2.0,
                           "text": "سلامٌ على قلبك 🤍\\N@XTreNDAW"})
            off += 2.0

    ass = workdir / "din.ass"
    lines = [ASS_HEADER]
    for ev in events:
        txt = ev["text"].replace("\n", " ")
        st = ev["style"]
        if st == "Ayah":
            # دخول نبضي ناعم + كاراوكي: الكلمة تتوهج دهبي لما تتقال
            fx = "{\\fad(320,240)\\fscx88\\fscy88\\t(80,560,\\fscx100\\fscy100)}"
            _ws = txt.split()
            if len(_ws) > 1:
                _dur = max(1, int((ev["end"] - ev["start"]) * 100))
                _tot = sum(max(1, len(w)) for w in _ws) or 1
                txt = " ".join(
                    "{\\kf%d}%s" % (max(8, _dur * max(1, len(w)) // _tot), w)
                    for w in _ws)
        elif st == "Calm":
            fx = "{\\fad(420,320)}"
        elif st == "Hdr":
            fx = "{\\fad(600,400)}"
        elif st == "WM":
            fx = "{\\fad(1200,800)}"
        else:
            fx = "{\\fad(450,350)}"
        lines.append(f"Dialogue: 0,{_t(ev['start'])},{_t(ev['end'])},{st},"
                     f",0,0,0,,{fx}{txt}\n")
    ass.write_text("".join(lines), encoding="utf-8")

    out = settings.OUT / f"{ep_id}.mp4"
    video.assemble({"wav": vox, "total_duration": total}, scene_list, ass,
                   out, workdir, music=None)
    cover = settings.OUT / f"{ep_id}-cover.png"
    brand.compose_cover({"id": ep_id, "title_ar": title,
                         "tags": "نور,قرآن,دعوة,XDAWNOVA"}, cover)
    return {"video": out, "cover": cover, "report": video.validate(out),
            "title": title, "id": ep_id, "reciter": reciter}


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
