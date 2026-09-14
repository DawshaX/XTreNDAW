# -*- coding: utf-8 -*-
"""بوت نوفا التفاعلي — مساعدك الشخصي على تيليجرام.

شغال كل 5 دقايق على رنر GitHub (مجاني للأبد): يقرأ رسائلك، يرد،
ينفذ أوامرك، ويبعتلك الإحصائيات والملخص اليومي.

الأوامر:
  /stats  — إحصائيات القناة (مشتركين/مشاهدات/فيديوهات) + المصنع
  /status — حالة المصنع والحماية
  /next   — إنتاج ونشر فوري
  /pause  — إيقاف النشر مؤقتًا (الإنتاج مستمر)
  /resume — رجوع النشر
  /watch  — فحص المحظور الآن
ومعظم الكلام العادي يفهمه بالعربي (احصائيات/وقف/كمل/التالي/افحص).
"""
from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from . import settings

TG = "https://api.telegram.org/bot{tok}/{method}"
PAUSE_FILE = settings.STATE / "pause.json"
OFFSET_FILE = settings.STATE / "bot_offset.json"
DIGEST_FILE = settings.STATE / "bot_digest.json"


def _call(method: str, **data):
    tok = settings.TELEGRAM["token"]
    try:
        r = requests.post(TG.format(tok=tok, method=method),
                          json=data, timeout=60)
        return r.json() if r.ok else {"ok": False}
    except Exception:
        return {"ok": False}


def send(chat_id, text: str) -> None:
    _call("sendMessage", chat_id=str(chat_id), text=text[:4000])


def _admin(chat_id) -> bool:
    return str(chat_id) == str(settings.TELEGRAM.get("admin_chat") or "")


# ---------------------------------------------------------------- الأقسام
def _yt_stats() -> str:
    try:
        from .publish import youtube
        tok = youtube._token()
        if not tok:
            return "يوتيوب: التوكن محتاج تجديد (هيتجدد تلقائيًا)"
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "statistics", "mine": "true"},
            headers={"Authorization": f"Bearer {tok}"}, timeout=30).json()
        st = (r.get("items") or [{}])[0].get("statistics", {})
        return (f"📺 القناة:\n"
                f"• المشتركين: {st.get('subscriberCount', '?')}\n"
                f"• المشاهدات: {st.get('viewCount', '?')}\n"
                f"• الفيديوهات: {st.get('videoCount', '?')}")
    except Exception as e:
        return f"تعذر جلب إحصائيات يوتيوب: {str(e)[:60]}"


def _factory_stats() -> str:
    from . import state
    produced = len(state.produced_ids())
    bad = state.reciter_badlist()
    watch = len(state.yt_recent())
    paused = "⏸ متوقف مؤقتًا (بأمرك)" if PAUSE_FILE.exists() else "▶ شغال"
    return (f"🏭 المصنع:\n"
            f"• حلقات أُنتجت: {produced}\n"
            f"• النشر: {paused}\n"
            f"• فيديوهات تحت المراقبة: {watch}\n"
            f"• قراء محظورين (حماية): {len(bad)}")


def cmd_stats(chat_id) -> None:
    send(chat_id, f"🤍 أهلا يا صاحبي! هذه آخر الأرقام:\n\n{_yt_stats()}\n\n{_factory_stats()}")


def cmd_status(chat_id) -> None:
    from . import state
    watch = state.yt_recent()
    lines = [w.get("title", "")[:50] for w in watch[-3:]]
    send(chat_id, "🛡️ الحالة:\n" + _factory_stats()
         + "\n\nآخر ما تحت المراقبة:\n" + ("\n".join(f"• {l}" for l in lines) or "• لا شيء"))


def cmd_next(chat_id) -> None:
    gh = os.environ.get("GITHUB_TOKEN")
    if not gh:
        send(chat_id, "⚙️ الأمر ده يتنفذ من الرنر — اكتبه في أي وقت وهيتنفذ في أقرب دورة (كل 5 دقايق).")
        return
    r = requests.post(
        f"https://api.github.com/repos/{os.environ.get('GITHUB_REPOSITORY', 'DawshaX/XTreNDAW')}"
        "/actions/workflows/nova.yml/dispatches",
        headers={"Authorization": f"Bearer {gh}",
                 "Accept": "application/vnd.github+json"},
        json={"ref": "main"}, timeout=30)
    send(chat_id, "🚀 تمام! دورة إنتاج فورية اتطلقت — الفيديو الجاي خلال دقائق، وهيوصلك إشعار هنا."
         if r.status_code == 204 else f"⚠️ تعذر الإطلاق ({r.status_code})")


def cmd_pause(chat_id) -> None:
    PAUSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PAUSE_FILE.write_text(f'{{"ts": {time.time()}}}', encoding="utf-8")
    send(chat_id, "⏸ تمام — النشر اتوقف مؤقتًا. الإنتاج والتخزين مستمرين، واكتب /resume وقت ما تحب.")


def cmd_resume(chat_id) -> None:
    PAUSE_FILE.unlink(missing_ok=True)
    send(chat_id, "▶ رجّعنا النشر! كل ساعة فيديو على كل المنصات المتصلة.")


def cmd_watch(chat_id) -> None:
    from .run_cycle import _yt_watchdog
    try:
        _yt_watchdog()
        send(chat_id, "🛡️ اتفحصت كل الفيديوهات — أي حظر كان اتحذف فورًا ولو مفيش رد يبقى كله سليم.")
    except Exception as e:
        send(chat_id, f"⚠️ الفحص اتعطل: {str(e)[:80]}")


def cmd_qurra(chat_id) -> None:
    from . import din, state
    prov, bad = state.reciter_proven(), state.reciter_badlist()
    lines = ["🎙️ قراء المصنع:"]
    for i, (rid, name, _) in enumerate(din.RECITERS):
        st = ("✅ معتمد" if rid in prov
              else "⛔ محظور" if rid in bad else "⏳ مرشح — محتاج اعتمادك")
        lines.append(f"{i}) {name} — {st}")
    lines.append("\nلاعتماد قارئ جديد بضغطة: /approve الرقم أو الاسم")
    send(chat_id, "\n".join(lines))


def cmd_approve(chat_id, arg: str) -> None:
    from . import din, state
    arg = (arg or "").strip()
    hit = None
    if arg.isdigit():
        i = int(arg)
        if 0 <= i < len(din.RECITERS):
            hit = din.RECITERS[i]
    elif arg:
        for r in din.RECITERS:
            if arg in r[0] or arg in r[1]:
                hit = r
                break
    if not hit:
        send(chat_id, "⚠️ معرفتش القارئ — اكتب /qurra تشوف القائمة بأرقامها.")
        return
    state.add_reciter_proven(hit[0])
    send(chat_id, f"✅ {hit[1]} اتعتمد رسميًا — هيبدأ ينزل يوتيوب "
                  f"من الحلقة الجاية، والحماية ظلّه فوقه.")


HELP = ("🤖 أنا بوت نوفا — مساعدك في المصنع:\n\n"
        "/stats — الإحصائيات (مشتركين/مشاهدات)\n"
        "/status — حالة المصنع والحماية\n"
        "/next — فيديو فوري\n"
        "/pause — إيقاف النشر مؤقتًا\n"
        "/resume — رجوع النشر\n"
        "/watch — فحص المحظور الآن\n"
        "/qurra — قائمة القراء (معتمد/محظور/مرشح)\n"
        "/approve — اعتماد قارئ جديد\n\n"
        "أو كلمني عادي بالعربي: «احصائيات»، «وقف»، «كمل»، «التالي»، «افحص».")

_KEYWORDS = (
    (("احصائ", "إحصائ", "stats", "ارقام", "أرقام"), "stats"),
    (("وقف", "pause", "ايقاف", "إيقاف"), "pause"),
    (("كمل", "شغل", "resume", "رجع"), "resume"),
    (("التالي", "next", "فيديو جديد", "عجل"), "next"),
    (("افحص", "watch", "حظر", "محظور"), "watch"),
    (("حالة", "status", "المصنع"), "status"),
)


def _handle(chat_id, text: str) -> None:
    t = (text or "").strip()
    low = t.lower()
    if low.startswith("/approve"):
        if not _admin(chat_id):
            send(chat_id, "⚠️ الأمر ده لصاحب المصنع بس.")
            return
        cmd_approve(chat_id, t.split(maxsplit=1)[1] if " " in t else "")
        return
    action = None
    if low.startswith("/"):
        action = {"start": "help", "help": "help", "stats": "stats",
                  "status": "status", "next": "next", "pause": "pause",
                  "resume": "resume", "watch": "watch",
                  "qurra": "qurra"}.get(low.split()[0][1:])
    if not action:
        for keys, act in _KEYWORDS:
            if any(k in t for k in keys):
                action = act
                break
    if not action:
        send(chat_id, "🤍 وصلني كلامك! اكتب /help تشوف كل اللي أقدر أعمله لك — "
                      "وأنا معاك هنا في أي وقت.")
        return
    if action in ("pause", "resume", "next", "watch") and not _admin(chat_id):
        send(chat_id, "⚠️ الأمر ده لصاحب المصنع بس.")
        return
    {"help": lambda: send(chat_id, HELP),
     "stats": lambda: cmd_stats(chat_id),
     "status": lambda: cmd_status(chat_id),
     "next": lambda: cmd_next(chat_id),
     "pause": lambda: cmd_pause(chat_id),
     "resume": lambda: cmd_resume(chat_id),
     "watch": lambda: cmd_watch(chat_id),
     "qurra": lambda: cmd_qurra(chat_id)}[action]()


def _daily_digest() -> None:
    """ملخص يومي 9 مساءً القاهرة — أرقام وتقدم."""
    import json

    now = datetime.now(ZoneInfo("Africa/Cairo"))
    if now.hour != 21:
        return
    today = now.strftime("%Y-%m-%d")
    last = {}
    if DIGEST_FILE.exists():
        try:
            last = json.loads(DIGEST_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    if last.get("date") == today:
        return
    try:
        from .publish import youtube
        tok = youtube._token()
        if not tok:
            return
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "statistics", "mine": "true"},
            headers={"Authorization": f"Bearer {tok}"}, timeout=30).json()
        st = (r.get("items") or [{}])[0].get("statistics", {})
        subs = int(st.get("subscriberCount", 0))
        views = int(st.get("viewCount", 0))
        ds = subs - int(last.get("subs", subs))
        dv = views - int(last.get("views", views))
        admin = settings.TELEGRAM.get("admin_chat")
        if admin:
            send(admin, f"🌙 الملخص اليومي:\n"
                        f"• المشتركين: {subs} ({'+' if ds >= 0 else ''}{ds} النهارده)\n"
                        f"• المشاهدات: {views} ({'+' if dv >= 0 else ''}{dv} النهارده)\n"
                        f"{_factory_stats()}\n"
                        f"ربنا يبارك ويكثر الخير 🤍")
        DIGEST_FILE.write_text(json.dumps({"date": today, "subs": subs,
                                           "views": views}), encoding="utf-8")
    except Exception:
        pass


def run_pass() -> None:
    """قراءة واحدة للرسائل والرد عليها — تتكرر كل 5 دقايق من الرنر."""
    if not settings.has_telegram():
        print("no telegram credentials")
        return
    import json

    offset = 0
    if OFFSET_FILE.exists():
        try:
            offset = json.loads(OFFSET_FILE.read_text(encoding="utf-8")).get("offset", 0)
        except Exception:
            pass
    ups = _call("getUpdates", offset=offset, timeout=5).get("result", [])
    for u in ups:
        offset = max(offset, u.get("update_id", 0) + 1)
        m = u.get("message") or {}
        chat = (m.get("chat") or {}).get("id")
        if chat:
            _handle(chat, m.get("text", ""))
    if offset:
        OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
        OFFSET_FILE.write_text(json.dumps({"offset": offset}), encoding="utf-8")
    try:
        if settings.INSTAGRAM.get("token"):
            from .publish import instagram as _ig
            _ig.refresh_token()
    except Exception:
        pass
    _daily_digest()


def run_loop(seconds: int = 1500) -> None:
    """جلسة حية: تقرأ وترد باستمرار لحد ما تخلص المدة — بعدها الرنر يعيد الإطلاق."""
    import time as _t

    end = _t.time() + seconds
    while _t.time() < end:
        try:
            run_pass()
        except Exception:
            pass
        _t.sleep(1)


if __name__ == "__main__":
    import sys

    if "--loop" in sys.argv:
        i = sys.argv.index("--loop")
        run_loop(int(sys.argv[i + 1]) if len(sys.argv) > i + 1 else 1500)
    else:
        run_pass()
