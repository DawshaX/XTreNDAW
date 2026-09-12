"""بنك المحتوى: مواضيع جاهزة + تكوين السيناريو.

القالب الأساسي: hook + 3 حقائق + outro — الصيغة اللي بتشتغل على Shorts/Reels.
التوليد اللامحدود بـLLM مجاني بيضاف كطبقة اختيارية (المحرك شغال بدونه).
"""
from __future__ import annotations

import hashlib
import re

from . import settings

# بنك أولي — كل موضوع مستقل بذاته، ومفيش تكرار (fingerprint بيتحسب)
SEED_TOPICS: list[dict] = [
    {
        "id": "ep1",
        "angle": "جسمك مصنوع من نجوم",
        "title_ar": "جسمك فيه نجوم حقيقية… والدليل هيصدمك!",
        "hook_ar": "هل تعرف إن كل ذرة في جسمك كانت جوه نجم انفجر؟",
        "facts_ar": [
            "كل ذرة كربون في جسمك اتصنعت جوه قلب نجم ضخم.",
            "الحديد اللي في دمك ما اتكونش غير في آخر لحظات انفجار نجمي.",
            "يعني إنت حرفيًا بتتنفس بقايا نجوم ماتت من مليارات السنين.",
        ],
        "outro_ar": "تابع XTreNDAW — الحلقة الجاية أقوى.",
        "tags": "حقائق,علوم,فضاء,XTreNDAW",
    },
    {
        "id": "ep2",
        "angle": "المادة المضادة",
        "title_ar": "أغلى من الماس بمليون مرة… مادة تكلف تريليونات!",
        "hook_ar": "في مادة تكلفتها أكبر من اقتصاد العالم كله.",
        "facts_ar": [
            "جرام واحد من المادة المضادة يتجاوز 60 تريليون دولار.",
            "كل اللي صنعته البشرية منها ما يملأش ملعقة شاي.",
            "لو لمست المادة العادية، الاثنان يتلاشيان في ومضة طاقة صرفة.",
        ],
        "outro_ar": "تابع XTreNDAW — الحلقة الجاية أقوى.",
        "tags": "حقائق,علوم,فيزياء,XTreNDAW",
    },
    {
        "id": "ep3",
        "angle": "سر النوم",
        "title_ar": "مخك بيغسل نفسه وإنت نايم… الحقيقة مرعبة!",
        "hook_ar": "إنت بتقضي ثلث عمرك نايم، والسبب مش الراحة بس.",
        "facts_ar": [
            "أثناء النوم مخك بيقلص حجمه عشان السائل النخاعي يغسله.",
            "الغسيل ده بيشيل البروتينات السامة اللي بتسبب الزهايمر.",
            "ليلة واحدة من غير نوم بترفع السموم دي بشكل measurable.",
        ],
        "outro_ar": "تابع XTreNDAW — الحلقة الجاية أقوى.",
        "tags": "حقائق,علوم,مخ,XTreNDAW",
    },
]

LABELS_AR = ["الحقيقة الأولى:", "الحقيقة الثانية:", "والحقيقة الثالثة:"]


def fingerprint(topic: dict) -> str:
    """بصمة ضد التكرار — عنوان + حقائق، مش بس الـid.

    السبب: نفس الموضوع ممكن يرجع بعنوان مختلف من المولّد.
    """
    raw = "|".join([
        re.sub(r"\s+", " ", (topic.get("title_ar") or topic["angle"])).strip(),
        *[re.sub(r"\s+", " ", f).strip() for f in (topic.get("facts_ar") or [])],
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def compose_script(topic: dict, lang: str = "ar") -> list[dict]:
    """موضوع → مقاطع مرتبة: hook / fact1..3 / outro."""
    if lang != "ar":
        raise NotImplementedError("مسار اللغة الإنجليزية لسه ما اتبناش — مفيش مسار صامت")

    segs = [{"seg": "hook", "text": topic["hook_ar"].strip()}]
    for i, fact in enumerate(topic["facts_ar"][:3]):
        label = LABELS_AR[i] if i < len(LABELS_AR) else f"الحقيقة {i + 1}:"
        segs.append({"seg": f"fact{i + 1}", "text": f"{label} {fact.strip()}"})
    segs.append({"seg": "outro",
                 "text": (topic.get("outro_ar") or settings.BRAND["outro_ar"]).strip()})
    return segs


def make_caption(topic: dict) -> str:
    """كابشن المنشور."""
    tags = " ".join(f"#{t.strip()}" for t in topic.get("tags", "").split(",") if t.strip())
    return f"{topic['title_ar']}\n{tags}"


def scene_queries(topic: dict) -> list[str]:
    """كلمات بحث للمشاهد (تُستخدم لو فيه مفتاح Pexels)."""
    return [t.strip() for t in topic.get("tags", "").split(",") if t.strip()][:4]
