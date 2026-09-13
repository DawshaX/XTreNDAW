"""تيليجرام — بوت يرفع الفيديو للقناة مباشرة. مجاني، بلا كوتة قاسية، مدي الحياة.

الحد الرسمي للملف في رسالة بوت: 50MB — فيديوهاتنا ≤40MB فتعدّي براحتها.
"""
import requests

from .. import settings

API = "https://api.telegram.org/bot{tok}"


def publish(video_path, title, caption, tags):
    if not settings.has_telegram():
        return None, "no_credentials"
    base = API.format(tok=settings.TELEGRAM["token"])
    text = f"{title}\n\n{caption}"
    if tags:
        text += "\n" + " ".join(f"#{t.replace(' ', '_')}" for t in tags[:8])
    with open(video_path, "rb") as f:
        r = requests.post(f"{base}/sendVideo",
                          data={"chat_id": settings.TELEGRAM["chat_id"],
                                "caption": text[:1024]},
                          files={"video": f}, timeout=900)
    if not r.ok:
        return None, f"tg_{r.status_code}:{r.text[:80]}"
    return f"https://t.me/{r.json()['result']['chat']['username']}/" \
           f"{r.json()['result']['message_id']}", None
