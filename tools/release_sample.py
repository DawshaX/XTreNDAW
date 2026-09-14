# -*- coding: utf-8 -*-
"""نشر حلقة العينة المعتمدة على كل المنصات + تسجيلها للمراقبة."""
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import os

URL = os.environ.get("RELEASE_URL") or \
    "https://github.com/DawshaX/XTreNDAW/releases/download/noor-samples/sample.mp4"
TITLE = os.environ.get("RELEASE_TITLE") or "سُورَةُ الشَّرۡحِ ﴿1–8﴾ — تلاوة نادرة للشيخ أيمن سويد 🤍"
_DEFAULT_CAPTION = (
    "🎧 غمّض عينك واسمع… تلاوة نادرة تهدي القلب وتشفي الصدر.\n\n"
    "📖 سورة الشرح (ألم نشرح) — الآيات 1–8 كاملة، بصوت الشيخ أيمن سويد.\n\n"
    "✨ معنى السورة: منّ الله على نبيه ﷺ بشرح الصدر، ووضع الوزر، "
    "ورفع الذكر… وفيها أعظم بشرى: ﴿إِنَّ مَعَ الْعُسْرِ يُسْرًا﴾.\n\n"
    "✅ تلاوة صحيحة بالتشكيل الدقيق من المصحف\n"
    "✅ ترجمة ومعنى وفائدة في الختام\n"
    "✅ بدون موسيقى — راحة لأذنك وقلبك\n\n"
    "شارِكها مع اللي تحبهم — «الدال على الخير كفاعله» 🤍\n"
    "نور جديد كل ساعة: @XTreNDAW\n\n"
    "🔎 سورة الشرح, ألم نشرح لك صدرك, تلاوة نادرة, أيمن سويد, "
    "قرآن كريم, إن مع العسر يسرا\n"
    "#سورة_الشرح #قرآن #تلاوة #ايمن_سويد #نور #اسلام #shorts"
)
CAPTION = os.environ.get("RELEASE_CAPTION") or _DEFAULT_CAPTION
TAGS = ["قرآن", "تلاوة", "سورة الشرح", "أيمن سويد", "نور", "shorts"]


PLATFORMS = [x.strip() for x in
             (os.environ.get("RELEASE_PLATFORMS") or "all").split(",")
             if x.strip()]


def _want(name: str) -> bool:
    return "all" in PLATFORMS or name in PLATFORMS


def main() -> int:
    import time as _time

    from xtrendaw import settings, state
    from xtrendaw.publish import facebook, instagram, telegram, tiktok, youtube

    vid = ROOT / "work" / "sample_release.mp4"
    vid.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(URL, timeout=300)
    vid.write_bytes(r.content)
    print(f"✓ تحميل العينة: {vid.stat().st_size} bytes")

    if _want("youtube") and settings.has_youtube():
        yt_url, err = youtube.publish(vid, TITLE, CAPTION, TAGS)
        print("YOUTUBE:", yt_url or f"FAIL {err}")
        if yt_url and "watch?v=" in yt_url:
            state.push_yt_recent({
                "id": yt_url.split("watch?v=")[-1].split("&")[0],
                "title": TITLE,
                "reciter": os.environ.get("RELEASE_RECITER") or "ar.aymanswoaid",
                "ts": _time.time()})
            print("✓ مسجلة في قائمة المراقبة — الووتشدوج هيحميها")
    else:
        print("YOUTUBE: متخطي (اختيار المنصات)")

    if _want("telegram") and settings.has_telegram():
        tg_url, err = telegram.publish(vid, TITLE, CAPTION, TAGS)
        print("TELEGRAM:", tg_url or f"FAIL {err}")

    if _want("instagram") and settings.has_instagram():
        ig_url, err = instagram.publish(URL, TITLE, CAPTION, TAGS)
        print("INSTAGRAM:", ig_url or f"FAIL {err}")

    if _want("facebook") and settings.has_facebook():
        fb_url, err = facebook.publish(URL, TITLE, CAPTION, TAGS)
        print("FACEBOOK:", fb_url or f"FAIL {err}")

    if _want("tiktok") and settings.has_tiktok():
        tt_url, err = tiktok.publish(vid, TITLE, CAPTION, TAGS)
        print("TIKTOK:", tt_url or f"FAIL {err}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
