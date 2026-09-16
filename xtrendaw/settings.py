"""الإعدادات المركزية.

قاعدة إلزامية: **مفيش قيمة سرية مكتوبة هنا**. كل حاجة من متغيرات البيئة
(محليًا: .env/secrets.txt المهمل في git · على GitHub: Secrets).
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
OUT = ROOT / "content" / "vids"
STATE = ROOT / "state"
ASSETS = ROOT / "assets"
FONTS = ASSETS / "fonts"

for _d in (WORK, OUT, STATE, FONTS):
    _d.mkdir(parents=True, exist_ok=True)

def get(key: str, default: str = "") -> str:
    return (os.environ.get(key) or default).strip()

def get_int(key: str, default: int) -> int:
    try:
        return int(float(get(key, str(default))))
    except ValueError:
        return default

def get_float(key: str, default: float) -> float:
    try:
        return float(get(key, str(default)))
    except ValueError:
        return default

def get_bool(key: str, default: bool = False) -> bool:
    v = get(key, "").lower()
    return default if not v else v in ("1", "true", "yes", "on")

# ─────────────────────────────────────────────────────────────
# مواصفات الفيديو — ثابتة لأن المنصات بتفرضها، مش تفضيل
# ─────────────────────────────────────────────────────────────
VIDEO = {
    "width": 1080,
    "height": 1920,          # 9:16 مطلوب لـReels/Shorts
    "fps": 30,               # إنستجرام يقبل 23–60
    "vcodec": "libx264",     # H.264 — إنستجرام يرفض غيره (خطأ 24)
    "acodec": "aac",         # AAC إلزامي
    "max_seconds": 90,       # حد إنستجرام API للـReels
    "target_seconds": 55,    # الهدف: 35–55 ثانية
    "max_bytes": 40 * 1024 * 1024,  # ≤40MB (حد إنستجرام 100MB — هامش أمان)
}

# ─────────────────────────────────────────────────────────────
# الصوت
# ─────────────────────────────────────────────────────────────
VOICE_AR = get("XT_VOICE_AR", "ar-EG-SalmaNeural")  # صوت أنثوي دافئ للمحتوى الديني
VOICE_EN = get("XT_VOICE_EN", "en-US-JennyNeural")
VOICE_RATE = get("XT_VOICE_RATE", "+8%")
VOICE_PITCH = get("XT_VOICE_PITCH", "+12Hz")

# مواعيد نشر الذروة (بتوقيت القاهرة) — المصنع يخزّن في أي ساعة ويفرج في الذروة.
# كوتة يوتيوب الرسمية ≈ 6 عمليات رفع/يوم → ست ذروات القاهرة تكفل النشر اليومي كاملًا.
_ph = get("XT_PUBLISH_HOURS", "all").strip()
PUBLISH_HOURS = (list(range(24)) if _ph in ("all", "") else
                 [int(h) for h in _ph.split(",") if h.strip().lstrip("-").isdigit()])

# وضع القناة: "deen" = محرك النور (الافتراضي بعد الانقلاب) · "old" = ترند/معرفة
CHANNEL_MODE = get("XT_MODE", "deen")
# نشر يوتيوب (بيتوقف مؤقتًا لاختبار سلامة المطالبات — تيليجرام شغال دايمًا)
PUBLISH_YOUTUBE = get("XT_YT", "1").strip() == "1"
# الصوت: piper = عربي حرفي بمخارج صحيحة (مجاني بلا حد)، وedge بديل احتياطي
TTS_ENGINE = get("XT_TTS_ENGINE", "edge")  # نيورال طبيعي، piper احتياطي
PIPER_RELEASE = "noor-models"
# يوتيوب: حلقات التلاوة — off = ما تنزلش يوتيوب (تيليجرام تنزل عادي)
# tts = تتلاوى بصوت نور المملوك لنا (صفر حقوق للأبد)
YT_RECITE_MODE = get("XT_YT_QURAN", "auto")  # auto=المعتمدين فقط / off=منع كامل
PIPER_DIR = Path(os.environ.get("XT_PIPER_DIR", "/tmp/noor-models"))

# ─────────────────────────────────────────────────────────────
# LLM مجاني (Groq) — اختياري، والمحرك شغال بدونه
# ─────────────────────────────────────────────────────────────
LLM = {
    "base": get("LLM_API_BASE"),
    "key": get("LLM_API_KEY"),
    "model": get("LLM_MODEL", "llama-3.3-70b-versatile"),
}

PEXELS_KEY = get("PEXELS_API_KEY")

YOUTUBE = {
    "client_id": get("YOUTUBE_CLIENT_ID"),
    "client_secret": get("YOUTUBE_CLIENT_SECRET"),
    "refresh_token": get("YOUTUBE_REFRESH_TOKEN"),
}
FACEBOOK = {"page_id": get("FACEBOOK_PAGE_ID"), "token": get("FACEBOOK_PAGE_TOKEN")}
INSTAGRAM = {"user_id": get("INSTAGRAM_USER_ID"), "token": get("INSTAGRAM_ACCESS_TOKEN")}

# الساندبوك = SELF_ONLY؛ بعد الموافقة الرسمية حوّلها PUBLIC_TO_EVERYONE
TIKTOK_PRIVACY = get("TIKTOK_PRIVACY", "SELF_ONLY")

TOKEN_KEY = get("XT_TOKEN_KEY")  # مفتاح تشفير التوكنز في الحالة العامة

TIKTOK = {"client_key": get("TIKTOK_CLIENT_KEY"),
          "client_secret": get("TIKTOK_CLIENT_SECRET"),
          "access_token": get("TIKTOK_ACCESS_TOKEN"),
          "refresh_token": get("TIKTOK_REFRESH_TOKEN")}


def _tt_state():
    f = STATE / "tiktok_token.json"
    if f.exists():
        try:
            import base64 as _b
            import json as _json
            d = _json.loads(f.read_text(encoding="utf-8")) or {}
            if d.get("enc") and TOKEN_KEY:
                import nacl.secret as _ns
                box = _ns.SecretBox(_b.b64decode(TOKEN_KEY))
                d = _json.loads(box.decrypt(_b.b64decode(d["enc"])).decode())
            return d
        except Exception:
            pass
    return {}


_tt = _tt_state()
if _tt.get("access_token"):
    TIKTOK["access_token"] = _tt["access_token"]
if _tt.get("refresh_token"):
    TIKTOK["refresh_token"] = _tt.get("refresh_token")


def _ig_state_token():
    """التوكن المتجدد المخزن في الحالة — بيعلو على المتغير البيئي."""
    f = STATE / "ig_token.json"
    if f.exists():
        try:
            import json as _json
            return (_json.loads(f.read_text(encoding="utf-8")) or {}).get("token")
        except Exception:
            pass
    return None


_igt = _ig_state_token()
if _igt:
    INSTAGRAM["token"] = _igt
TELEGRAM = {"token": get("TELEGRAM_BOT_TOKEN"),
            "chat_id": get("TELEGRAM_CHAT_ID"),
            "admin_chat": get("TELEGRAM_ADMIN_CHAT_ID")}

DAILY_CAP = get_int("XT_DAILY_CAP", 4)          # سقف نشر آمن/يوم

def has_youtube() -> bool:
    return all(YOUTUBE.values())

def has_facebook() -> bool:
    return bool(FACEBOOK["page_id"] and FACEBOOK["token"])

def has_tiktok() -> bool:
    return bool(TIKTOK.get("client_key") and TIKTOK.get("access_token"))


def has_instagram() -> bool:
    return bool(INSTAGRAM["user_id"] and INSTAGRAM["token"])

def has_telegram() -> bool:
    return bool(TELEGRAM["token"] and TELEGRAM["chat_id"])

def has_llm() -> bool:
    return bool(LLM["base"] and LLM["key"])

def has_pexels() -> bool:
    return bool(PEXELS_KEY)

BRAND = {
    "name": "XDAW NOVA",
    "tagline_ar": "نور • معرفة • رحمة • قوة مسؤولة",
    "tagline_en": "LIGHT • KNOWLEDGE • MERCY • RESPONSIBLE STRENGTH",
    "hashtags": "#حقائق #علوم #XDAWNOVA",
    "outro_ar": "انتو خير ونور من الله. تابع XDAW NOVA.",
    "outro_en": "You are goodness and light. Follow XDAW NOVA.",
    # زاد نوفا الافتراضي — ملخص العقل والقلب والروح لما الموضوع مايكتبش زاده
    "takeaway_ar": {
        "aql": "المعرفة مش معلومات… المعرفة قوة مسؤولة.",
        "qalb": "إنت مش وحدك في الكون ده — إحنا معاك.",
        "rouh": "نور • رحمة • خير من الله… دايمًا.",
    },
    "takeaway_en": {
        "aql": "Knowledge isn't trivia — it's responsible power.",
        "qalb": "You're not alone in this universe — we're with you.",
        "rouh": "Light • mercy • goodness from God… always.",
    },
}
LOGO = ASSETS / "brand" / "logo.png"
