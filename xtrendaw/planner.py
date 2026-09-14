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

KIND_ROTATION = ["quran", "adhkar", "hadith", "qissa", "dua", "tafsir", "info"]


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
    if kind in ("quran", "tafsir"):
        return [(f"s{w['surah']:03d}-{w['frm']}", w) for w in quran_windows()]
    if kind == "qissa":
        return [(q["id"], q) for q in QISSA]
    st = _stock()
    lists = {"dua": "duas", "adhkar": "adhkar", "hadith": "hadiths",
             "info": "info"}
    items = st.get(lists[kind], [])
    return [(f"{i}", {"idx": i}) for i in range(len(items))]


def next_episode() -> dict:
    """الحلقة الجاية: نوع متناوب + أول مفتاح لسه ما اتعملش."""
    led = _read_ledger()
    done = led["done"]
    last = led.get("last") or ""
    start = (KIND_ROTATION.index(last) + 1) % len(KIND_ROTATION)         if last in KIND_ROTATION else 0
    for k in range(len(KIND_ROTATION)):
        kind = KIND_ROTATION[(start + k) % len(KIND_ROTATION)]
        series = _series(kind)
        off = led["n"] % max(1, len(series))
        for i in range(len(series)):
            key, spec = series[(off + i) % len(series)]
            lk = f"{kind}:{key}"
            if lk not in done:
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
    if kind in ("quran", "tafsir"):
        pool = [x["scenes"] for x in _dinmod.QURAN]
        scenes = pool[n % len(pool)]
        spec = {**spec, "id": f"{kind[:1]}{key}", "scenes": scenes}
        title = f"{spec.get('name', '')} ﴿{spec['frm']}–{spec['to']}﴾ — {rec_name}"
    elif kind == "qissa":
        spec = dict(spec)
        title = f"قصة: {spec.get('title', key)} — {rec_name}"
    else:
        st = _stock()
        lists = {"dua": ("duas", "دعاء"), "adhkar": ("adhkar", "ذِكر"),
                 "hadith": ("hadiths", "حديث"), "info": ("info", "معلومة")}
        lname, lab = lists[kind]
        item = st[lname][spec["idx"] % len(st[lname])]
        title = f"{lab}: {item['text'][:42]}…"
    return {"id": f"noor-{kind}-{key}-r{rec}",
            "title_ar": title, "tags": "نور,قرآن,دعوة,XDAWNOVA",
            "_din": kind, "_din_rec": rec, "_din_spec": spec, "_kind": kind}
