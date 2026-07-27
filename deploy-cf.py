#!/usr/bin/env python3
"""Deploy PawWork Bot to Cloudflare Workers."""
import json, urllib.request, uuid, io, os, sys

CF_TOKEN = os.environ.get("CF_API_TOKEN", "")
CF_ACCOUNT = os.environ.get("CF_ACCOUNT", "fb92fb442c9a1d5ea93dfb71b368c350")
SCRIPT_NAME = os.environ.get("CF_SCRIPT", "pawwork-bot")

WORKER_PATH = os.path.join(os.path.dirname(__file__), "src", "webhook-worker.js")

with open(WORKER_PATH, "r", encoding="utf-8") as f:
    code = f.read()

print(f"Deploying {SCRIPT_NAME} to Cloudflare Workers...")
print(f"Account: {CF_ACCOUNT}")
print(f"Script size: {len(code)} chars")

url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/workers/scripts/{SCRIPT_NAME}"

boundary = uuid.uuid4().hex
body = io.BytesIO()

def w(s):
    body.write(s.encode("utf-8"))

# Metadata part
w(f"--{boundary}\r\n")
w('Content-Disposition: form-data; name="metadata"\r\n')
w("Content-Type: application/json\r\n\r\n")
# Get tokens from env (set these before running)
tg_token = os.environ.get("TELEGRAM_TOKEN", "")
gh_token = os.environ.get("GH_TOKEN", "")

bindings = []
if tg_token:
    bindings.append({"type": "secret_text", "name": "TELEGRAM_TOKEN", "text": tg_token})
if gh_token:
    bindings.append({"type": "secret_text", "name": "GITHUB_TOKEN", "text": gh_token})
    bindings.append({"type": "secret_text", "name": "GH_TOKEN", "text": gh_token})

metadata = json.dumps({
    "main_module": "worker.js",
    "compatibility_date": "2025-04-01",
    "compatibility_flags": ["nodejs_compat"],
    "bindings": bindings,
})
w(metadata)
w("\r\n")

# Code part
w(f"--{boundary}\r\n")
w('Content-Disposition: form-data; name="worker.js"; filename="worker.js"\r\n')
w("Content-Type: application/javascript+module\r\n\r\n")
w(code)
w("\r\n")

# End
w(f"--{boundary}--\r\n")

req = urllib.request.Request(url, data=body.getvalue(), method="PUT")
req.add_header("Authorization", f"Bearer {CF_TOKEN}")
req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

try:
    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read())
    if result.get("success"):
        print("[OK] Deployed successfully!")
        subdomain = f"{SCRIPT_NAME}.{CF_ACCOUNT[:8]}.workers.dev"
        print(f"     URL: https://{subdomain}")
    else:
        print(f"[FAIL] Deploy failed: {result.get('errors', result)}")
except urllib.error.HTTPError as e:
    err = e.read().decode()[:500]
    print(f"[HTTP {e.code}] {err}")
    sys.exit(1)
