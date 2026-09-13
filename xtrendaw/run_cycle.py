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
    if topic.get("_din"):
        from . import din as _din

        r = _din.produce_din(topic["_din"], workdir, topic.get("_din_rec", 0),
                             topic.get("_din_spec"))
    else:
        r = produce.produce_episode(topic, workdir)
    dt = time.time() - t0

    info = r["report"]["info"]
    if not r["report"]["ok"]:
        _log(f"✗ {topic['id']} فشل في فحص المواصفات:")
        for name, ok in r["report"]["checks"].items():
            if not ok:
                _log(f"    - {name}")
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)
        return 1

    urls = {}
    if upload and github_store.available():
        try:
            meta = {"id": topic["id"], "title_ar": topic["title_ar"],
                    "tags": topic.get("tags", ""), "_issue": topic.get("_issue"),
                    "kind": topic.get("_kind", "know")}
            urls = github_store.upload_to_vault(r["video"], r["cover"], meta)
            _log("📦 اتخزنت في الـvault — مستنية موعد الذروة")
        except Exception as e:  # فشل التخزين ما يوقفش الدورة
            _log(f"⚠ تخزين GitHub اتخطى: {str(e)[:120]}")
    state.mark_produced(topic, str(r["video"]), info["duration"], urls=urls)
    if topic.get("_ledger_key"):
        from . import planner

        planner.mark_done(topic)
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
    from .publish import facebook as _fb, instagram as _ig, telegram as _tg, youtube as _yt
    video_url = urls.get("video")
    if not video_url:
        return  # من غير رابط عام مفيش نشر (إنستجرام/فيسبوك بيحتاجوه)
    title = topic["title_ar"]
    caption = content.make_caption(topic)
    tags = [t.strip() for t in topic.get("tags", "").split(",") if t.strip()]
    for name, mod, ok in (("youtube", _yt, settings.has_youtube),
                          ("telegram", _tg, settings.has_telegram),
                          ("facebook", _fb, settings.has_facebook),
                          ("instagram", _ig, settings.has_instagram)):
        if not ok():
            continue
        try:
            if name in ("youtube", "telegram"):
                url, err = mod.publish(r["video"], title, caption, tags)
            else:
                url, err = mod.publish(video_url, title, caption, tags)
            if err:
                _log(f"⚠ {name}: {err[:100]}")
                if name == "youtube" and video_url:
                    state.push_yt_pending({"url": video_url, "title": title,
                                           "caption": caption, "tags": tags})
                    _log("⏳ الحلقة اتعلقت في طابور يوتيوب — هتنشر أول ما الكوتة تفتح")
            else:
                _log(f"📣 {name}: {url}")
        except Exception as e:  # النشر ما يكسرش الدورة أبدًا
            _log(f"⚠ {name} اتخطى: {str(e)[:100]}")


def _flush_yt_pending() -> None:
    """يحاول نشر أقدم حلقة معلقة (كوتة) — واحدة كل دورة."""
    import tempfile

    import requests as _rq

    from .publish import youtube as _yt

    if not settings.has_youtube():
        return
    pend = state.yt_pending()
    if not pend:
        return
    item = pend[0]
    tmp = Path(tempfile.mkdtemp()) / "v.mp4"
    try:
        r = _rq.get(item["url"], timeout=600)
        r.raise_for_status()
        tmp.write_bytes(r.content)
        url, err = _yt.publish(tmp, item["title"], item["caption"], item["tags"])
        if err:
            _log(f"⏳ المعلقة لسه مستنية الكوتة: {str(err)[:80]}")
            return
        state.pop_yt_pending()
        _log(f"📣 يوتيوب (من الطابور): {url}")
    except Exception as e:
        _log(f"⚠ تفريغ الطابور اتخطى: {str(e)[:80]}")


def _promote_due(force: bool = False) -> None:
    """الإفراج عن أقدم حلقة من الـvault على القناة في مواعيد الذروة (القاهرة)."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    _flush_yt_pending()

    hour = datetime.now(ZoneInfo("Africa/Cairo")).hour
    if not force and hour not in settings.PUBLISH_HOURS:
        return
    res = github_store.promote_next()
    if not res:
        return
    meta = res["meta"]
    _log(f"📺 موعد الذروة: {res['id']} نزلت على القناة → {res['urls']['video']}")
    state.set_last_kind(meta.get("kind", "know"))  # التناوب: الجاية النوع التاني
    topic = {"id": meta.get("id", res["id"]),
             "title_ar": meta.get("title_ar", ""),
             "tags": meta.get("tags", ""), "_issue": meta.get("_issue")}
    _publish(topic, {"video": res["local_video"]}, res["urls"])
    if topic.get("_issue"):
        from . import requests as viewer_requests

        viewer_requests.answer_and_close(topic["_issue"], res["urls"]["video"])
        _log("💬 اترد على طلب المشاهد واتقفل")
    import shutil
    shutil.rmtree(res["tmp"], ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(prog="xtrendaw")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--episode")
    ap.add_argument("--next", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--stock", type=int, default=0,
                    help="تموين: ينتج N حلقات جديدة ويخزّنها")
    ap.add_argument("--want", choices=["trend", "know"],
                    help="فرض نوع الحلقة (لتجهيز عينات الاعتماد)")
    ap.add_argument("--promote", action="store_true",
                    help="إفراج فوري عن حلقة من الـvault (للاختبار)")
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()

    if args.promote:
        _promote_due(force=True)
        return 0

    if args.stock:
        topics = content.load_topics()
        rc = 0
        for _ in range(args.stock):
            topic = brain.generate(topics)
            if not topic:
                _log("المخ وقف — مفيش مواضيع جديدة دلوقتي")
                break
            topic["id"] = _auto_id(topics)
            topics.append(topic)
            rc |= _produce(topic, upload=not args.no_upload)
            if not args.no_upload:
                _promote_due()
        content.save_topics(topics)
        return rc

    if args.list:
        return cmd_list()

    if args.episode:
        topic = next((t for t in content.load_topics() if t["id"] == args.episode), None)
        if not topic:
            _log(f"✗ مفيش موضوع بالـid ده: {args.episode}")
            return 1
        return _produce(topic, upload=not args.no_upload)

    if args.next:
        if settings.CHANNEL_MODE == "deen":
            # المخطّط الذكي: سلسلة + تناوب + بلا تكرار (الذاكرة على git)
            from . import planner

            topic = planner.next_episode()
            _log(f"🧭 المخطط: {topic['_din']} · {topic['title_ar']}")
            rec = topic["_din_rec"]
            topic = {**topic, "_din_rec": rec}
            rc = _produce(topic, upload=not args.no_upload)
            if not args.no_upload:
                _promote_due()
            return rc
        topics = content.load_topics()
        # التناوب: ساعة تريند / ساعة معرفة — عكس آخر نوع اتنشر
        want = args.want or ("know" if state.last_kind() == "trend" else "trend")
        topic = None
        if want == "know":
            topic = state.next_topic(topics)
        if not topic:
            topic = brain.generate(topics, want=want)
        if not topic:  # ترند مطلوب ومش سخن دلوقتي → معرفة بدل ما نضيع الدورة
            topic = state.next_topic(topics) or brain.generate(topics, want="know")
        if not topic:
            _log("المخ ما قدرش يولّد موضوع جديد — استنى المفتاح أو زوّد القوالب")
            return 0
        if topic.get("id") is None or \
                not any(t["id"] == topic.get("id") for t in topics):
            topic["id"] = _auto_id(topics)
            topics.append(topic)
            content.save_topics(topics)
            _log(f" المخ ولّد موضوع جديد ({want}): {topic['id']}")
        rc = _produce(topic, upload=not args.no_upload)
        if not args.no_upload:
            _promote_due()
        return rc

    if args.all:
        rc = 0
        for t in content.load_topics():
            if state.is_produced(t["id"]):
                _log(f"· {t['id']} متنتجة قبل كده — تخطي")
                continue
            rc |= _produce(t, upload=not args.no_upload)
        if not args.no_upload:
            _promote_due()
        cmd_list()
        return rc

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
