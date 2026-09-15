"""📸 لقطة_frames فورية من كل حلقة — مراقبة جودة بصرية دائمة على GitHub.

بعد ما الحلقة تعدي فحص ما قبل النشر، بنطلّع ورقة إطارات 5×2 وتتcommit
مع state — فتفضل موجودة دايمًا حتى بعد ما أصول الـvault تتحذف.
إضافة بلا أي حذف لأي كود سابق.
"""
import json
import shutil
import subprocess
import time
from pathlib import Path

from . import settings

_FF = None


def _ffmpeg() -> str | None:
    global _FF
    if _FF:
        return _FF
    _FF = shutil.which("ffmpeg")
    if not _FF:
        try:
            import imageio_ffmpeg

            _FF = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            _FF = None
    return _FF


def shoot(mp4, kind: str, title: str) -> Path | None:
    """ورقة إطارات 5×2 (كل 6 ثوانٍ) تتحفظ في state/latest_sheet.jpg."""
    ff = _ffmpeg()
    if not ff:
        return None
    out = settings.ROOT / "state" / "latest_sheet.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [ff, "-y", "-i", str(mp4), "-vf",
         "fps=1/6,scale=300:-1,tile=5x2", "-frames:v", "1",
         "-q:v", "3", str(out)],
        capture_output=True, timeout=180, check=False)
    if not out.exists() or out.stat().st_size < 2000:
        return None
    (settings.ROOT / "state" / "latest_sheet.json").write_text(
        json.dumps({"kind": kind, "title": title, "ts": int(time.time())},
                   ensure_ascii=False, indent=1),
        encoding="utf-8")
    return out
