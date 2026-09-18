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
    ("ar.alafasy", "مشاري راشد العفاسي", 128),
    ("ar.ahmedajamy", "أحمد بن علي العجمي", 64),
    ("ar.muhammadayyoub", "محمد أيوب", 128),
    ("ar.minshawimujawwad", "المنشاوي (مجوَّد)", 128),
    ("ar.abdullahmatroud", "عبدالله المطرود", 128),
    ("ar.salahbukhatir", "صلاح بوخاطر", 128),
    ("ar.ibrahimakhbar", "إبراهيم الأخضر", 128),
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
         scenes=["heart sky clouds", "mosque dome moonlight",
                 "night sky stars", "dawn light rays"]),
    dict(id="fatiha", surah=1, frm=1, to=7,
         scenes=["makkah clock tower night", "mosque night lights", "sunrise mountains clouds",
                 "quran book mosque", "sky clouds light", "desert dunes sunset",
                 "stars night sky"]),
    dict(id="kursi", surah=2, frm=255, to=255,
         scenes=["universe galaxy stars", "throne light rays sky",
                 "night sky milky way", "cosmos nebula"]),
    dict(id="amanah", surah=2, frm=285, to=286,
         scenes=["night sky stars calm", "mosque dome blue hour",
                 "clouds sunrise light", "candle flame dark room"]),
    dict(id="ulul", surah=3, frm=190, to=191,
         scenes=["galaxy stars deep space", "mountains night stars",
                 "ocean horizon dusk", "thinker silhouette dawn"]),
    dict(id="rahman", surah=55, frm=1, to=13,
         scenes=["roses garden dew", "sunrise sea golden", "palm trees oasis",
                 "flowing river forest", "stars night sky"]),
    dict(id="mulk", surah=67, frm=1, to=2,
         scenes=["night sky milky way", "birds flying sunset",
                 "mountains clouds aerial", "stars desert night"]),
    dict(id="duha", surah=93, frm=1, to=11,
         scenes=["morning sun rays window", "dawn city quiet",
                 "sunrise field light", "birds flying dawn"] ),
    dict(id="qadr", surah=97, frm=1, to=5,
         scenes=["night sky stars calm", "lantern glow night",
                 "moon clouds night", "candles warm dark"]),
    dict(id="zilzal", surah=99, frm=1, to=8,
         scenes=["desert sand wind", "earth mountains dawn",
                 "scales justice old", "tiny seed sprout"]),
    dict(id="takathur", surah=102, frm=1, to=8,
         scenes=["hourglass sand time", "old clock vintage",
                 "desert dunes wind", "sunset clouds fast"]),
    dict(id="asr", surah=103, frm=1, to=3,
         scenes=["sunset hourglass sky", "time clock stars",
                 "desert sunset", "wheat field sunset"]),
    dict(id="humazah", surah=104, frm=1, to=9,
         scenes=["gold coins old", "desert fire night",
                 "locked door ancient", "mountains dusk"]),
    dict(id="fil", surah=105, frm=1, to=5,
         scenes=["birds flock sky sunset", "desert stones ground",
                 "old mosque architecture", "desert dunes wind"]),
    dict(id="quraish", surah=106, frm=1, to=4,
         scenes=["desert dunes dawn", "old mosque architecture",
                 "ancient stone architecture", "desert night stars"]),
    dict(id="maun", surah=107, frm=1, to=7,
         scenes=["wheat field golden", "bread oven old",
                 "ancient empty street architecture", "water jug clay"]),
    dict(id="kawthar", surah=108, frm=1, to=3,
         scenes=["river paradise light", "fountain water sparkle",
                 "dawn light rays", "white doves sky"]),
    dict(id="nasr", surah=110, frm=1, to=3,
         scenes=["empty mosque courtyard moonlight", "sunrise mountains gold",
                 "desert dunes dusk", "sky light rays"]),
]

# قصص بآيات متتابعة — مشاهد سينمائية تاريخية
QISSA = [
    dict(id="naqat", title="ناقة صالح", surah=11, frm=64, to=67,
         scenes=["camel ancient desert village", "ancient stone village desert mountains",
                 "camel desert dunes", "desert dunes wind",
                 "desert mountains dawn"]),
    dict(id="feel", title="أصحاب الفيل", surah=105, frm=1, to=5,
         scenes=["elephant desert ancient", "desert dunes wind",
                 "ancient mosque dome", "birds flock sky sunset",
                 "desert stones ground"]),
    dict(id="yusuf-dream", title="رؤيا يوسف", surah=12, frm=4, to=6,
         scenes=["desert night stars", "sun moon stars sky", "desert night stars",
                 "desert path dawn"]),
    dict(id="kahf", title="أهل الكهف", surah=18, frm=9, to=12,
         scenes=["cave inside light rays", "ancient cave mountains",
                 "sleeping cave darkness", "sunlight cave entrance"]),
    dict(id="adam", title="آدم وتعلّم الأسماء", surah=2, frm=30, to=33,
         scenes=["garden eden trees light", "angels light sky", "ancient earth dawn landscape",
                 "stars cosmos creation"]),
    dict(id="nuh", title="سفينة نوح", surah=11, frm=37, to=41,
         scenes=["ancient wooden ship flood", "heavy rain clouds sea", "mountain waves storm",
                 "dove bird sky calm"]),
    dict(id="ibrahim-nar", title="نار إبراهيم بردًا", surah=21, frm=68, to=70,
         scenes=["huge fire flames night", "firelight ancient stone", "green garden from ashes",
                 "ancient babylon ruins"]),
    dict(id="musa", title="عصا موسى", surah=20, frm=17, to=21,
         scenes=["ancient egypt nile river", "wooden staff hand desert", "snake sand ancient",
                 "ancient stone palace ruins"]),
    dict(id="yunus", title="يونس في بطن الحوت", surah=37, frm=139, to=144,
         scenes=["whale deep sea dark", "ocean waves moonlight", "glowing plankton ocean deep",
                 "pumpkin plant shore"]),
    dict(id="sulayman", title="سليمان والنملة", surah=27, frm=17, to=19,
         scenes=["desert wind dunes", "tiny ant sand closeup", "ancient empty throne room",
                 "birds flock sky"]),
    dict(id="zakariya", title="دعاء زكريا", surah=19, frm=2, to=6,
         scenes=["mihrab mosque interior", "candle light ancient mosque", "quran book candle",
                 "dawn light window"]),
    dict(id="maryam", title="مريم ونخلة الرطب", surah=19, frm=22, to=26,
         scenes=["palm tree desert oasis", "dates palm closeup", "stream water desert",
                 "palm shadow warm light"]),
    dict(id="ayyub", title="صبر أيوب", surah=38, frm=41, to=43,
         scenes=["ancient stone room candlelight", "spring water gushing rock", "desert oasis sunset",
                 "green field after rain"]),
    dict(id="dhaby", title="فداء إسماعيل", surah=37, frm=102, to=107,
         scenes=["mountain path dawn", "ram mountain dawn", "ancient desert ruins",
                 "sky clouds mercy light"]),
    dict(id="hijra", title="هجرة النبي ﷺ والغار", surah=9, frm=40, to=40,
         scenes=["cave entrance spider web", "cave entrance light", "desert night journey camels",
                 "dawn horizon hijra"]),
    dict(id="badr", title="نصر بدر", surah=3, frm=123, to=125,
         scenes=["desert dust sunrise", "angels light sky riders", "desert camp night fires",
                 "victory sunrise desert"]),
    {"id": "ukhdud", "title": "أصحاب الأخدود", "surah": 85, "frm": 4, "to": 9, "scenes": ["ancient fire trench desert night", "mountain fortress dawn", "ancient empty palace throne", "fire burning pit desert", "stars night sky hope"]},
    {"id": "talut", "title": "طالوت وجالوت", "surah": 2, "frm": 246, "to": 251, "scenes": ["ancient bridge over river", "shepherd staff on stone", "ancient stone battlefield ruins", "ancient battle desert dust", "sunrise over desert ruins"]},
    {"id": "baqara-q", "title": "قصة البقرة", "surah": 2, "frm": 67, "to": 73, "scenes": ["cow grazing green field", "ancient israelite village", "ancient stone village", "golden light miracle", "ancient scroll torah"]},
    {"id": "khidr", "title": "موسى والخضر", "surah": 18, "frm": 65, "to": 75, "scenes": ["empty sea shore dawn", "wooden boat old sea", "ancient wall rebuilding village", "sea waves journey mystery", "old stone library light"]},
    {"id": "jannatayn", "title": "صاحب الجنتين", "surah": 18, "frm": 32, "to": 43, "scenes": ["lush garden grape vines", "two beautiful gardens fountain", "storm destroying garden night", "empty palace ruins", "ruins garden regret dawn"]},
    {"id": "uzair", "title": "الذي نام مئة عام", "surah": 2, "frm": 259, "to": 259, "scenes": ["ancient ruined city walls", "donkey standing desert road", "bones rising life miracle", "sunrise sunset time lapse", "rebuilt ancient town light"]},
    {"id": "abnay-adam", "title": "ابنا آدم", "surah": 5, "frm": 27, "to": 31, "scenes": ["empty ancient field", "raven digging earth", "green hills ancient land", "sacrifice offering fire sky", "empty desert sunset"]},
    {"id": "luqman", "title": "وصايا لقمان", "surah": 31, "frm": 12, "to": 19, "scenes": ["ancient home window light", "ancient simple home", "mountains steadfast rock", "bird flying sky small", "path humble walk sunset"]},
    {"id": "namla", "title": "سليمان والنملة", "surah": 27, "frm": 17, "to": 19, "scenes": ["ant on ground close up", "empty valley dust", "ancient palace sky light", "ants colony moving", "desert valley sunlight"]},
    {"id": "hudhud", "title": "الهدهد وملكة سبأ", "surah": 27, "frm": 20, "to": 28, "scenes": ["hoopoe bird flying", "ancient empty throne palace", "letter scroll royal seal", "sunrise ancient temple", "majestic kingdom gold"]},
    {"id": "sabt", "title": "أصحاب السبت", "surah": 7, "frm": 163, "to": 166, "scenes": ["empty coastal village", "fish jumping water sabbath", "ancient seaside town walls", "storm sea punishment waves", "quiet empty village lesson"]},
    {"id": "firawn", "title": "غرق فرعون", "surah": 10, "frm": 90, "to": 92, "scenes": ["sea parting walls water", "ancient egypt ruins desert", "storm waves sea", "pyramids desert ancient egypt", "calm sea after storm dawn"]},
    {"id": "abrar", "title": "الأبرار في الجنة", "surah": 76, "frm": 8, "to": 12, "scenes": ["bread and dates table", "bread basket warm light", "water cup soft light", "paradise garden rivers light", "silk garments reward glow"]},
    {"id": "qarun", "title": "قارون وكنوزه", "surah": 28, "frm": 76, "to": 82, "scenes": ["treasure gold chests ancient", "treasure palace empty", "earth swallowing palace ruin", "gold coins shining dark", "desert emptiness lesson dawn"]},
    dict(id="yunus", title="يونس في بطن الحوت", surah=37, frm=139, to=144,
         scenes=["stormy sea waves night", "whale ocean deep",
                 "dark sea night stars", "desert shore dawn"]),
    dict(id="musa-staff", title="عصا موسى", surah=27, frm=10, to=12,
         scenes=["desert night fire", "staff light glow",
                 "mountain sinai dawn", "serpent rock desert"]),
    dict(id="maryam-mihrab", title="محراب مريم", surah=3, frm=37, to=37,
         scenes=["mihrab mosque light", "fruits summer winter",
                 "ancient room pray light", "date palm oasis"]),
    dict(id="ibrahim-birds", title="طيور إبراهيم", surah=2, frm=260, to=260,
         scenes=["birds flock mountains", "four birds sky",
                 "ancient desert ruins", "birds flying dawn"]),
]

TAFASEER = [
    dict(id="t-asr", surah=103, frm=1, to=3,
         scenes=["sunset hourglass sky", "time clock stars", "desert sunset",
                 "wheat field sunset"]),
    dict(id="t-thikr", surah=13, frm=28, to=28,
         scenes=["heart light chest", "calm lake sunrise", "prayer beads mosque",
                 "sky clouds peace"]),
    dict(id="t-yusr", surah=94, frm=5, to=8,
         scenes=["dark cloud silver lining", "dawn after night mountains",
                 "path light darkness", "sunrise hope sky"]),
    dict(id="t-thara", surah=99, frm=7, to=8,
         scenes=["tiny seed sprout", "mountain small big", "scales justice sky",
                 "desert atom sand"]),
    dict(id="t-kawthar", surah=108, frm=1, to=3,
         scenes=["river paradise light", "fountain sparkle water",
                 "dawn light rays", "white doves sky"]),
    dict(id="t-nasr", surah=110, frm=1, to=3,
         scenes=["empty mosque courtyard moonlight", "sunrise mountains gold",
                 "desert dunes dusk", "sky light rays"]),
    dict(id="t-maun", surah=107, frm=1, to=7,
         scenes=["wheat field golden", "bread oven old",
                 "ancient empty street architecture", "water jug clay"]),
    dict(id="t-fil", surah=105, frm=1, to=5,
         scenes=["birds flock sky sunset", "desert stones ground",
                 "old mosque architecture", "desert dunes wind"]),
    dict(id="t-humazah", surah=104, frm=1, to=9,
         scenes=["gold coins old", "desert fire night",
                 "locked door ancient", "mountains dusk"]),
    dict(id="t-asr2", surah=103, frm=1, to=3,
         scenes=["sunset hourglass sky", "time clock stars",
                 "desert sunset", "wheat field sunset"]),
    dict(id="t-qadr", surah=97, frm=1, to=5,
         scenes=["night sky stars calm", "lantern glow night",
                 "moon clouds night", "candles warm dark"]),
    dict(id="t-duha", surah=93, frm=1, to=11,
         scenes=["morning sun rays window", "dawn city quiet",
                 "sunrise field light", "warm sunlight window"]),
    dict(id="t-layl", surah=92, frm=1, to=21,
         scenes=["night city lights", "moon clouds night",
                 "lantern street old", "stars desert night"]),
    dict(id="t-shams", surah=91, frm=1, to=15,
         scenes=["sunrise desert bright", "noon sun shadows",
                 "ancient city sun", "tribe ruins desert"]),
]

# بنك التفسير الحي — إيچنت المكتبة بيضيف فيه كل دورة (مضاف فقط)
_tbank = settings.ROOT / "content" / "tafsir_bank.json"
if _tbank.exists():
    try:
        import json as _tj
        TAFASEER = TAFASEER + _tj.loads(_tbank.read_text(encoding="utf-8"))
    except Exception:
        pass

# أسئلة تدبُّر منتقاة بعناية — خطّاف قالب التفسير (بصمة المراجع الهادئة)
HOOKS = {
    "t-asr": "لماذا أقسم الله بالوقت في ثلاث آيات فقط؟",
    "t-thikr": "لماذا تطمئن القلوب بذكر الله تحديدًا؟",
    "t-yusr": "لماذا جاء اليُسْر مع العسر لا بعده؟",
    "t-thara": "لماذا خُتمت السورة بمثقال الذرّة؟",
}

# الأنواع الجريئة تحتفظ بهوية النيون الكاملة؛ الهادئة تنزع الإطار والشبكة
NEON_KINDS = {"hadith", "info", "qissa"}

# الرقية الشرعية — أعلى طلب في المحتوى الإسلامي (سلسلة تلاوة)
RUQYAH = [
    dict(id="ruq-fatiha", surah=1, frm=1, to=7),
    dict(id="ruq-kursi", surah=2, frm=255, to=255),
    dict(id="ruq-amanar", surah=2, frm=285, to=286),
    dict(id="ruq-ilah", surah=2, frm=163, to=164),
    dict(id="ruq-shifa", surah=17, frm=82, to=82),
    dict(id="ruq-hashr", surah=59, frm=21, to=24),
    dict(id="ruq-ikhlas", surah=112, frm=1, to=4),
    dict(id="ruq-falaq", surah=113, frm=1, to=5),
    dict(id="ruq-nas", surah=114, frm=1, to=6),
    dict(id="ruq-yunus", surah=10, frm=57, to=57),
]

# التحصين — آيات الحفظ الصباحية والمسائية (سلسلة تلاوة)
TAHSEEN = [
    dict(id="tah-kursi", surah=2, frm=255, to=255),
    dict(id="tah-amanar", surah=2, frm=285, to=286),
    dict(id="tah-saffat", surah=37, frm=1, to=10),
    dict(id="tah-isra", surah=17, frm=45, to=46),
    dict(id="tah-ikhlas", surah=112, frm=1, to=4),
    dict(id="tah-falaq", surah=113, frm=1, to=5),
    dict(id="tah-nas", surah=114, frm=1, to=6),
    dict(id="tah-taha", surah=20, frm=111, to=112),
]

# جزء عمّ: كل سورة سلسلة تلاوة مرقّمة (التقليم التلقائي يحافظ على ≤90ث)
JUZ = [dict(id=f"juz{s}", surah=s, frm=1, to=999) for s in range(78, 115)]

# سلاسل واعية مرقّمة: المصنع عارف إنه بينشر الجزء (س/ص) من سلسلة كاملة
SERIES_KINDS = {"asma", "seerah", "kawn", "akhira", "akhlaq", "qissa",
                "tafsir", "juz", "nawawi", "ruqyah", "hisn", "tahseen",
                "qudsi"}
SERIES_LABEL = {"asma": "سلسلة الأسماء الحسنى", "seerah": "سلسلة السيرة النبوية",
                "kawn": "سلسلة آيات في الكون", "akhira": "سلسلة الاستعداد للآخرة",
                "akhlaq": "سلسلة مكارم الأخلاق", "qissa": "سلسلة قصص الأنبياء",
                "tafsir": "سلسلة التدبُّر", "juz": "سلسلة جزء عمّ",
                "nawawi": "سلسلة الأربعين النووية",
                "qudsi": "سلسلة الأحاديث القدسية",
                "ruqyah": "سلسلة الرقية الشرعية",
                "hisn": "سلسلة حصن المسلم",
                "tahseen": "سلسلة التحصين"}

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Ayah,Amiri,110,&H0039C8FF,&H00F2F2F2,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,4,2,5,70,70,0,1
Style: Trj,Tajawal,46,&H00B6FFB6,&H000000FF,&H00000000,&H8A000000,0,0,0,0,100,100,0,0,1,3,1,2,60,60,150,1
Style: Shr,Amiri,66,&H00D6C9A6,&H000000FF,&H00000000,&H8A000000,-1,0,0,0,100,100,0,0,1,3,1,2,70,70,220,1
Style: Calm,Amiri,60,&H00FFFFFF,&H00000000,&H00101010,&H8A000000,0,0,0,0,100,100,0,0,1,2,2,2,70,70,300,1
Style: CalmL,Amiri,60,&H00FFFFFF,&H00000000,&H00101010,&H8A000000,0,0,0,0,100,100,0,0,1,2,2,1,90,70,300,1
Style: Hook,Amiri,47,&H0086C8F4,&H00000000,&H00101010,&H8A000000,0,0,0,0,100,100,0,0,1,2,2,8,70,70,820,1
Style: Hdr,Amiri Quran,60,&H009AD8FF,&H000000FF,&H00000000,&H8A000000,-1,0,0,0,100,100,0,0,1,3,2,8,60,60,90,1
Style: Big,Tajawal,112,&H00FFFFFF,&H000000FF,&H00141414,&H96000000,-1,0,0,0,100,100,0,0,1,5,3,2,60,60,260,1

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
    import re as _qre

    q = spec["scenes"][i % len(spec["scenes"])]
    print(f"[din] scene {i} query-start", flush=True)
    # حارس أخير: أي كلمة قد تستدعي بشرًا تتحول قبل وصولها لأي مزود.
    # ده يضمن الصفر حتى لو أضاف إيچنت المكتبة استعلامًا بشريًا مستقبلًا.
    _people_words = {
        "people", "person", "man", "woman", "child", "family", "father",
        "son", "mother", "baby", "hands", "pilgrim", "pilgrims", "crowd",
        "soldier", "soldiers", "army", "king", "queen", "pharaoh", "prophet",
        "orphan", "orphans", "captive", "scholar", "caravan", "worship", "praying",
        "prayer", "helping", "friends", "market", "fishermen",
    }
    if _people_words.intersection(_qre.findall(r"[a-z]+", q.lower())):
        q = "empty nature landscape architecture light"
    # تنويع حقيقي: كل مشهد بزاوية/إضاءة مختلفة — بلا تكرار بين الحلقات
    q = f"{q}, {['cinematic wide shot', 'golden hour light', 'aerial view', 'close-up detail', 'dramatic side light'][i % 5]}"
    # قيد صفري ثابت على مستوى الاستعلام: لا بشر/وجوه/حشود حتى مع Pexels.
    # الطبيعة والمعمار هما البديل، وليس لقطة أشخاص يتم اكتشافها بعد الشحن.
    q = f"{q}, empty scene, no people, no faces, no crowd"
    scdir = workdir / f"sc{i:02d}"
    if spec.get("grade") == "calm":
        q = f"{q}, nature landscape"
    _src = "auto"
    clip = footage.fetch_clip(q, max(1.0, seconds), scdir, f"{seed}:{i}",
                              source=_src)
    print(f"[din] scene {i} clip={'yes' if clip else 'no'}", flush=True)
    if not clip:
        # محاولة ثانية باستعلام أبسط — اللقطة الحيّة أولى من الصورة
        _q2 = f"{' '.join(q.split(',')[0].split()[:3])}, empty landscape, no people"
        if _q2 and _q2 != q:
            clip = footage.fetch_clip(_q2, max(1.0, seconds), scdir,
                                      f"{seed}:{i}r", source=_src)
    if clip:
        return {"video": clip, "overlays": [],
                "grade": spec.get("grade", "soft")}
    base = scdir / "base.png"
    print(f"[din] scene {i} fallback-start", flush=True)
    if spec.get("style") == "cinema":
        prompt = (f"{q}, ancient middle-east historical scene, cinematic film still, "
                  "realistic, dramatic natural light, 9:16 vertical, no text")
        if not scenes.fetch_ai_visual(prompt, base, hash(seed) % 10_000_000):
            (scenes.fetch_real_visual(q, base)
             or scenes.fetch_library_visual(q, base)
             or scenes.render_ambient(base, spec.get("rgb", "#e8b64c"), seed))
    else:
        if not (scenes.fetch_real_visual(q, base) or scenes.fetch_library_visual(q, base)):
            scenes.fetch_ai_visual(
                f"{q}, majestic cosmic cinematic scene, 9:16 vertical, no text",
                base, hash(seed) % 10_000_000) or scenes.render_ambient(
                base, spec.get("rgb", "#e8b64c"), seed)
    return {"base": base, "overlays": [], "grade": "soft"}


def _end_card(workdir: Path, fayda: str, quiet: bool = False) -> dict:
    """كرت الختام: نيون البراند للأنواع الجريئة، وسكون أسود للأنواع الهادئة."""
    from . import textrender

    d = workdir / "end"
    ov = [] if quiet else [scenes._brand_layer(d / "brand.png")]
    ov.append(scenes.frame_overlay(d / "frame.png", color="#ffd166"))
    ov.append(textrender.text_image(
        "﴿ فَائِدَةٌ وَنُور ﴾", d / "h.png", font_size=64, y_ratio=0.21,
        fill="#ffd9a0" if not quiet else "#e8e2d5", stroke_width=4,
        font_path=settings.FONTS / "AmiriQuran-Regular.ttf"))
    ov.append(textrender.text_image(fayda, d / "f.png", font_size=54,
                                    y_ratio=0.50, fill="#f7ecd7",
                                    stroke_width=4, max_width_ratio=0.76))
    ov.append(textrender.text_image("انشر الخير — XDAW NOVA", d / "b.png",
                                    font_size=34, y_ratio=0.90,
                                    fill="#ffd166" if not quiet else "#9a938a",
                                    stroke_width=3))
    return {"base": scenes.render_bg(d / "base.png",
                                     "quiet" if quiet else "outro",
                                     "noor-end"),
            "overlays": ov}


def produce_din(kind: str, workdir: Path, reciter_idx: int = 0,
                spec: dict | None = None,
                tts_recite: bool = False) -> dict:
    """ينتج حلقة نور ويعيد {video, cover, report, title, id}."""
    # تنويع الأصوات كل ساعة — المخزون النصي ×4 بلا حدود
    from . import tts as _tt
    import time as _tm
    _tt.VOICE_OVERRIDE_AR = [
        "ar-EG-SalmaNeural", "ar-SA-ZariyahNeural",
        "ar-LB-LaylaNeural", "ar-AE-FatimaNeural"][int(_tm.time() / 3600) % 4]
    workdir.mkdir(parents=True, exist_ok=True)
    chip = ""
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

    if kind in ("quran", "qissa", "tafsir", "juz", "ruqyah", "tahseen"):
        pool = {"quran": QURAN, "qissa": QISSA, "tafsir": TAFASEER,
                "juz": JUZ, "ruqyah": RUQYAH, "tahseen": TAHSEEN}[kind]
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
        if kind == "quran":
            title = ["آيةٌ تُريح القلب 🤍 ", "استمع بقلبك… 🎧 ",
                     "راحةٌ لصدرِك 🤍 ", "دقيقة نور 🌙 ",
                     "هديّة لقلبك اليوم 🤍 "][spec["surah"] % 5] + title
        if kind == "tahseen":
            _ti = next((j for j, w in enumerate(TAHSEEN)
                        if w["surah"] == spec["surah"]
                        and w["frm"] == spec["frm"]), 0)
            title = (f"{SERIES_LABEL['tahseen']} ({_ti + 1}/{len(TAHSEEN)}): "
                     f"{title}")
        if kind == "ruqyah":
            _ri = next((j for j, w in enumerate(RUQYAH)
                        if w["surah"] == spec["surah"]
                        and w["frm"] == spec["frm"]), 0)
            title = (f"{SERIES_LABEL['ruqyah']} ({_ri + 1}/{len(RUQYAH)}): "
                     f"{title}")
        if kind == "juz":
            from . import planner as _pl

            _jw = [w for w in _pl.quran_windows() if w["surah"] >= 78]
            _ji = next((j for j, w in enumerate(_jw)
                        if w["surah"] == spec["surah"]
                        and w["frm"] == spec["frm"]), 0)
            title = f"{SERIES_LABEL['juz']} ({_ji + 1}/{len(_jw)}): {title}"
        if kind == "tafsir":
            _ti = next((j for j, w in enumerate(TAFASEER)
                        if w["id"] == spec["id"]), 0)
            title = (f"{SERIES_LABEL['tafsir']} ({_ti + 1}/{len(TAFASEER)}): "
                     f"{title}")
        t = _get_json(f"{APIQ}/surah/{spec['surah']}/ar.muyassar")["ayahs"]
        tafs = {a["numberInSurah"]: a["text"] for a in t}
        fayda = _trim_sent(tafs.get(spec["frm"], ""), 190)
        fayda = f"نزلت {rev}. {fayda}"
        # لمسة المراجع الناجحة: مود بصري واحد موحّد للفيديو كله
        if kind in ("quran", "tafsir", "juz", "ruqyah", "tahseen"):
            import hashlib as _h
            # لكل نوع شخصيته البصرية — القناة بتطوّر وبتنوِّع قوالبها
            if kind == "tafsir":
                _moods = [
                    ["candle flame close up", "warm candlelight dark room",
                     "old quran book pages", "vintage room warm light"],
                    ["rain on window night", "rainy street lights reflection",
                     "window rain drops dark", "night rain city glow"],
                    ["old stone alley lantern", "antique lantern glow",
                     "flowers by window dusk", "cozy interior candle light"],
                ]
            else:
                _moods = [
                    ["sunset over calm sea", "ocean horizon golden light",
                     "sun setting into water", "slow sea waves golden hour"],
                    ["mosque silhouette dusk", "minarets sunset sky",
                     "mosque dome blue hour", "masjid lights night"],
                    ["starry night sky", "milky way over desert",
                     "stars night clouds", "moon night sky calm"],
                    ["mosque courtyard empty", "grand mosque exterior night",
                     "grand mosque lights night", "mosque silhouette dusk"],
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
        if kind == "tafsir":
            # خطّاف تدبُّري يفتح الحلقة بسؤال — بصمة قالب التفسير
            events.append({"style": "Hook",
                           "text": HOOKS.get(spec["id"],
                                             f"وقفة تدبُّر في {sname} 🤍"),
                           "start": 1.4, "end": 4.8})

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
                if i == 0 and not tts_recite:
                    # الخطاف الذهبي: الآية الأولى كاملة بالكاراوكي الدهبي كلمة-كلمة — توقيع القناة
                    events.append({"style": "Ayah",
                                   "text": f"{a['text']} ﴿{_ar_num(a['numberInSurah'])}﴾",
                                   "start": off, "end": off + d})
                else:
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
                            "style": "CalmL" if kind == "tafsir" else "Calm",
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
                # مشاهد حية تغطي شرح المفسر — بدونها الفيديو كان بيتقصّ نص الجملة
                sc = _scene_media(i + 10, spec, workdir, spec["id"],
                                  r["duration"])
                sc.update(start=off, end=off + r["duration"], frame=False)
                scene_list.append(sc)
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
                 "info": ("info", "معلومة تُضيء"),
                 "seerah": ("seerah", "مِن السيرة النبوية"),
                 "asma": ("asma", "مِن الأسماء الحسنى"),
                 "kawn": ("kawn", "آية في الكون"),
                 "akhira": ("akhira", "استعد للقاء"),
                 "akhlaq": ("akhlaq", "خُلق حسن"),
                 "nawawi": ("nawawi", "قال رسول الله ﷺ"),
                 "hisn": ("hisn", "حصن المسلم"),
                 "qudsi": ("qudsi", "قال الله تعالى")}
        lname, label = lists[kind]
        items = stock[lname]
        _idx = (spec or {}).get("idx", reciter_idx) % len(items)
        item = items[_idx]
        if kind in SERIES_LABEL:
            title = (f"{SERIES_LABEL[kind]} ({_idx + 1}/{len(items)}): "
                     f"{item['text'][:34]}…")
        else:
            title = f"{label}: {item['text'][:40]}…"
        r = synthesize_line(item["text"], "ar", workdir / "vox", name="main",
                            rate="-8%", pitch="-2Hz")
        wavs.append(r["wav"])
        intro = synthesize_line(label, "ar", workdir / "vox", name="intro",
                                rate="-6%", pitch="-3Hz")
        wavs = [intro["wav"], _silence(workdir / "g0.wav", 0.05)] + wavs
        base_off = intro["duration"] + 0.05
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
        chip = label
        # 🌍 دبلجة للعالم: نفس النص بإنجليزي واضح + كابتشن كلمات
        _en = (item.get("en") or "").strip()
        if _en:
            wavs.append(_silence(workdir / "g_en.wav", 0.22))
            off += 0.22
            er = synthesize_line(_en, "en", workdir / "vox", name="endub",
                                 rate="-4%")
            wavs.append(er["wav"])
            for ch in captions.chunk_words(er["words"], size=4):
                events.append({"style": "Shr", "text": ch["text"],
                               "start": off + ch["start"],
                               "end": off + ch["end"]})
            events.append({"style": "Trj",
                           "text": "English 🌍 — XDAW NOVA",
                           "start": off, "end": off + er["duration"]})
            off += er["duration"]
        fayda = {
            "dua": "الدعاء عبادةٌ تُشرَح بها الصدور ويُرَدّ بها البلاء — "
                   "اجعله وَردَك اليوم.",
            "hadith": "علمٌ يُعمَل به ويُنشَر يضاعِف اللهُ به الأجر — "
                      "اعمل به وذكِّر غيرك.",
            "adhkar": "ذِكرُ الله تُطمئنّ به القلوب وتُحطّ به الخطايا — "
                      "لا يفارق لسانك.",
            "info": "التفكّر عبادة، والمعرفة نور — تدبَّر وشارك الخير.",
            "seerah": "في رسول الله أسوة حسنة لمن كان يرجو الله واليوم الآخر.",
            "asma": "لله الأسماء الحسنى فادعوه بها — وذوقوا ضياءها.",
            "kawn": "في كل مخلوق آية تدل على الخالق — فتفكَّروا.",
            "akhira": "من جعل الآخرة نصب عينيه جمع الله شمله وجعل غناه في قلبه.",
            "akhlaq": "أثقل ما في الميزان خُلق حسن — فأحسنوا الخلق.",
            "nawawi": "من حفظ الأربعين النوويّة حاز جوامع الكلم — "
                      "احفظها وعلّمها.",
            "hisn": "من لزم ذكر الله حُفظ — «ألا بذكر الله تطمئن القلوب».",
            "qudsi": "كلام ربك لك مباشرة — اقرأه بقلبك وادعُ به.",
            "ruqyah": "الرقية الشرعية حصن المؤمن — اقرأها على نفسك "
                      "وأهلك كل يوم.",
            "tahseen": "من قالها صباحًا ومساءً حُفظ بإذن الله — "
                       "«وهو يحفظهم من أمر الله».",
        }.get(kind, "نورٌ يُتدبَّر وعملٌ يُخلَص — شارِك الخير.")
        # شخصية بصرية مميزة لكل نوع من المخزون — مش قالب واحد للجميع
        qs = {
            "dua": ["sunset over calm sea", "doves flying sky",
                    "soft sunrise clouds", "olive branch morning light"],
            "adhkar": ["starry night sky", "moon night clouds",
                       "milky way over desert", "night sky stars calm"],
            "hadith": ["old lantern warm light", "vintage book candle",
                       "antique quran pages", "warm candlelight dark room"],
            "info": ["aerial desert dunes", "underwater sun rays",
                     "forest fog sunrise", "mountains clouds aerial"],
            "seerah": ["old mosque architecture", "desert dunes dawn",
                       "ancient city stone walls", "desert migration path"],
            "asma": ["light rays sky clouds", "golden sunrise glory",
                     "stars night vast sky", "sunrise mountains light"],
            "kawn": ["galaxy spiral space", "ocean deep waves aerial",
                     "bees flowers macro", "mountains aerial clouds"],
            "akhira": ["scales justice ancient", "bridge light darkness",
                       "paradise garden rivers", "desert dawn vast"],
            "akhlaq": ["olive branch warm light", "bread table warm light",
                       "birds flying sky", "warm sunlight window"],
            "nawawi": ["old quran book candle", "lantern warm light night",
                       "vintage room warm light", "old books candle desk"],
            "hisn": ["morning sunrise sky", "olive tree light",
                     "calm sea horizon", "night stars sky"],
            "qudsi": ["golden light rays clouds", "night sky deep stars",
                      "sunrise over mountains", "calm ocean light"],
            "ruqyah": ["soft light mosque", "golden dome light",
                       "olive branch light", "calm sky clouds"],
            "tahseen": ["sunrise golden light", "fortress walls light",
                        "calm desert dawn", "stars night sky"],
        }.get(kind, ["mosque night lights", "makkah clock tower night", "quran book candle",
                     "open quran sky light", "dawn mountains peace"])
        _gr = ["calm", "soft", "calm", "soft", "calm"][_idx % 5]
        from . import multiverse as _mv0
        spec = dict(spec or {})
        spec.setdefault("seed", f"noor-{kind}-{_idx}:{item['text'][:24]}")
        spec["rgb"] = _mv0.style_dna(spec["seed"])["rgb"]
        import hashlib as _hl
        _rhy_size = [3, 2, 4][int(_hl.sha256(
            f"{kind}:{title[:24]}".encode()).hexdigest(), 16) % 3]
        # مونتاج يطارد الكلام: قصّة حية لكل عبارة منطوقة — الصور تصف الصوت
        segs = [(base_off + ch["start"] - 0.15, base_off + ch["end"] + 0.2)
                for ch in captions.chunk_words(r["words"], size=_rhy_size)]
        merged: list[tuple[float, float]] = []
        for s, e in segs:
            if merged and e - s < 1.1:
                merged[-1] = (merged[-1][0], e)
            else:
                merged.append((s, e))
        # ثلاث لقطات حيّة كفاية لشد الانتباه، وتمنع xfade عالي الدقة من
        # استهلاك ساعة كاملة؛ كل لقطة مختلفة بالبصمة والمصدر والانتقال.
        merged = merged[:3]
        # آخر مشهد يبتلع الذيل/Dبلجة دائمًا — التغطية كاملة مهما طال النص
        if merged and off > merged[-1][1]:
            merged[-1] = (merged[-1][0], off)
        if not merged:
            merged = [(0.0, off)]
        print(f"[din] stock scenes={len(merged)}", flush=True)
        for i, (s, e) in enumerate(merged):
            sc = _scene_media(i, {"scenes": qs, "grade": _gr},
                              workdir, f"{kind}-{_idx}", max(1.0, e - s))
            sc.update(start=s, end=e, frame=True)
            scene_list.append(sc)
        print("[din] visual-scenes-done", flush=True)
        ep_id = f"noor-{kind}-{reciter_idx % len(items)}"

    # محرك الأنماط (Multiverse): DNA بصري فريد لكل حلقة —
    # لوحة لون × تدرّج × حركة × جسيمات بعمقين × انتقال × حبيبة
    from . import multiverse as _mvx
    # بذرة الحرية: الحلقة تختار روحها — ويمكن للمخرج اختيار بذرة يدويًا
    _seed = (spec or {}).get("seed") or f"{ep_id}:{title[:24]}"
    dna = _mvx.style_dna(_seed)
    # ضمانة الاختلاف الحقيقية: لا نكرر البصمة الكاملة في آخر 12 حلقة،
    # ولا نعيد نفس التخطيط أو افتتاحية الـ7 هياكل خلال آخر حلقتين.
    # كده التنوع محفوظ حتى لو المخطّط رجّع نوعًا واحدًا عدة ساعات.
    try:
        import json as _jl
        from . import intro_lab as _il0

        _histf = settings.STATE / "dna_history.json"
        _hist = []
        if _histf.exists():
            _raw = _jl.loads(_histf.read_text(encoding="utf-8"))
            if isinstance(_raw, list):
                _hist = [x.get("sig", x) if isinstance(x, dict) else x
                         for x in _raw]
        # ترقية ذاكرة الإصدار السابق ذات العنصر الواحد بدون كسرها.
        if not _hist:
            _lastf = settings.STATE / "dna_last.json"
            if _lastf.exists():
                _last = _jl.loads(_lastf.read_text(encoding="utf-8"))
                if isinstance(_last, dict) and _last.get("sig"):
                    _hist = [_last["sig"]]

        def _visual_sig(_d, _s):
            _ih = _il0._h(_s, "intro")
            return [
                _d["palette"], _d["layout"], _d["grade"], _d["motion"],
                _d["particles"], _d["rise"], _d["transition"], _d["grain"],
                _d["vig"], _d["p_speed"], _d["live_zoom"], _d["xtrans"],
                _d["depth"], _d["typo"], _d["ramp"], _d["intro"],
                _d["rhythm"], _ih % 7, (_ih >> 3) & 1,
            ]

        _recent = _hist[-12:]
        _picked = None
        # 128 بذرة بديلة تكفي لتفادي أي تشابه عمليًا، مع الحفاظ على حتمية الحلقة.
        for _salt in range(128):
            _try_seed = _seed if _salt == 0 else f"{_seed}:visual-v{_salt}"
            _try_dna = _mvx.style_dna(_try_seed)
            _try_sig = _visual_sig(_try_dna, _try_seed)
            _layouts = [x[1] for x in _recent[-2:] if isinstance(x, list) and len(x) > 17]
            _arches = [x[17] for x in _recent[-2:] if isinstance(x, list) and len(x) > 17]
            _strict = (_try_sig not in _recent and
                       (not _recent or _try_sig[:3] != _recent[-1][:3]) and
                       _try_sig[1] not in _layouts and _try_sig[17] not in _arches)
            _loose = (_try_sig not in _recent and
                      (not _recent or _try_sig != _recent[-1]))
            if _strict or (_salt >= 64 and _loose):
                _seed, dna, _sig = _try_seed, _try_dna, _try_sig
                _picked = True
                break
        if not _picked:
            _sig = _visual_sig(dna, _seed)
        dna["_sig"] = _sig
        dna["_history_file"] = str(_histf)
        dna["_history"] = _hist
    except Exception:
        # اختلاف الألوان الأساسي يظل فعالًا حتى لو كانت ذاكرة الحالة تالفة.
        dna["_sig"] = [dna.get("palette"), dna.get("layout"), dna.get("grade"),
                        dna.get("xtrans")]
    # جسيمات بمعنى: الجو البصري بيتبع معنى الكلام (مطر/نور…)
    import re as _re_sem
    _alltx = "".join(ev.get("text", "") for ev in events)
    _plain_sem = _re_sem.sub(r"[\u064B-\u0652\u0670\u0640]", "", _alltx)
    if any(k in _plain_sem for k in ("مطر", "غيث", "ماء", "نهر", "بحر", "سيل")):
        dna = {**dna, "particles": 3, "rise": False}
    elif any(k in _plain_sem for k in ("نور", "ضياء", "فلق", "صبح", "شمس")):
        dna = {**dna, "particles": 2}
    dust = _mvx.particles_png(dna, workdir / "dust")
    _ly = dna.get("layout", "depth" if dna["depth"] else "full")
    _mround = _mcirc = None
    for i, sc in enumerate(scene_list):
        sc.setdefault("glint", True)
        sc["dna"] = dna
        sc["dust"] = dust
        sc["layout"] = _ly
        if sc.get("video"):
            if _ly == "depth":
                _mround = _mround or _mvx.rounded_mask(workdir / "ov" / "mask.png")
                sc["mask"] = _mround
            elif _ly == "circle":
                _mcirc = _mcirc or _mvx.circle_mask(workdir / "ov" / "maskc.png")
                sc["mask"] = _mcirc
        if dna["ramp"]:
            sc["ramp"] = (i % 2 == 0)
    # مزج استوديو بين المشاهد (0.5s) + تعويض المدة عل الصوت يفضل مظبوط
    _XD = 0.5
    for sc in scene_list[:-1]:
        sc["end"] += _XD
    off += _XD * max(0, len(scene_list) - 1)
    # تايبوغرافيا ضخمة بدل الذهبي الشاعري — حسب روح الحلقة
    if dna["typo"] == "bold":
        for ev in events:
            if ev["style"] == "Ayah":
                ev["style"] = "Big"

    # هوية البراند فوق كل المشاهد: لوجو + تدرّجات + إطار ذهبي للمشاهد
    from . import intro_lab
    _sq, INTRO = intro_lab.render(dna, workdir / "intro.mp4", square=True)
    print(f"[din] intro-done arch={intro_lab._h(dna.get('seed', ''), 'intro') % 7}", flush=True)
    bl = scenes._brand_layer(workdir / "ov" / "brand.png")
    fr_ov = scenes.frame_overlay(workdir / "ov" / "frame.png",
                                 color=dna["rgb"])
    _stk = (scenes.sticker_overlay(workdir / "ov" / "sticker.png", chip,
                                   color=dna["rgb"])
            if chip else None)
    for sc in scene_list:
        sc["overlays"] = [bl] + (sc.get("overlays") or [])
        if _stk is not None:
            sc["overlays"].append(_stk)
        # الإطار الذهبي هوية الأنواع الجريئة فقط — الهادئة تتنفس بدونه
        if sc.get("frame") and kind in NEON_KINDS:
            sc["overlays"].append(fr_ov)
    # الدخلة مربع صغير فوق أول مشهد + غلاف العنوان — المحتوى يبدأ فورًا
    from . import textrender as _tr
    _Wd = settings.VIDEO["width"]
    _title_ov = _tr.text_image(title, workdir / "ov" / "title.png",
                               font_size=60, y_ratio=0.375, fill="#ffd166",
                               stroke_width=5)
    _first = scene_list[0]
    _first.setdefault("vover", []).extend([
        {"path": _sq, "x": (_Wd - 430) // 2, "y": 170,
         "st": 0.0, "en": INTRO + 0.2, "fade": 0.3},
        {"path": _title_ov, "x": 0, "y": 0, "st": 0.5, "en": 4.8, "fade": 0.45},
    ])
    # استيكرات دلالية: أيقونة متوهجة توصّف كلمات كلام الله لحظة نطقها
    from . import stickers as _stkmod
    _rgb = dna["rgb"].lstrip("#")
    _side, _flip = 210, 0
    for ev in events:
        if ev["style"] not in ("Ayah", "Big"):
            continue
        icon = _stkmod.sticker_for(ev["text"], _rgb)
        if not icon:
            continue
        sc = next((x for x in scene_list
                   if x["start"] <= ev["start"] < x["end"]), None)
        if not sc:
            continue
        png = _stkmod.sticker_png(icon, _rgb, workdir / "ov")
        _x = _Wd - _side - 46 if _flip % 2 else 46
        _flip += 1
        sc.setdefault("vover", []).append({
            "path": png, "x": _x, "y": 300,
            "st": max(0.0, ev["start"] - sc["start"] - 0.1),
            "en": min(ev["end"] + 0.5, sc["end"]) - sc["start"],
            "fade": 0.25})
    if dna["intro"] == "pop":
        # افتتاحية نبضية: أول كلمات العنوان تقفز ضخمة ثم تستقر
        _pw = " ".join(title.replace("…", "").split()[:3])
        events.append({"style": "Hdr",
                       "text": ("{\\fscx210\\fscy210"
                                "\\t(90,620,\\fscx100\\fscy100)}" + _pw),
                       "start": 0.12, "end": INTRO - 0.1})

    # كرت الختام: فائدة مسموعة فوق خلفية البراند
    voice_fayda = (f"وقف ثانية يا صديقي… {fayda} "
                   "انشر الخير، لعلها تكون صدقة جارية ليك وليّا.")
    print("[din] fayda-start", flush=True)
    fr = synthesize_line(voice_fayda, "ar", workdir / "end", name="fayda",
                         rate="-6%", pitch="-1Hz")
    print("[din] fayda-done", flush=True)
    wavs.append(fr["wav"])
    end_dur = fr["duration"] + 1.0
    scene_list.append({**_end_card(workdir, fayda,
                                   quiet=kind not in NEON_KINDS),
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
        # أجواء طبيعة حقيقية CC0 من Freesound (بلا موسيقى) — للصوت البشري فقط،
        # التلاوة تفضل صافية 100%. ولو المصدر فشل → ضوضاء بنية زي الأول.
        _amb_ok = False
        if kind in ("dua", "adhkar", "hisn"):
            try:
                from . import library as _lb
                import requests as _rq
                _u = _lb.freesound_ambience(
                    {"dua": "soft rain calm", "adhkar": "gentle night wind",
                     "hisn": "morning birds soft"}[kind])
                if _u:
                    _rb = _rq.get(_u, timeout=90)
                    if _rb.ok and len(_rb.content) > 20000:
                        _mp = workdir / "amb_src.mp3"
                        _mp.write_bytes(_rb.content)
                        subprocess.run(
                            [ffmpeg(), "-y", "-stream_loop", "-1",
                             "-i", str(_mp), "-t", f"{total:.2f}",
                             "-af", f"volume=0.05,afade=t=out:"
                             f"st={max(total - 2.0, 0.0):.2f}:d=2",
                             "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le",
                             str(amb)], capture_output=True)
                        _amb_ok = amb.exists()
            except Exception:
                _amb_ok = False
        if not _amb_ok:
            subprocess.run([ffmpeg(), "-y", "-f", "lavfi", "-i",
                            "anoisesrc=color=brown:amplitude=0.35",
                            "-af", "lowpass=f=300,volume=0.018",
                            "-t", f"{total:.2f}",
                            "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le",
                            str(amb)], capture_output=True)
        pr = subprocess.run([ffmpeg(), "-y", "-i", str(vox), "-i", str(amb),
                             "-filter_complex",
                             "[0:a]afftdn=nf=-30,"
                             "equalizer=f=110:width_type=q:width=1:g=1,"
                             "equalizer=f=3400:width_type=q:width=1:g=1.5,"
                             "acompressor=threshold=-18dB:ratio=2:attack=20:"
                             "release=250[a];"
                             "[a][1:a]amix=inputs=2:normalize=0,"
                             "loudnorm=I=-14:TP=-1.2:LRA=11[out]",
                             "-map", "[out]", "-ar", "44100", "-ac", "2",
                             "-c:a", "pcm_s16le", str(processed)],
                            capture_output=True)
    if pr.returncode == 0 and processed.exists():
        vox = processed
    print("[din] audio-done", flush=True)

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
        elif st in ("Calm", "CalmL"):
            fx = "{\\fad(420,320)}"
        elif st == "Hook":
            fx = "{\\fad(500,400)}"
        elif st == "Hdr":
            fx = "{\\fad(600,400)}"
        elif st == "WM":
            fx = "{\\fad(1200,800)}"
        else:
            fx = "{\\fad(450,350)}"
        lines.append(f"Dialogue: 0,{_t(ev['start'])},{_t(ev['end'])},{st},"
                     f",0,0,0,,{fx}{txt}\n")
    ass.write_text("".join(lines), encoding="utf-8")
    print("[din] ass-done", flush=True)

    out = settings.OUT / f"{ep_id}.mp4"
    print("[din] assemble-start", flush=True)
    video.assemble({"wav": vox, "total_duration": total,
                    "xtrans": dna.get("xtrans")}, scene_list, ass,
                   out, workdir, music=None)
    print(f"[din] assemble-done bytes={out.stat().st_size if out.exists() else 0}", flush=True)
    cover = settings.OUT / f"{ep_id}-cover.png"
    brand.compose_cover({"id": ep_id, "title_ar": title, "_kind": kind,
                         "tags": "نور,قرآن,دعوة,XDAWNOVA"}, cover)
    # 4K اختياري خارج دورة الساعة؛ ملف النشر 1080 هو المعتمد (4K feel من
    # العمق/الحركة والجسيمات). تفعيله يدويًا لا يعرقل النشر الساعي.
    v4k = out
    if settings.get_bool("XT_MAKE_4K", False) and total <= 55:
        v4k = settings.OUT / f"{ep_id}-4k.mp4"
        try:
            subprocess.run(
                [ffmpeg(), "-y", "-i", str(out), "-vf",
                 "scale=2160:3840:flags=lanczos",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                 "-x264-params", "rc-lookahead=5:sync-lookahead=0",
                 "-threads", "2",
                 "-pix_fmt", "yuv420p", "-c:a", "copy",
                 "-movflags", "+faststart", str(v4k)],
                capture_output=True, timeout=420)
            if not v4k.exists():
                v4k = out
        except Exception:
            v4k = out
    try:
        import json as _jl2
        if dna.get("_sig"):
            _hist2 = list(dna.get("_history") or [])
            _hist2.append({"sig": dna["_sig"], "seed": dna.get("seed"),
                           "kind": kind, "title": title[:80]})
            _hist2 = _hist2[-12:]
            (settings.STATE / "dna_history.json").write_text(
                _jl2.dumps(_hist2, ensure_ascii=False), encoding="utf-8")
            (settings.STATE / "dna_last.json").write_text(
                _jl2.dumps({"sig": dna["_sig"], "seed": dna.get("seed")},
                           ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return {"video": out, "video_4k": v4k, "cover": cover,
            "report": video.validate(out), "style": dna,
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
