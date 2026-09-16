"""إيچنت المكتبة — مكتبة لا نهائية بتجدد نفسها.

يجلب من مصادر موثوقة مجانية بلا مفاتيح:
- الأحاديث: صحيح البخاري، صحيح مسلم، سنن أبي داود، سنن ابن ماجه، موطأ مالك
  (fawazahmed0/hadith-api على jsDelivr — نصوص عربية كاملة)
- التفسير: تفسير الميسر لكل آية (api.quran.com — id=16)

كل دورة إنتاج يستدعيه run_cycle بميزانية صغيرة → المخزون بيكبر كل ساعة
لحد ما يغطي المصادر كلها (~25 ألف حديث + 6236 تفسير) وبعدها يلف بالتنويع.
مضاف فقط — لا تعديل ولا حذف لأي محتوى قائم.
"""
from __future__ import annotations

import hashlib
import json
import re
import time

import requests

from . import settings

HADITH_SOURCES = [
    ("ara-bukhari", "صحيح البخاري"),
    ("ara-muslim", "صحيح مسلم"),
    ("ara-abudawud", "سنن أبي داود"),
    ("ara-ibnmajah", "سنن ابن ماجه"),
    ("ara-malik", "موطأ مالك"),
]
TAFSIR_ID = 16          # الميسر — عربي
MIN_LEN, MAX_LEN = 45, 330   # طول مناسب لحلقة ≤90ث
UA = {"User-Agent": "XDAW-NOVA-factory/1.0 (free knowledge shorts)"}

_seen_p = settings.ROOT / "state" / "expand_seen.json"
_tbank_p = settings.ROOT / "content" / "tafsir_bank.json"
_cache_p = settings.ROOT / "state" / "hadith_cache.json"


def _seen() -> dict:
    if _seen_p.exists():
        try:
            return json.loads(_seen_p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"h": [], "src_i": 0, "next_i": 0, "taf_v": 0}


def _save_seen(s: dict) -> None:
    _seen_p.parent.mkdir(parents=True, exist_ok=True)
    _seen_p.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")


def _h(t: str) -> str:
    return hashlib.md5(t.encode("utf-8")).hexdigest()[:12]


def _clean(t: str) -> str:
    t = re.sub(r"\s+", " ", t).strip()
    return t


_TASH = re.compile("[\u064b-\u0652\u0670\u0640]")


def _bare(s: str) -> str:
    s = _TASH.sub("", s)
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ٱ", "ا"), ("ء", "")):
        s = s.replace(a, b)
    return s


def _matn(a: str) -> str:
    """يستخلص المتن: يقص السند عند آخر «قال» — مقاوم للتشكيل."""
    keep = [i for i, ch in enumerate(a) if not _TASH.match(ch)]
    bare = _bare("".join(a[i] for i in keep))
    pos = bare.rfind(" قال")   # حد كلمة — ما نقصش نص «فقال»
    if pos < 0:
        pos = 0 if bare.startswith("قال") else -1
    if pos < 0:
        return a
    j = pos + (4 if bare[pos] == " " else 3)
    if j >= len(keep):
        return a
    out = a[keep[j]:].strip(" ،,:\u060c«»\u200f")
    if len(out) < 30 or len(_bare(out).split()[0]) < 3:
        return a
    return out


def _cache_editions() -> list[dict]:
    """كل أحاديث المصادر العربية (كاش محلي — تحميل واحد)."""
    if _cache_p.exists():
        try:
            c = json.loads(_cache_p.read_text(encoding="utf-8"))
            if len(c.get("items", [])) > 5000:
                return c["items"]
        except Exception:
            pass
    items = []
    for name, label in HADITH_SOURCES:
        try:
            r = requests.get(
                f"https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/"
                f"editions/{name}.json", headers=UA, timeout=60)
            if not r.ok:
                continue
            for h in r.json().get("hadiths", []):
                a = _clean(h.get("text") or h.get("arabic") or "")
                # استخلاص المتن: آخر مقطع بعد نهاية السند
                if _bare(a)[:8].startswith(("حدثنا", "اخبرنا", "حدثني")):
                    a = _clean(_matn(a))
                    if _bare(a)[:8].startswith(("حدثنا", "اخبرنا", "حدثني")):
                        continue  # السند ما اتفكش — مرفوض
                if MIN_LEN <= len(a) <= MAX_LEN:
                    items.append({"text": a, "src": label})
        except Exception:
            continue
    if items:
        _cache_p.parent.mkdir(parents=True, exist_ok=True)
        _cache_p.write_text(json.dumps({"items": items}, ensure_ascii=False),
                            encoding="utf-8")
    return items


def _verse_keys() -> list[str]:
    """كل مفاتيح الآيات بالترتيب (كاش)."""
    p = settings.ROOT / "state" / "verse_keys.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    keys = []
    r = requests.get("https://api.quran.com/api/v4/chapters",
                     params={"language": "ar"}, headers=UA, timeout=30)
    for ch in r.json().get("chapters", []):
        s = ch["id"]
        for v in range(1, ch["verses_count"] + 1):
            keys.append(f"{s}:{v}")
    if keys:
        p.write_text(json.dumps(keys), encoding="utf-8")
    return keys


def tafsir_batch(limit: int = 8) -> list[dict]:
    """تفسير الميسر للآيات التالية بالترتيب."""
    st = _seen()
    keys = _verse_keys()
    if not keys:
        return []
    out = []
    i = st.get("taf_v", 0)
    tries = 0
    while len(out) < limit and i < len(keys) and tries < limit * 4:
        tries += 1
        vk = keys[i]
        i += 1
        try:
            r = requests.get(
                f"https://api.alquran.cloud/v1/ayah/{vk}/ar.muyassar",
                headers=UA, timeout=20)
            if r.status_code != 200:
                continue
            txt = _clean((r.json().get("data") or {}).get("text", ""))
            if len(txt) < 40:
                continue
            s, v = vk.split(":")
            out.append({"id": f"taf-{vk.replace(':', '-')}", "surah": int(s),
                        "frm": int(v), "to": int(v), "text": txt[:340],
                        "src": "تفسير الميسر"})
        except Exception:
            continue
    st["taf_v"] = i
    _save_seen(st)
    return out


def hadith_batch(limit: int = 120) -> list[dict]:
    st = _seen()
    items = _cache_editions()
    if not items:
        return []
    seen = set(st.get("h", []))
    out = []
    i = st.get("next_i", 0)
    while len(out) < limit and i < len(items):
        it = items[i]
        i += 1
        k = _h(it["text"])
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    st["next_i"] = i
    st["h"] = list(seen)
    _save_seen(st)
    return out


def run(hadith_limit: int = 120, tafsir_limit: int = 8) -> dict:
    """تنفيذ دورة تجديد — يعيد إحصائيات الإضافة."""
    rep = {"hadiths": 0, "tafsir": 0}
    sp = settings.ROOT / "content" / "din_stock.json"
    stock = json.loads(sp.read_text(encoding="utf-8"))
    hs = hadith_batch(hadith_limit)
    if hs:
        stock.setdefault("hadiths", []).extend(hs)
        sp.write_text(json.dumps(stock, ensure_ascii=False, indent=1),
                      encoding="utf-8")
        rep["hadiths"] = len(hs)
    tf = tafsir_batch(tafsir_limit)
    if tf:
        bank = []
        if _tbank_p.exists():
            try:
                bank = json.loads(_tbank_p.read_text(encoding="utf-8"))
            except Exception:
                bank = []
        bank.extend(tf)
        _tbank_p.parent.mkdir(parents=True, exist_ok=True)
        _tbank_p.write_text(json.dumps(bank, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        rep["tafsir"] = len(tf)
    rep["total_hadiths"] = len(stock.get("hadiths", []))
    return rep


if __name__ == "__main__":
    import sys
    hl = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    tl = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    print(run(hl, tl))
