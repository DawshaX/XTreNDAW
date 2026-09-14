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
    url = (f"https://t.me/{r.json()['result']['chat']['username']}/"
           f"{r.json()['result']['message_id']}")
    admin = settings.TELEGRAM.get("admin_chat")
    if admin:
        send_text(f"📣 نُشر الآن على القناة:\n{title}\n{url}", admin)
    return url, None


def send_text(text: str, chat_id: str | None = None) -> bool:
    """رسالة نصية للقناة أو لأدمن المصنع (إشعارات فورية)."""
    if not settings.has_telegram():
        return False
    base = API.format(tok=settings.TELEGRAM["token"])
    try:
        r = requests.post(
            f"{base}/sendMessage",
            data={"chat_id": chat_id or settings.TELEGRAM["chat_id"],
                  "text": text[:4000]}, timeout=60)
        return r.ok
    except Exception:
        return False
