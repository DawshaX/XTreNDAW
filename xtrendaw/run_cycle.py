"""باب الدخول للبرنامج.

الاستخدام:
  python -m xtrendaw.run_cycle --list          # المواضيع وحالتها
  python -m xtrendaw.run_cycle --episode ep1   # إنتاج حلقة محددة
  python -m xtrendaw.run_cycle --next          # إنتاج التالية (مش متنتجة/مكررة)
  python -m xtrendaw.run_cycle --all           # إنتاج كل العيّنات الأولية
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import brain, content, github_store, produce, settings, state, video


def _log(*a) -> None:
    print(f"[xtrendaw {time.strftime('%H:%M:%S')}]", *a, flush=True)


def cmd_list() -> int:
    _log("المواضيع:")
    for t in content.load_topics():
        status = "✓ متنتجة" if state.is_produced(t["id"]) else "· لسه"
        _log(f"  [{t['id']}] {status} — {t['title_ar']}")
    return 0


def _produce(topic: dict, upload: bool = True) -> int:
    _log(f"▶ إنتاج {topic['id']}: {topic['title_ar']}")
    workdir = settings.WORK / topic["id"]
    t0 = time.time()
    r = produce.produce_episode(topic, workdir)
    dt = time.time() - t0

    info = r["report"]["info"]
    if not r["report"]["ok"]:
        _log(f"✗ {topic['id']} فشل في فحص المواصفات:")
        for name, ok in r["report"]["checks"].items():
            if not ok:
                _log(f"    - {name}")
        return 1

    urls = {}
    if upload and github_store.available():
        try:
            urls = github_store.upload_episode(r["video"], r["cover"])
            _log(f"☁ على GitHub: {urls['video']}")
        except Exception as e:  # فشل الرفع ما يوقفش الدورة
            _log(f"⚠ رفع GitHub اتخطى: {str(e)[:120]}")
    _publish(topic, r, urls)
    state.mark_produced(topic, str(r["video"]), info["duration"], urls=urls)
    # عادة المساحة: اللي اترفع على GitHub بيتحذف محليًا،
    # ومجلد الشغل الوسيط بيتحذف دايمًا (الفيديو النهائي يفضل في content/vids)
    if urls.get("video"):
        for f in (r["video"], r["cover"]):
            try: Path(f).unlink(missing_ok=True)
            except Exception: pass
        _log(" النواتج المحلية اتحذفت (موجودة على GitHub)")
    import shutil
    shutil.rmtree(workdir, ignore_errors=True)
    _log(
        f"✓ {topic['id']} في {dt:.0f}ث — "
        f"{info['width']}×{info['height']} · {info['duration']:.1f}s · "
        f"{info['bytes'] // 1024}KB · غلاف: {Path(r['cover']).name}"
    )
    return 0


def _auto_id(topics: list[dict]) -> str:
    mx = 0
    for t in topics:
        if t["id"].startswith("auto-"):
            try:
                mx = max(mx, int(t["id"].split("-", 1)[1]))
            except ValueError:
                pass
    return f"auto-{mx + 1:03d}"


def _publish(topic, r: dict, urls: dict) -> None:
    """ينشر على المنصات المتصلة بس — رابط Releases العام هو مصدر الفيديو."""
    from . import publish
    video_url = urls.get("video")
    if not video_url:
        return  # من غير رابط عام مفيش نشر (إنستجرام/فيسبوك بيحتاجوه)
    title = topic["title_ar"]
    caption = content.make_caption(topic)
    tags = [t.strip() for t in topic.get("tags", "").split(",") if t.strip()]
    for name, mod, ok in (("youtube", publish.youtube, settings.has_youtube),
                          ("facebook", publish.facebook, settings.has_facebook),
                          ("instagram", publish.instagram, settings.has_instagram)):
        if not ok():
            continue
        try:
            if name == "youtube":
                url, err = mod.publish(r["video"], title, caption, tags)
            else:
                url, err = mod.publish(video_url, title, caption, tags)
            if err:
                _log(f"⚠ {name}: {err[:100]}")
            else:
                _log(f"📣 {name}: {url}")
        except Exception as e:  # النشر ما يكسرش الدورة أبدًا
            _log(f"⚠ {name} اتخطى: {str(e)[:100]}")


def main() -> int:
    ap = argparse.ArgumentParser(prog="xtrendaw")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--episode")
    ap.add_argument("--next", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()

    if args.list:
        return cmd_list()

    if args.episode:
        topic = next((t for t in content.load_topics() if t["id"] == args.episode), None)
        if not topic:
            _log(f"✗ مفيش موضوع بالـid ده: {args.episode}")
            return 1
        return _produce(topic, upload=not args.no_upload)

    if args.next:
        topics = content.load_topics()
        topic = state.next_topic(topics)
        if not topic:  # المخزون خلص → المخ يولّد موضوع جديد
            topic = brain.generate(topics)
            if not topic:
                _log("المخ ما قدرش يولّد موضوع جديد — استنى المفتاح أو زوّد القوالب")
                return 0
            topic["id"] = _auto_id(topics)
            topics.append(topic)
            content.save_topics(topics)
            _log(f" المخ ولّد موضوع جديد: {topic['id']}")
        return _produce(topic, upload=not args.no_upload)

    if args.all:
        rc = 0
        for t in content.load_topics():
            if state.is_produced(t["id"]):
                _log(f"· {t['id']} متنتجة قبل كده — تخطي")
                continue
            rc |= _produce(t, upload=not args.no_upload)
        cmd_list()
        return rc

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
