"""المخطّط الذكي — مصنع يعرف هو بيعمل إيه.

سلاسل تكفي سنين، بلا تكرار، والمسجّل (ledger) على git عشان كل دورة
تكمل من مكان اللي قبلها:
  - قرآن مُقطَّع: كل السور نوافذ ~4 آيات  (~1500 حلقة) × تناوب 4 قراء
  - تفسير: نفس النوافذ بشرح الميسّر     (~1500 حلقة)
  - قصص الأنبياء: مقاطع قصصية من السور   (16 قصة)
  - أذكار / أدعية / أحاديث+نووي / معلومات (مخزون محلي صحيح)

next_episode() بيرجّع موضوع الحلقة الجاية ذكيًا: تناوب أنواع + أول مفتاح
لسه ما اتنتجش في سلسلته.
"""
from __future__ import annotations

import json

from . import settings, state
from . import din as _dinmod
QISSA = _dinmod.QISSA

LEDGER = settings.STATE / "ledger.json"
WINDOWS_CACHE = settings.STATE / "quran_windows.json"

KIND_ROTATION = ["quran", "adhkar", "hadith", "qissa", "dua",
               "tafsir", "info", "seerah", "asma", "kawn", "akhira",
               "akhlaq", "juz", "nawawi"]


def _read_ledger() -> dict:
    if LEDGER.exists():
        try:
            return json.loads(LEDGER.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"done": {}, "n": 0}


def _write_ledger(d: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def quran_windows() -> list[dict]:
    """نوافذ ~4 آيات لكل السور — مخزنة محليًا عشان سنين."""
    if WINDOWS_CACHE.exists():
        return json.loads(WINDOWS_CACHE.read_text(encoding="utf-8"))
    import requests

    data = requests.get(f"{_dinmod.APIQ}/surah",
                        headers={"User-Agent": "XDAW-NOVA/1.0"},
                        timeout=30).json()["data"]
    wins = []
    for s in data:
        n, num = s["numberOfAyahs"], s["number"]
        step = 4 if n > 8 else n
        for frm in range(1, n + 1, step):
            to = min(n, frm + step - 1)
            wins.append({"surah": num, "frm": frm, "to": to, "n": n,
                         "name": s.get("name", "")})
    WINDOWS_CACHE.write_text(json.dumps(wins), encoding="utf-8")
    return wins


def _stock() -> dict:
    return json.loads((settings.ROOT / "content" / "din_stock.json")
                      .read_text(encoding="utf-8"))


def _series(kind: str) -> list[tuple[str, dict]]:
    """[(مفتاح, spec)] بترتيب ثابت للسلسلة."""
    if kind == "juz":
        return [(f"j{w['surah']:03d}-{w['frm']}", w)
                for w in quran_windows() if w["surah"] >= 78]
    if kind in ("quran", "tafsir"):
        return [(f"s{w['surah']:03d}-{w['frm']}", w) for w in quran_windows()]
    if kind == "qissa":
        return [(q["id"], q) for q in QISSA]
    st = _stock()
    lists = {"dua": "duas", "adhkar": "adhkar", "hadith": "hadiths",
             "info": "info", "seerah": "seerah", "asma": "asma",
             "kawn": "kawn", "akhira": "akhira", "akhlaq": "akhlaq",
             "nawawi": "nawawi"}
    items = st.get(lists[kind], [])
    return [(f"{i}", {"idx": i}) for i in range(len(items))]


# آيات ذهبية — الأقرب للقلب والأشهر: تتقدم على الترتيب العادي
GOLD_AYAHS = [
    (55, 1), (55, 13), (55, 26), (55, 46), (55, 60),      # الرحمن
    (67, 1), (67, 3),                                     # الملك
    (93, 1), (93, 5), (93, 9), (94, 1),                   # الضحى والشرح
    (2, 152), (2, 156), (2, 186), (2, 255), (2, 285),     # البقرة: اذكروني/الصبر/الدعاء/الكرسي/آمن الرسول
    (3, 139), (3, 159), (13, 28), (39, 53), (9, 40),      # لا تهن/فبما رحمة/تطمئن القلوب/لا يقنط/لا تحزن
    (20, 25), (14, 7), (12, 87), (21, 107), (19, 96),     # اشرح لي/لأزيدنكم/لا تيأسوا/رحمة للعالمين/ودّ المؤمنين
    (57, 22), (65, 2), (11, 88), (29, 69), (10, 62),      # المصيبة/يتق يجعل مخرجا/توكلت/يجاهدون/أولياء الله
    (112, 1), (113, 1), (114, 1), (1, 1),                 # الإخلاص والمعوذتان والفاتحة
    (17, 80), (25, 74), (35, 2), (7, 56), (4, 69),        # مدخل صدق/قرة أعين/الرحمة/لا تفسدوا/مع المنعمين
]


def _golden_keys(kind: str) -> set:
    """مفاتيح النوافذ اللي فيها آية ذهبية."""
    keys = set()
    if kind not in ("quran", "tafsir"):
        return keys
    for w in quran_windows():
        for su, ay in GOLD_AYAHS:
            if w["surah"] == su and w["frm"] <= ay <= w["to"]:
                keys.add(f"s{w['surah']:03d}-{w['frm']}")
    return keys


# أنواع السلاسل الواعية تُعرَّف في din (SERIES_KINDS / SERIES_LABEL)


def _coverage_order(kind: str, keys: list) -> list[int]:
    """سلاسل واعية بالترتيب، والباقي ذهبي أولًا ثم تغطية شبه عشوائية."""
    from . import din as _d

    if kind in _d.SERIES_KINDS:
        return list(range(len(keys)))
    import hashlib
    gold = _golden_keys(kind)
    return sorted(range(len(keys)), key=lambda i: (
        0 if keys[i] in gold else 1,
        hashlib.sha1(f"{kind}:{i}".encode()).hexdigest()))


def next_episode() -> dict:
    """الحلقة الجاية: نوع متناوب (متغيّر كل دور) + تغطية كاملة للمخزون."""
    import random as _rnd
    led = _read_ledger()
    done = led["done"]
    skip = led.get("skip") or {}
    last = led.get("last") or ""
    # ترتيب الأنواع يتبدّل كل دور كامل — نفس التغطية، شكل مختلف كل مرة
    order = KIND_ROTATION[:]
    _rnd.Random(led["n"] // len(KIND_ROTATION)).shuffle(order)
    start = (order.index(last) + 1) % len(order) if last in order else 0
    # 🧠 ذكاء الذروة: مساء مصر (١٦–٢٣ القاهرة) الجمهور الأعظم → قدّم الأعمق
    import datetime as _dt

    if _dt.datetime.now(_dt.timezone(
            _dt.timedelta(hours=2))).hour in range(16, 23):
        order = [k for k in ("quran", "tafsir") if k in order] + \
                [k for k in order if k not in ("quran", "tafsir")]
        start = 0
    # 🎛 زر الأدمن: state/force_kind.json يقدّم نوعًا واحدًا لمرة واحدة (بلا تكرار)
    _fkp = LEDGER.with_name("force_kind.json")
    if _fkp.exists():
        try:
            _fk = _fkp.read_text(encoding="utf-8").strip().strip('"')
            _fkp.unlink(missing_ok=True)
            if _fk in KIND_ROTATION:
                order = [_fk] + [k for k in order if k != _fk]
                start = 0
        except Exception:
            pass
    for k in range(len(order)):
        kind = order[(start + k) % len(order)]
        series = _series(kind)
        for i in _coverage_order(kind, [k for k, _ in series]):
            key, spec = series[i]
            lk = f"{kind}:{key}"
            if lk in done or skip.get(lk, 0) >= 2:
                continue
            if True:
                from . import din as _din2
                from . import state as _st2
                _prov = [i for i, (rid, _, _) in enumerate(_din2.RECITERS)
                         if rid in _st2.reciter_proven()]
                if kind in ("quran", "tafsir", "qissa") and _prov:
                    rec = _prov[led["n"] % len(_prov)]
                else:
                    rec = led["n"] % 4
                n = led["n"] + 1
                t = _topic(kind, key, spec, rec, n)
                t["_ledger_key"] = lk
                t["_ledger_n"] = n
                return t
    # كل السلاسل خلصت (مش هيحصل قبل سنين) — نلف من أولها بنسخة قارئ تانية
    led["done"] = {}
    _write_ledger(led)
    return next_episode()


def mark_fail(topic: dict) -> None:
    """حلقة فشلت إنتاج — بعد محاولتين المخطّط يتخطاها للأبد (مفيش تجميد)."""
    led = _read_ledger()
    led.setdefault("skip", {})
    k = topic.get("_ledger_key")
    if k:
        led["skip"][k] = int(led["skip"].get(k, 0)) + 1
        _write_ledger(led)


def mark_done(topic: dict) -> None:
    """بعد نجاح الإنتاج بس — عشان الحلقة الفاشلة تتعاد مش تضيع."""
    led = _read_ledger()
    led["done"][topic["_ledger_key"]] = 1
    led["n"] = topic["_ledger_n"]
    led["last"] = topic["_din"]
    _write_ledger(led)


def _topic(kind: str, key: str, spec: dict, rec: int, n: int) -> dict:
    from . import din
    from . import state as _st

    _bad = _st.reciter_badlist()
    if din.RECITERS[rec % len(din.RECITERS)][0] in _bad:
        for _i, _alt in enumerate(din.RECITERS):
            if _alt[0] not in _bad:
                rec = _i
                break
    rec_name = din.RECITERS[rec % len(din.RECITERS)][1]
    if kind in ("quran", "tafsir", "juz"):
        pool = [x["scenes"] for x in _dinmod.QURAN]
        scenes = pool[n % len(pool)]
        spec = {**spec, "id": f"{kind[:1]}{key}", "scenes": scenes}
        title = f"{spec.get('name', '')} ﴿{spec['frm']}–{spec['to']}﴾ — {rec_name}"
    elif kind == "qissa":
        spec = dict(spec)
        from . import din as _d

        _qi = next((j for j, q in enumerate(_d.QISSA) if q["id"] == key), 0)
        title = (f"سلسلة قصص الأنبياء ({_qi + 1}/{len(_d.QISSA)}): "
                 f"{spec.get('title', key)}")
    else:
        st = _stock()
        lists = {"dua": ("duas", "دعاء"), "adhkar": ("adhkar", "ذِكر"),
                 "hadith": ("hadiths", "حديث"), "info": ("info", "معلومة"),
                 "seerah": ("seerah", "سيرة"), "asma": ("asma", "اسم"),
                 "kawn": ("kawn", "كون"), "akhira": ("akhira", "آخرة"),
                 "akhlaq": ("akhlaq", "خُلق"),
                 "nawawi": ("nawawi", "نووية")}
        lname, lab = lists[kind]
        item = st[lname][spec["idx"] % len(st[lname])]
        from . import din as _d

        if kind in _d.SERIES_LABEL:
            title = (f"{_d.SERIES_LABEL[kind]} ({spec['idx'] + 1}"
                     f"/{len(st[lname])}): {item['text'][:34]}…")
        else:
            title = f"{lab}: {item['text'][:42]}…"
    return {"id": f"noor-{kind}-{key}-r{rec}",
            "title_ar": title, "tags": "نور,قرآن,دعوة,XDAWNOVA",
            "_din": kind, "_din_rec": rec, "_din_spec": spec, "_kind": kind}
