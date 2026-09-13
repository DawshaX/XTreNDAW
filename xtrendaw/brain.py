"""المخ — توليد مواضيع جديدة لما المخزون يقرّب يخلص (ما ينفدش أبدًا).

طبقتان:
1) LLM مجاني (Groq) لو فيه مفتاح → مواضيع لا نهائية ثنائية اللغة.
2) احتياطي قوالب جاهزة (بلا مفتاح) عشان المصنع ما يقفش أبدًا.
النتيجة دايمًا موضوع جديد ببصمة ما اتكررتش (state بيمنع التكرار).
"""
from __future__ import annotations

import json

import requests

from . import content, settings

# احتياطي بلا مفتاح — مواضيع إضافية جاهزة
FALLBACK_POOL: list[dict] = [
    {
        "angle": "الموز مش فاكهة",
        "title_ar": "الموز مش فاكهة… وشجرة الموز مش شجرة!",
        "title_en": "Bananas aren't fruit, and banana trees aren't trees!",
        "hook_ar": "تحذير: كل اللي تعرفه عن الموز غلط من أوله لآخره!",
        "hook_en": "Warning: everything you know about bananas is wrong, top to bottom!",
        "facts_ar": [
            "الموز بيصنف علميًا من التوت، مش الفواكه.",
            "شجرة الموز مش شجرة أصلًا — دي أكبر عشبة معمرة في العالم.",
            "يعني إنت بتاكل توتة ضخمة من عشبة عملاقة. استمتع!",
        ],
        "facts_en": [
            "Botanically, bananas are classified as berries, not fruits.",
            "A banana tree isn't a tree at all — it's the world's largest herb.",
            "So you're eating a giant berry from a massive herb. Enjoy!",
        ],
        "tags": "حقائق,نبات,طعام,XTreNDAW",
    },
    {
        "angle": "المريخ أزرق",
        "title_ar": "غروب الشمس على المريخ أزرق… مش أحمر!",
        "title_en": "Sunsets on Mars are blue, not red!",
        "hook_ar": "تحذير: لو سافرت المريخ، الغروب هيلخبط كل حساباتك!",
        "hook_en": "Warning: on Mars, the sunset will break all your expectations!",
        "facts_ar": [
            "الغبار الدقيق في جو المريخ بيشتت الضوء الأحمر ويسيب الأزرق.",
            "فعند الغروب بتشوف هالة زرقا حوالين الشمس.",
            "يعني الكوكب الأحمر بيغروب بالأزرق… المفارقة حلوة!",
        ],
        "facts_en": [
            "Fine dust in Mars' air scatters red light and lets blue through.",
            "So at sunset you see a blue halo around the sun.",
            "So the red planet sets in blue… what a twist!",
        ],
        "tags": "حقائق,فضاء,مريخ,XTreNDAW",
    },
    {
        "angle": "القلب بيض ضوء",
        "title_ar": "قلبك بيض ضوء كفاية يشغل مصباح… بجد!",
        "title_en": "Your heart powers a small light bulb, seriously!",
        "hook_ar": "تحذير: جوه صدرك مولد كهرباء شغال من أول يوم!",
        "hook_en": "Warning: inside your chest there's a power plant running since day one!",
        "facts_ar": [
            "القلب بيضخ طاقة يومية تكفي نظريًا لإضاءة لمبة صغيرة.",
            "بيدق حوالي 100 ألف مرة في اليوم من غير ما ياخد إجازة.",
            "يعني عندك موتور شغال 24 ساعة ومش بيشتكي… اتعلم منه!",
        ],
        "facts_en": [
            "The heart's daily output could theoretically light a small bulb.",
            "It beats about 100,000 times a day without ever taking a break.",
            "So you own a 24/7 engine that never complains… learn from it!",
        ],
        "tags": "حقائق,جسم,صحة,XTreNDAW",
    },
]


def _llm_topic() -> dict | None:
    if not settings.has_llm():
        return None
    prompt = (
        "اعمل موضوع فيديو حقائق قصير بالعربي والإنجليزي. رجّع JSON فقط بهذه المفاتيح: "
        "angle, title_ar, title_en, hook_ar, hook_en, facts_ar(3), facts_en(3), tags. "
        "النبرة: تحذير لعب في الـhook، نكتة في الحقيقة التالتة، ختام مريح."
    )
    try:
        r = requests.post(
            f"{settings.LLM['base']}/chat/completions",
            headers={"Authorization": f"Bearer {settings.LLM['key']}"},
            json={"model": settings.LLM["model"],
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.9},
            timeout=60,
        )
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
        text = text[text.find("{"): text.rfind("}") + 1]
        t = json.loads(text)
        if t.get("hook_ar") and t.get("facts_ar"):
            t.setdefault("id", f"auto")
            return t
    except Exception:
        return None
    return None


def trend_topic(skip: set | None = None) -> dict | None:
    """موضوع من الرادار اللحظي: نوفا بتركب التريند بروحها (بلا اختلاق وقائع —
    كل "حقيقة" هنا رقم حقيقي من الرادار نفسه). بيعدّي المستهلك قبل كده."""
    from . import trend

    skip = skip or set()
    try:
        top = trend.scan()
    except Exception:
        return None
    for t in top:
        if t["score"] < 5 or not t.get("traffic_raw"):
            continue
        title = t["title"][:60]
        srcs = t.get("sources", 1)
        words = [w for w in title.split() if len(w) >= 3][:3]
        queries = [title] + words
        if words:
            queries.append(f"{words[0]} stadium")
            queries.append(f"{words[0]} match")
        cand = {
            "angle": f"ترند:{t['key'][:24]}",
            "title_ar": f"ليه الكل بيبحث عن «{title}» دلوقتي؟",
            "title_en": f"Why is everyone searching '{title}' right now?",
            "hook_ar": f"تحذير: «{title}» مغطّي على كل حاجة في الإنترنت النهارده!",
            "hook_en": f"Warning: '{title}' is taking over the internet today!",
            "facts_ar": [
                f"أكتر من {t['traffic_raw']} بحث عليه في ساعات على جوجل.",
                f"الإشارة التقطها الرادار من {srcs} مصدر مختلف في نفس اللحظة.",
                "ونوفا شايفة كل حاجة… بس إحنا بنختارلك اللي يستاهل بس.",
            ],
            "facts_en": [
                f"Over {t['traffic_raw']} searches on Google in hours.",
                f"Our radar caught it from {srcs} different sources at once.",
                "NOVA sees everything… we only pick what's worth it.",
            ],
            "tags": "ترند,رادار_نوفا,XTreNDAW",
            "_visual_queries": queries,
            "takeaway_ar": {
                "aql": "الترند بيعدي… بس اللي بيفهم ليه انتشر بيستفيد.",
                "qalb": "إنت مش مجرد متفرج — إنت جزء من الحكاية.",
                "rouh": "خير ونور من الله… وإنت الحر في اللي يجذبك.",
            },
            "takeaway_en": {
                "aql": "Trends fade… but understanding why they spread is power.",
                "qalb": "You're not just a viewer — you're part of the story.",
                "rouh": "Goodness and light from God… and you're free to choose.",
            },
        }
        if content.fingerprint(cand) in skip:
            continue  # مستهلك قبل كده → الترند اللي بعده
        return cand
    return None


def generate(topics: list[dict], want: str = "auto") -> dict | None:
    """موضوع جديد مش مكرر بالبصمة، وإلا None.

    الأولوية: طلبات المشاهدين ← التريند (لو مطلوب/أوتو) ← LLM ← المخزون.
    want: "trend" | "know" | "auto" — التناوب بيحدده run_cycle.
    """
    from . import requests as viewer_requests
    from . import state as _state

    seen = {content.fingerprint(t) for t in topics}

    def _fresh(cand: dict | None, kind: str) -> dict | None:
        if cand and content.fingerprint(cand) not in seen \
                and not _state.fingerprint_seen(cand):
            cand["_kind"] = kind
            return cand
        return None

    for req in viewer_requests.pending():
        cand = _fresh(viewer_requests.topic_from(req), "request")
        if cand:
            return cand

    if want in ("auto", "trend"):
        skip = seen | _state.seen_fingerprints()
        tr = _fresh(trend_topic(skip), "trend")
        if tr:
            return tr
    if want == "trend":
        return None  # مفيش ترند سخن دلوقتي — الدورة تتعدل على معرفة

    t = _fresh(_llm_topic(), "know")
    if t:
        return t

    for cand in FALLBACK_POOL:
        c2 = _fresh(dict(cand), "know")
        if c2:
            return c2
    return None
