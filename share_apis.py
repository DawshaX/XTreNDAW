#!/usr/bin/env python3
"""🧰 نسخ مفاتيح الـAPIs من المستودع ده لمستودع Dollars (المصنع يستخدم كل حاجة متاحة)."""
import base64, json, os, urllib.request

NAMES = [n.strip() for n in (os.environ.get("NAMES") or "").split(",") if n.strip()]

def env(n, d=""):
    return (os.environ.get(n) or d).strip()

def put_secret(repo, name, value, pat):
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/actions/secrets/public-key",
                                 headers={"Authorization": f"token {pat}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        pk = json.load(r)
    from nacl import encoding, public
    sealed = base64.b64encode(public.SealedBox(
        public.PublicKey(pk["key"].encode(), encoding.Base64Encoder)).encrypt(value.encode())).decode()
    body = json.dumps({"encrypted_value": sealed, "key_id": pk["key_id"]}).encode()
    rq = urllib.request.Request(f"https://api.github.com/repos/{repo}/actions/secrets/{name}",
        data=body, method="PUT", headers={"Authorization": f"token {pat}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(rq, timeout=30) as r:
        return r.status

def main():
    pat, target = env("CROSS_PAT"), env("TARGET", "DawshaX/Dollars")
    if not (pat and NAMES):
        print("⏭️ مفيش مفاتيح تتنقل"); return 0
    moved, missing = [], []
    for n in NAMES:
        v = os.environ.get(n, "")
        if not v.strip():
            missing.append(n); continue
        try:
            put_secret(target, n, v, pat); moved.append(n)
        except Exception as e:
            missing.append(f"{n} (فشل: {type(e).__name__})")
    print("✅ اتنقل:", ", ".join(moved) or "مفيش")
    print("⏭️ مش موجود:", ", ".join(missing) or "مفيش")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
