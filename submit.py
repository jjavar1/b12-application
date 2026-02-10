import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

URL = "https://b12.io/apply/submission"


def need(key: str) -> str:
    v = os.getenv(key, "").strip()
    if not v:
        raise SystemExit(f"miss env var: {key}")
    return v


def iso_utc_ms() -> str:
    now = datetime.now(timezone.utc)
    ms = now.microsecond // 1000
    return now.replace(microsecond=ms * 1000).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def main() -> int:
    name = need("B12_NAME")
    email = need("B12_EMAIL")
    resume_link = need("B12_RESUME_LINK")
    secret = need("B12_SIGNING_SECRET")

    server = os.getenv("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repo = need("GITHUB_REPOSITORY")
    run_id = need("GITHUB_RUN_ID")

    payload = {
        "action_run_link": f"{server}/{repo}/actions/runs/{run_id}",
        "email": email,
        "name": name,
        "repository_link": f"{server}/{repo}",
        "resume_link": resume_link,
        "timestamp": iso_utc_ms(),
    }

    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    req = urllib.request.Request(
        URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-Signature-256": f"sha256={sig}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = r.read().decode("utf-8", errors="replace")
            status = r.status
    except urllib.error.HTTPError as e:
        resp = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}\n{resp}", file=sys.stderr)
        return 1

    if status != 200:
        print(f"HTTP {status}\n{resp}", file=sys.stderr)
        return 1

    data = json.loads(resp)
    receipt = data.get("receipt")
    if data.get("success") is True and isinstance(receipt, str) and receipt.strip():
        print(receipt.strip())
        return 0

    print(resp, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
