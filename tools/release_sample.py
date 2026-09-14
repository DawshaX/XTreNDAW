# -*- coding: utf-8 -*-
"""نشر حلقة العينة المعتمدة على كل المنصات + تسجيلها للمراقبة."""
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

URL = "https://github.com/DawshaX/XTreNDAW/releases/download/noor-samples/sample.mp4"
TITLE = "سُورَةُ الشَّرۡحِ ﴿1–8﴾ — تلاوة نادرة للشيخ أيمن سويد 🤍"
CAPTION = (
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
TAGS = ["قرآن", "تلاوة", "سورة الشرح", "أيمن سويد", "نور", "shorts"]


def main() -> int:
    from xtrendaw import state
    from xtrendaw.publish import telegram, youtube

    vid = ROOT / "work" / "sample_release.mp4"
    vid.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(URL, timeout=300)
    vid.write_bytes(r.content)
    print(f"✓ تحميل العينة: {vid.stat().st_size} bytes")

    yt_url, err = youtube.publish(vid, TITLE, CAPTION, TAGS)
    print("YOUTUBE:", yt_url or f"FAIL {err}")
    if yt_url and "watch?v=" in yt_url:
        state.push_yt_recent({
            "id": yt_url.split("watch?v=")[-1].split("&")[0],
            "title": TITLE, "reciter": "ar.aymanswoaid",
            "ts": __import__("time").time()})
        print("✓ مسجلة في قائمة المراقبة — الووتشدوج هيحميها")

    tg_url, err = telegram.publish(vid, TITLE, CAPTION, TAGS)
    print("TELEGRAM:", tg_url or f"FAIL {err}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
